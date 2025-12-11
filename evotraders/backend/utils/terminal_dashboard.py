# -*- coding: utf-8 -*-
"""
Terminal Dashboard - Persistent unified panel using Rich Live
"""
# pylint: disable=R0915,R0912
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class TerminalDashboard:
    """Unified persistent terminal dashboard"""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.live: Optional[Live] = None

        # Config state
        self.mode = "live"
        self.config_name = ""
        self.host = "0.0.0.0"
        self.port = 8765
        self.poll_interval = 10
        self.trigger_time = "now"
        self.mock = False
        self.enable_memory = False
        self.local_time = ""
        self.nyse_time = ""
        self.start_date = ""
        self.end_date = ""
        self.tickers: List[str] = []
        self.initial_cash = 100000.0

        # Trading state
        self.current_date = "-"
        self.status = "Initializing"
        self.total_value = 0.0
        self.cash = 0.0
        self.pnl_pct = 0.0
        self.holdings: List[Dict] = []
        self.trades: List[Dict] = []
        self.days_completed = 0
        self.days_total = 0

        # Progress message (last line)
        self.progress = ""
        self._dots_index = 0
        self._animator_running = False
        self._animator_thread: Optional[threading.Thread] = None

    def set_config(
        self,
        mode: str,
        config_name: str,
        host: str,
        port: int,
        poll_interval: int,
        trigger_time: str = "now",
        mock: bool = False,
        enable_memory: bool = False,
        local_time: str = "",
        nyse_time: str = "",
        start_date: str = "",
        end_date: str = "",
        tickers: List[str] = None,
        initial_cash: float = 100000.0,
    ):
        """Set configuration state"""
        self.mode = mode
        self.config_name = config_name
        self.host = host
        self.port = port
        self.poll_interval = poll_interval
        self.trigger_time = trigger_time
        self.mock = mock
        self.enable_memory = enable_memory
        self.local_time = local_time
        self.nyse_time = nyse_time
        self.start_date = start_date
        self.end_date = end_date
        self.tickers = tickers or []
        self.initial_cash = initial_cash
        self.total_value = initial_cash
        self.cash = initial_cash

    def _build_panel(self) -> Panel:
        """Build the unified dashboard panel"""
        # Main grid
        main_table = Table.grid(padding=(0, 2))
        main_table.add_column(width=28)
        main_table.add_column(width=22)
        main_table.add_column(width=22)

        # Left: Config + Status
        left = Table.grid(padding=(0, 0))
        left.add_column()

        # Mode line
        if self.mode == "backtest":
            mode_str = "[cyan]Backtest[/cyan]"
        elif self.mock:
            mode_str = "[yellow]MOCK[/yellow]"
        else:
            mode_str = "[green]LIVE[/green]"

        left.add_row(f"[bold]Mode:[/bold] {mode_str}")
        left.add_row(f"[dim]Config:[/dim] {self.config_name}")
        left.add_row(f"[dim]Server:[/dim] {self.host}:{self.port}")

        if self.mode == "live" and self.nyse_time:
            left.add_row(f"[dim]NYSE:[/dim] {self.nyse_time[:19]}")
            trigger_display = (
                "[green]NOW[/green]"
                if self.trigger_time == "now"
                else self.trigger_time
            )
            left.add_row(f"[dim]Trigger:[/dim] {trigger_display}")

        # Status
        left.add_row("")
        status_style = "green" if self.status == "Running" else "yellow"
        left.add_row(
            "[bold]Status:[/bold] "
            f"[{status_style}]{self.status}[/{status_style}]",
        )
        if self.mode == "backtest":
            left.add_row(
                f"[dim]Backtesting Period:[/dim] {self.days_total} days\n"
                f"  {self.start_date} -> {self.end_date}",
            )
        left.add_row(f"[dim]Current Date:[/dim] {self.current_date}")

        # Middle: Portfolio
        mid = Table.grid(padding=(0, 0))
        mid.add_column()

        pnl_style = "green" if self.pnl_pct >= 0 else "red"
        mid.add_row("[bold]Portfolio[/bold]")
        mid.add_row(f"NAV: [bold]${self.total_value:,.0f}[/bold]")
        mid.add_row(f"Cash: ${self.cash:,.0f}")
        mid.add_row(f"P&L: [{pnl_style}]{self.pnl_pct:+.2f}%[/{pnl_style}]")

        # Positions
        mid.add_row("")
        mid.add_row("[bold]Positions[/bold]")
        stock_holdings = [
            h for h in self.holdings if h.get("ticker") != "CASH"
        ]
        if stock_holdings:
            for h in stock_holdings[:7]:
                qty = h.get("quantity", 0)
                ticker = h.get("ticker", "")[:5]
                val = h.get("marketValue", 0)
                qty_str = f"{qty:+d}" if qty != 0 else "0"
                mid.add_row(
                    f"[cyan]{ticker:<5}[/cyan] {qty_str:>5} ${val:>7,.0f}",
                )
            if len(stock_holdings) > 7:
                mid.add_row(f"[dim]+{len(stock_holdings) - 7} more[/dim]")
        else:
            mid.add_row("[dim]No positions[/dim]")

        # Right: Recent Trades
        right = Table.grid(padding=(0, 0))
        right.add_column()

        right.add_row("[bold]Recent Trades[/bold]")
        if self.trades:
            for t in self.trades[:10]:
                side = t.get("side", "")
                ticker = t.get("ticker", "")[:5]
                qty = t.get("qty", 0)
                if side == "LONG":
                    side_str = "[green]L[/green]"
                elif side == "SHORT":
                    side_str = "[red]S[/red]"
                else:
                    side_str = "[dim]H[/dim]"
                right.add_row(f"{side_str} [cyan]{ticker:<5}[/cyan] {qty:>4}")
            if len(self.trades) > 10:
                right.add_row(f"[dim]+{len(self.trades) - 10} more[/dim]")
        else:
            right.add_row("[dim]No trades[/dim]")

        main_table.add_row(left, mid, right)

        # Outer table to add progress line at bottom
        outer = Table.grid(padding=(0, 0))
        outer.add_column()
        outer.add_row(main_table)

        # Progress line (last row) with animated dots
        if self.progress:
            DOTS_FRAMES = ["   ", ".  ", ".. ", "..."]
            dots = DOTS_FRAMES[self._dots_index % len(DOTS_FRAMES)]
            outer.add_row("")
            outer.add_row(f"[dim]> {self.progress}{dots}[/dim]")

        # Build panel
        title = "[bold cyan]EvoTraders[/bold cyan]"
        if self.mode == "backtest":
            title += " [dim]Backtest[/dim]"
        elif self.mock:
            title += " [dim]Mock[/dim]"
        else:
            title += " [dim]Live[/dim]"

        return Panel(
            outer,
            title=title,
            border_style="cyan",
            padding=(0, 1),
        )

    def _run_animator(self):
        """Background thread to animate the dots"""
        while self._animator_running:
            time.sleep(0.3)
            if self.progress and self.live:
                self._dots_index += 1
                self.live.update(self._build_panel())

    def start(self):
        """Start the live dashboard display"""
        self.live = Live(
            self._build_panel(),
            console=self.console,
            refresh_per_second=4,
            vertical_overflow="visible",
        )
        self.live.start()

        # Start animator thread
        self._animator_running = True
        self._animator_thread = threading.Thread(
            target=self._run_animator,
            daemon=True,
        )
        self._animator_thread.start()

    def stop(self):
        """Stop the live dashboard"""
        self._animator_running = False
        if self._animator_thread:
            self._animator_thread.join(timeout=0.5)
            self._animator_thread = None
        if self.live:
            self.live.stop()
            self.live = None

    def update(
        self,
        date: str = None,
        status: str = None,
        portfolio: Dict[str, Any] = None,
        holdings: List[Dict] = None,
        trades: List[Dict] = None,
        days_completed: int = None,
        days_total: int = None,
    ):
        """Update dashboard state and refresh display"""
        if date:
            self.current_date = date
        if status:
            self.status = status
        if days_completed is not None:
            self.days_completed = days_completed
        if days_total is not None:
            self.days_total = days_total

        if portfolio:
            self.total_value = portfolio.get(
                "totalAssetValue",
                0,
            ) or portfolio.get(
                "total_value",
                self.initial_cash,
            )
            self.cash = portfolio.get("cashPosition", 0) or portfolio.get(
                "cash",
                self.initial_cash,
            )
            if self.total_value > 0 and self.initial_cash > 0:
                self.pnl_pct = (
                    (self.total_value - self.initial_cash) / self.initial_cash
                ) * 100

        if holdings is not None:
            self.holdings = holdings
        if trades is not None:
            self.trades = trades

        if self.live:
            self.live.update(self._build_panel())

    def log(self, msg: str, also_log: bool = True):
        """
        Update progress message and refresh panel

        Args:
            msg: Progress message to display
            also_log: Whether to also write to logger (default True)
        """
        self.progress = msg
        if also_log:
            logger.info(msg)
        if self.live:
            self.live.update(self._build_panel())

    def print_final_summary(self):
        """Print final summary when dashboard stops"""
        pnl_style = "green" if self.pnl_pct >= 0 else "red"

        if self.mode == "backtest":
            msg = (
                f"[bold]Backtest Complete[/bold] | "
                f"Days: {self.days_completed} | "
                f"NAV: ${self.total_value:,.0f} | "
                f"Return: [{pnl_style}]{self.pnl_pct:+.2f}%[/{pnl_style}]"
            )
        else:
            msg = (
                f"[bold]Session End[/bold] | "
                f"NAV: ${self.total_value:,.0f} | "
                f"P&L: [{pnl_style}]{self.pnl_pct:+.2f}%[/{pnl_style}]"
            )

        self.console.print(Panel(msg, border_style="green"))


# Global instance
_dashboard: Optional[TerminalDashboard] = None


def get_dashboard() -> TerminalDashboard:
    """Get or create global dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = TerminalDashboard()
    return _dashboard
