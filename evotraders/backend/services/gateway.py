# -*- coding: utf-8 -*-
"""
WebSocket Gateway for frontend communication
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from backend.utils.msg_adapter import FrontendAdapter
from backend.utils.terminal_dashboard import get_dashboard
from backend.core.pipeline import TradingPipeline
from backend.core.state_sync import StateSync
from backend.services.market import MarketService
from backend.services.storage import StorageService

logger = logging.getLogger(__name__)


class Gateway:
    """WebSocket Gateway for frontend communication"""

    def __init__(
        self,
        market_service: MarketService,
        storage_service: StorageService,
        pipeline: TradingPipeline,
        state_sync: Optional[StateSync] = None,
        scheduler_callback: Optional[Callable] = None,
        config: Dict[str, Any] = None,
    ):
        self.market_service = market_service
        self.storage = storage_service
        self.pipeline = pipeline
        self.scheduler_callback = scheduler_callback
        self.config = config or {}

        self.mode = self.config.get("mode", "live")
        self.is_backtest = self.mode == "backtest" or self.config.get(
            "backtest_mode",
            False,
        )

        self.state_sync = state_sync or StateSync(storage=storage_service)
        # self.state_sync.set_mode(self.is_backtest)
        self.state_sync.set_broadcast_fn(self.broadcast)
        self.pipeline.state_sync = self.state_sync

        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.lock = asyncio.Lock()
        self._backtest_task: Optional[asyncio.Task] = None
        self._backtest_start_date: Optional[str] = None
        self._backtest_end_date: Optional[str] = None
        self._dashboard = get_dashboard()
        self._market_status_task: Optional[asyncio.Task] = None

        # Session tracking for live returns
        self._session_start_portfolio_value: Optional[float] = None

    async def start(self, host: str = "0.0.0.0", port: int = 8766):
        """Start gateway server"""
        logger.info(f"Starting gateway on {host}:{port}")

        # Initialize terminal dashboard
        self._dashboard.set_config(
            mode=self.mode,
            config_name=self.config.get("config_name", "default"),
            host=host,
            port=port,
            poll_interval=self.config.get("poll_interval", 10),
            mock=self.config.get("mock_mode", False),
            tickers=self.config.get("tickers", []),
            initial_cash=self.storage.initial_cash,
            start_date=self._backtest_start_date or "",
            end_date=self._backtest_end_date or "",
        )
        self._dashboard.start()

        self.state_sync.load_state()
        self.state_sync.update_state("status", "running")
        self.state_sync.update_state("server_mode", self.mode)
        self.state_sync.update_state("is_backtest", self.is_backtest)
        self.state_sync.update_state(
            "is_mock_mode",
            self.config.get("mock_mode", False),
        )

        # Load and display existing portfolio state if available
        summary = self.storage.load_file("summary")
        if summary:
            holdings = self.storage.load_file("holdings") or []
            trades = self.storage.load_file("trades") or []
            current_date = self.state_sync.state.get("current_date")
            self._dashboard.update(
                date=current_date or "-",
                status="running",
                portfolio=summary,
                holdings=holdings,
                trades=trades,
            )
            logger.info(
                "Loaded existing portfolio: $%s",
                f"{summary.get('totalAssetValue', 0):,.2f}",
            )

        await self.market_service.start(broadcast_func=self.broadcast)

        if self.scheduler_callback:
            await self.scheduler_callback(callback=self.on_strategy_trigger)

        # Start market status monitoring (only for live mode)
        if not self.is_backtest:
            self._market_status_task = asyncio.create_task(
                self._market_status_monitor(),
            )

        async with websockets.serve(
            self.handle_client,
            host,
            port,
            ping_interval=30,
            ping_timeout=60,
        ):
            logger.info(
                f"Gateway started: ws://{host}:{port}, mode={self.mode}",
            )
            await asyncio.Future()

    @property
    def state(self) -> Dict[str, Any]:
        return self.state_sync.state

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket client connection"""
        async with self.lock:
            self.connected_clients.add(websocket)

        await self._send_initial_state(websocket)
        await self._handle_client_messages(websocket)

        async with self.lock:
            self.connected_clients.discard(websocket)

    async def _send_initial_state(self, websocket: WebSocketServerProtocol):
        state_payload = self.state_sync.get_initial_state_payload(
            include_dashboard=True,
        )
        # Include market status in initial state
        state_payload[
            "market_status"
        ] = self.market_service.get_market_status()

        # Include live returns if session is active
        if self.storage.is_live_session_active:
            live_returns = self.storage.get_live_returns()
            if "portfolio" in state_payload:
                state_payload["portfolio"].update(live_returns)

        await websocket.send(
            json.dumps(
                {"type": "initial_state", "state": state_payload},
                ensure_ascii=False,
                default=str,
            ),
        )

    async def _handle_client_messages(
        self,
        websocket: WebSocketServerProtocol,
    ):
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type", "unknown")

                if msg_type == "ping":
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "pong",
                                "timestamp": datetime.now().isoformat(),
                            },
                            ensure_ascii=False,
                        ),
                    )
                elif msg_type == "get_state":
                    await self._send_initial_state(websocket)
                elif msg_type == "start_backtest":
                    await self._handle_start_backtest(data)

        except websockets.ConnectionClosed:
            pass
        except json.JSONDecodeError:
            pass

    async def _handle_start_backtest(self, data: Dict[str, Any]):
        if not self.is_backtest:
            return
        dates = data.get("dates", [])
        if dates and self._backtest_task is None:
            task = asyncio.create_task(
                self._run_backtest_dates(dates),
            )
            task.add_done_callback(self._handle_backtest_exception)
            self._backtest_task = task

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.connected_clients:
            return

        message_json = json.dumps(message, ensure_ascii=False, default=str)

        async with self.lock:
            tasks = [
                self._send_to_client(client, message_json)
                for client in self.connected_clients.copy()
            ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_client(
        self,
        client: WebSocketServerProtocol,
        message: str,
    ):
        try:
            await client.send(message)
        except websockets.ConnectionClosed:
            async with self.lock:
                self.connected_clients.discard(client)

    async def _market_status_monitor(self):
        """Periodically check and broadcast market status changes"""
        while True:
            try:
                await self.market_service.check_and_broadcast_market_status()

                # On market open, start live session tracking
                status = self.market_service.get_market_status()
                if (
                    status["status"] == "open"
                    and not self.storage.is_live_session_active
                ):
                    self.storage.start_live_session()
                    summary = self.storage.load_file("summary") or {}
                    self._session_start_portfolio_value = summary.get(
                        "totalAssetValue",
                        self.storage.initial_cash,
                    )
                    logger.info(
                        "Session start portfolio: "
                        f"${self._session_start_portfolio_value:,.2f}",
                    )
                elif (
                    status["status"] != "open"
                    and self.storage.is_live_session_active
                ):
                    self.storage.end_live_session()
                    self._session_start_portfolio_value = None

                # Update and broadcast live returns if session is active
                if self.storage.is_live_session_active:
                    await self._update_and_broadcast_live_returns()

                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Market status monitor error: {e}")
                await asyncio.sleep(60)

    async def _update_and_broadcast_live_returns(self):
        """Calculate and broadcast live returns for current session"""
        if not self.storage.is_live_session_active:
            return

        # Get current prices and calculate portfolio value
        prices = self.market_service.get_all_prices()
        if not prices or not any(p > 0 for p in prices.values()):
            return

        # Load current internal state to get baseline values
        state = self.storage.load_internal_state()

        # Get latest values from history (if available)
        equity_history = state.get("equity_history", [])
        baseline_history = state.get("baseline_history", [])
        baseline_vw_history = state.get("baseline_vw_history", [])
        momentum_history = state.get("momentum_history", [])

        current_equity = equity_history[-1]["v"] if equity_history else None
        current_baseline = (
            baseline_history[-1]["v"] if baseline_history else None
        )
        current_baseline_vw = (
            baseline_vw_history[-1]["v"] if baseline_vw_history else None
        )
        current_momentum = (
            momentum_history[-1]["v"] if momentum_history else None
        )

        # Update live returns with current values
        point = self.storage.update_live_returns(
            current_equity=current_equity,
            current_baseline=current_baseline,
            current_baseline_vw=current_baseline_vw,
            current_momentum=current_momentum,
        )

        # Broadcast if we have new data
        if point:
            live_returns = self.storage.get_live_returns()
            await self.broadcast(
                {
                    "type": "team_summary",
                    "equity_return": live_returns["equity_return"],
                    "baseline_return": live_returns["baseline_return"],
                    "baseline_vw_return": live_returns["baseline_vw_return"],
                    "momentum_return": live_returns["momentum_return"],
                },
            )

    async def on_strategy_trigger(self, date: str):
        """Handle trading cycle trigger"""
        logger.info(f"Strategy triggered for {date}")

        tickers = self.config.get("tickers", [])

        if self.is_backtest:
            await self._run_backtest_cycle(date, tickers)
        else:
            await self._run_live_cycle(date, tickers)

    async def _run_backtest_cycle(self, date: str, tickers: List[str]):
        """Run backtest cycle with pre-loaded prices"""
        self.market_service.set_backtest_date(date)
        await self.market_service.emit_market_open()

        await self.state_sync.on_cycle_start(date)
        self._dashboard.update(date=date, status="Analyzing...")

        prices = self.market_service.get_open_prices()
        close_prices = self.market_service.get_close_prices()
        market_caps = self._get_market_caps(tickers, date)

        result = await self.pipeline.run_cycle(
            tickers=tickers,
            date=date,
            prices=prices,
            close_prices=close_prices,
            market_caps=market_caps,
        )

        await self.market_service.emit_market_close()
        settlement_result = result.get("settlement_result")
        self._save_cycle_results(result, date, close_prices, settlement_result)
        await self._broadcast_portfolio_updates(result, close_prices)
        await self._finalize_cycle(date)

    async def _run_live_cycle(self, date: str, tickers: List[str]):
        """
        Run live cycle with real market timing.

        - Analysis runs immediately
        - Execution waits for market open
            (or uses current prices if already open)
        - Settlement waits for market close
        """
        # Get actual trading date (might be next trading day if weekend)
        trading_date = self.market_service.get_live_trading_date()
        logger.info(
            f"Live cycle: triggered={date}, trading_date={trading_date}",
        )

        await self.state_sync.on_cycle_start(trading_date)
        self._dashboard.update(date=trading_date, status="Analyzing...")

        market_caps = self._get_market_caps(tickers, trading_date)

        # Run pipeline with async price callbacks
        result = await self.pipeline.run_cycle(
            tickers=tickers,
            date=trading_date,
            market_caps=market_caps,
            get_open_prices_fn=self.market_service.wait_for_open_prices,
            get_close_prices_fn=self.market_service.wait_for_close_prices,
        )

        close_prices = self.market_service.get_all_prices()
        settlement_result = result.get("settlement_result")
        self._save_cycle_results(
            result,
            trading_date,
            close_prices,
            settlement_result,
        )
        await self._broadcast_portfolio_updates(result, close_prices)
        await self._finalize_cycle(trading_date)

    async def _finalize_cycle(self, date: str):
        """Finalize cycle: broadcast state and update dashboard"""
        summary = self.storage.load_file("summary") or {}

        # Include live returns if session is active
        if self.storage.is_live_session_active:
            live_returns = self.storage.get_live_returns()
            summary.update(live_returns)

        await self.state_sync.on_cycle_end(date, portfolio_summary=summary)

        holdings = self.storage.load_file("holdings") or []
        trades = self.storage.load_file("trades") or []
        leaderboard = self.storage.load_file("leaderboard") or []

        if leaderboard:
            await self.state_sync.on_leaderboard_update(leaderboard)

        self._dashboard.update(
            date=date,
            status="Running",
            portfolio=summary,
            holdings=holdings,
            trades=trades,
        )

    def _get_market_caps(
        self,
        tickers: List[str],
        date: str,
    ) -> Dict[str, float]:
        """
        Get market caps for tickers (stub implementation)

        Args:
            tickers: List of tickers
            date: Trading date

        Returns:
            Dict mapping ticker to market cap
        """
        from ..tools.data_tools import get_market_cap

        market_caps = {}
        for ticker in tickers:
            try:
                market_cap = get_market_cap(ticker, date)
                if market_cap:
                    market_caps[ticker] = market_cap
                else:
                    market_caps[ticker] = 1e9
            except Exception:
                market_caps[ticker] = 1e9

        return market_caps

    async def _broadcast_portfolio_updates(
        self,
        result: Dict[str, Any],
        prices: Dict[str, float],
    ):
        portfolio = result.get("portfolio", {})

        if portfolio:
            holdings = FrontendAdapter.build_holdings(portfolio, prices)
            if holdings:
                await self.state_sync.on_holdings_update(holdings)

            stats = FrontendAdapter.build_stats(portfolio, prices)
            if stats:
                await self.state_sync.on_stats_update(stats)

        executed_trades = result.get("executed_trades", [])
        if executed_trades:
            await self.state_sync.on_trades_executed(executed_trades)

    def _save_cycle_results(
        self,
        result: Dict[str, Any],
        date: str,
        prices: Dict[str, float],
        settlement_result: Optional[Dict[str, Any]] = None,
    ):
        portfolio = result.get("portfolio", {})
        executed_trades = result.get("executed_trades", [])

        # Extract baseline values from settlement result
        baseline_values = None
        if settlement_result:
            baseline_values = settlement_result.get("baseline_values")

        if portfolio:
            self.storage.update_dashboard_after_cycle(
                portfolio=portfolio,
                prices=prices,
                date=date,
                executed_trades=executed_trades,
                baseline_values=baseline_values,
            )

    async def _run_backtest_dates(self, dates: List[str]):
        self.state_sync.set_backtest_dates(dates)
        self._dashboard.update(days_total=len(dates), days_completed=0)

        await self.state_sync.on_system_message(
            f"Starting backtest - {len(dates)} trading days",
        )

        try:
            for i, date in enumerate(dates):
                self._dashboard.update(days_completed=i)
                await self.on_strategy_trigger(date=date)
                await asyncio.sleep(0.1)

            await self.state_sync.on_system_message(
                f"Backtest complete - {len(dates)} days",
            )

            # Update dashboard with final state
            summary = self.storage.load_file("summary") or {}
            self._dashboard.update(
                status="Complete",
                portfolio=summary,
                days_completed=len(dates),
            )
            self._dashboard.stop()
            self._dashboard.print_final_summary()
        except Exception as e:
            error_msg = f"Backtest failed: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self.state_sync.on_system_message(error_msg)
            self._dashboard.update(status=f"Failed: {str(e)}")
            self._dashboard.stop()
            raise
        finally:
            self._backtest_task = None

    def _handle_backtest_exception(self, task: asyncio.Task):
        """Handle exceptions from backtest task"""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Backtest task was cancelled")
        except Exception as e:
            logger.error(
                f"Backtest task failed with exception:{type(e).__name__}:{e}",
                exc_info=True,
            )

    def set_backtest_dates(self, dates: List[str]):
        self.state_sync.set_backtest_dates(dates)
        if dates:
            self._backtest_start_date = dates[0]
            self._backtest_end_date = dates[-1]
            self._dashboard.days_total = len(dates)

    def stop(self):
        self.state_sync.save_state()
        self.market_service.stop()
        if self._backtest_task:
            self._backtest_task.cancel()
        if self._market_status_task:
            self._market_status_task.cancel()
        self._dashboard.stop()
