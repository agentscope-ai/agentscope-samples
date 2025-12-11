#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EvoTraders CLI - Command-line interface for the EvoTraders trading system.

This module provides easy-to-use commands for running backtest, live trading,
and frontend development server.
"""
# flake8: noqa: E501
# pylint: disable=R0912, R0915
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

app = typer.Typer(
    name="evotraders",
    help="EvoTraders: A self-evolving multi-agent trading system",
    add_completion=False,
)

console = Console()


def get_project_root() -> Path:
    """Get the project root directory."""
    # Assuming cli.py is in backend/
    return Path(__file__).parent.parent


def handle_history_cleanup(config_name: str, auto_clean: bool = False) -> None:
    """
    Handle cleanup of historical data for a given config.

    Args:
        config_name: Configuration name for the run
        auto_clean: If True, skip confirmation and clean automatically
    """
    # logs_dir = get_project_root() / "logs"
    logs_dir = get_project_root()
    base_data_dir = logs_dir / config_name

    # Check if historical data exists
    if not base_data_dir.exists() or not any(base_data_dir.iterdir()):
        console.print(
            f"\n[dim]No historical data found for config '{config_name}'[/dim]",
        )
        console.print("[dim]   Will start from scratch[/dim]\n")
        return

    console.print("\n[bold yellow]Detected existing run data:[/bold yellow]")
    console.print(f"   Data directory: [cyan]{base_data_dir}[/cyan]")

    # Show directory size
    try:
        total_size = sum(
            f.stat().st_size for f in base_data_dir.rglob("*") if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)
        if size_mb < 1:
            console.print(
                f"   Directory size: [cyan]{total_size / 1024:.1f} KB[/cyan]",
            )
        else:
            console.print(f"   Directory size: [cyan]{size_mb:.1f} MB[/cyan]")
    except Exception:
        pass

    # Show last modified time
    state_dir = base_data_dir / "state"
    if state_dir.exists():
        state_files = list(state_dir.glob("*.json"))
        if state_files:
            last_modified = max(f.stat().st_mtime for f in state_files)
            last_modified_str = datetime.fromtimestamp(last_modified).strftime(
                "%Y-%m-%d %H:%M:%S",
            )
            console.print(f"   Last updated: [cyan]{last_modified_str}[/cyan]")

    console.print()

    # Determine if we should clean
    should_clean = auto_clean
    if not auto_clean:
        should_clean = Confirm.ask(
            "   ﹂ Clear historical data and start fresh?",
            default=False,
        )
    else:
        console.print("[yellow]⚠️  Auto-clean enabled (--clean flag)[/yellow]")
        should_clean = True

    if should_clean:
        console.print("\n[yellow]▩  Cleaning historical data...[/yellow]")

        # Backup important config files if they exist
        backup_files = [".env", "config.json"]
        backed_up = []
        backup_dir = None

        for backup_file in backup_files:
            file_path = base_data_dir / backup_file
            if file_path.exists():
                if backup_dir is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_dir = (
                        base_data_dir.parent
                        / f"{config_name}_backup_{timestamp}"
                    )
                    backup_dir.mkdir(parents=True, exist_ok=True)

                shutil.copy(file_path, backup_dir / backup_file)
                backed_up.append(backup_file)

        if backed_up:
            console.print(
                f"   💾 Backed up config files to: [cyan]{backup_dir}[/cyan]",
            )
            console.print(f"      Files: {', '.join(backed_up)}")

        # Remove the data directory
        try:
            shutil.rmtree(base_data_dir)
            console.print("   ✔ Historical data cleared\n")
        except Exception as e:
            console.print(f"   [red]✗ Error clearing data: {e}[/red]\n")
            raise typer.Exit(1)
    else:
        console.print(
            "\n[dim]  Continuing with existing historical data[/dim]\n",
        )


def run_data_updater(project_root: Path) -> None:
    """Run the historical data updater."""
    console.print("\n[bold]Checking historical data update...[/bold]")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "backend.data.ret_data_updater", "--help"],
            capture_output=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:
            console.print("[cyan]Updating historical data...[/cyan]")
            update_result = subprocess.run(
                [sys.executable, "-m", "backend.data.ret_data_updater"],
                cwd=project_root,
                check=False,
            )

            if update_result.returncode == 0:
                console.print(
                    "[green]✔ Historical data updated successfully[/green]\n",
                )
            else:
                console.print(
                    "[yellow]  Data update failed (might be weekend/holiday)[/yellow]",
                )
                console.print(
                    "[dim]   Will continue with existing data[/dim]\n",
                )
        else:
            console.print(
                "[yellow]  Data updater module not available, skipping update[/yellow]\n",
            )
    except Exception:
        console.print(
            "[yellow]  Data updater check failed, skipping update[/yellow]\n",
        )


@app.command()
def backtest(
    start: Optional[str] = typer.Option(
        None,
        "--start",
        "-s",
        help="Start date for backtest (YYYY-MM-DD)",
    ),
    end: Optional[str] = typer.Option(
        None,
        "--end",
        "-e",
        help="End date for backtest (YYYY-MM-DD)",
    ),
    config_name: str = typer.Option(
        "backtest",
        "--config-name",
        "-c",
        help="Configuration name for this backtest run",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="WebSocket server host",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        "-p",
        help="WebSocket server port",
    ),
    poll_interval: int = typer.Option(
        10,
        "--poll-interval",
        help="Price polling interval in seconds",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Clear historical data before starting",
    ),
    enable_memory: bool = typer.Option(
        False,
        "--enable-memory",
        help="Enable ReMeTaskLongTermMemory for agents (requires MEMORY_API_KEY)",
    ),
):
    """
    Run backtest mode with historical data.

    Example:
        evotraders backtest --start 2025-11-01 --end 2025-12-01
        evotraders backtest --config-name my_strategy --port 9000
        evotraders backtest --clean  # Clear historical data before starting
        evotraders backtest --enable-memory  # Enable long-term memory
    """
    console.print(
        Panel.fit(
            "[bold cyan]EvoTraders Backtest Mode[/bold cyan]",
            border_style="cyan",
        ),
    )

    # Validate dates - required for backtest
    if not start or not end:
        console.print(
            "[red]✗ Both --start and --end dates are required for backtest mode[/red]",
        )
        raise typer.Exit(1)

    try:
        datetime.strptime(start, "%Y-%m-%d")
    except ValueError as exc:
        console.print(
            "[red]✗ Invalid start date format. Use YYYY-MM-DD[/red]",
        )
        raise typer.Exit(1) from exc

    try:
        datetime.strptime(end, "%Y-%m-%d")
    except ValueError as exc:
        console.print(
            "[red]✗ Invalid end date format. Use YYYY-MM-DD[/red]",
        )
        raise typer.Exit(1) from exc

    # Handle historical data cleanup
    handle_history_cleanup(config_name, auto_clean=clean)

    # Display configuration
    console.print("\n[bold]Configuration:[/bold]")
    console.print("   Mode: Backtest")
    console.print(f"   Config: {config_name}")
    console.print(f"   Period: {start} -> {end}")
    console.print(f"   Server: {host}:{port}")
    console.print(f"   Poll Interval: {poll_interval}s")
    console.print(
        f"   Long-term Memory: {'enabled' if enable_memory else 'disabled'}",
    )
    console.print("\nAccess frontend at: [cyan]http://localhost:5173[/cyan]")
    console.print("Press Ctrl+C to stop\n")

    # Change to project root
    project_root = get_project_root()
    os.chdir(project_root)

    # Run data updater
    run_data_updater(project_root)

    # Build command using backend.main
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "backend.main",
        "--mode",
        "backtest",
        "--config-name",
        config_name,
        "--host",
        host,
        "--port",
        str(port),
        "--poll-interval",
        str(poll_interval),
        "--start-date",
        start,
        "--end-date",
        end,
    ]

    if enable_memory:
        cmd.append("--enable-memory")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Backtest stopped by user[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(
            f"\n[red]Backtest failed with exit code {e.returncode}[/red]",
        )
        raise typer.Exit(1)


@app.command()
def live(
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use mock mode with simulated prices (for testing)",
    ),
    config_name: str = typer.Option(
        "live",
        "--config-name",
        "-c",
        help="Configuration name for this live run",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="WebSocket server host",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        "-p",
        help="WebSocket server port",
    ),
    trigger_time: str = typer.Option(
        "now",
        "--trigger-time",
        "-t",
        help="Trigger time in LOCAL timezone (HH:MM), or 'now' to run immediately",
    ),
    poll_interval: int = typer.Option(
        10,
        "--poll-interval",
        help="Price polling interval in seconds",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Clear historical data before starting",
    ),
    enable_memory: bool = typer.Option(
        False,
        "--enable-memory",
        help="Enable ReMeTaskLongTermMemory for agents (requires MEMORY_API_KEY)",
    ),
):
    """
    Run live trading mode with real-time data.

    Example:
        evotraders live                    # Run immediately (default)
        evotraders live --mock             # Mock mode
        evotraders live -t 22:30           # Run at 22:30 local time daily
        evotraders live --trigger-time now # Run immediately
        evotraders live --clean            # Clear historical data before starting
    """
    mode_name = "MOCK" if mock else "LIVE"
    console.print(
        Panel.fit(
            f"[bold cyan]EvoTraders {mode_name} Mode[/bold cyan]",
            border_style="cyan",
        ),
    )

    # Check for required API key in live mode
    if not mock:
        env_file = get_project_root() / ".env"
        if not env_file.exists():
            console.print("\n[yellow]Warning: .env file not found[/yellow]")
            console.print("Creating from template...\n")
            template = get_project_root() / "env.template"
            if template.exists():
                shutil.copy(template, env_file)
                console.print("[green].env file created[/green]")
                console.print(
                    "\n[red]Error: Please edit .env and set FINNHUB_API_KEY[/red]",
                )
                console.print(
                    "Get your free API key at: https://finnhub.io/register\n",
                )
            else:
                console.print("[red]Error: env.template not found[/red]")
            raise typer.Exit(1)

    # Handle historical data cleanup
    handle_history_cleanup(config_name, auto_clean=clean)

    # Convert local time to NYSE time
    nyse_tz = ZoneInfo("America/New_York")
    local_tz = datetime.now().astimezone().tzinfo
    local_now = datetime.now()
    nyse_now = datetime.now(nyse_tz)

    # Convert trigger time from local to NYSE
    if trigger_time.lower() == "now":
        nyse_trigger_time = "now"
    else:
        local_trigger = datetime.strptime(trigger_time, "%H:%M")
        local_trigger_dt = local_now.replace(
            hour=local_trigger.hour,
            minute=local_trigger.minute,
            second=0,
            microsecond=0,
        )
        local_trigger_aware = local_trigger_dt.astimezone(local_tz)
        nyse_trigger_dt = local_trigger_aware.astimezone(nyse_tz)
        nyse_trigger_time = nyse_trigger_dt.strftime("%H:%M")

    # Display time info
    console.print("\n[bold]Time Info:[/bold]")
    console.print(f"   Local Time: {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(
        f"   NYSE Time:  {nyse_now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
    )
    if nyse_trigger_time == "now":
        console.print("   Trigger:    [green]NOW (immediate)[/green]")
    else:
        console.print(
            f"   Trigger:    {trigger_time} local = {nyse_trigger_time} NYSE",
        )

    # Display configuration
    console.print("\n[bold]Configuration:[/bold]")
    if mock:
        console.print("   Mode: [yellow]MOCK[/yellow] (Simulated prices)")
    else:
        console.print(
            "   Mode: [green]LIVE[/green] (Real-time prices via Finnhub)",
        )
    console.print(f"   Config: {config_name}")
    console.print(f"   Server: {host}:{port}")
    console.print(f"   Poll Interval: {poll_interval}s")
    console.print(
        f"   Long-term Memory: {'enabled' if enable_memory else 'disabled'}",
    )

    console.print("\nAccess frontend at: [cyan]http://localhost:5173[/cyan]")
    console.print("Press Ctrl+C to stop\n")

    # Change to project root
    project_root = get_project_root()
    os.chdir(project_root)

    # Data update (if not mock mode)
    if not mock:
        run_data_updater(project_root)
    else:
        console.print(
            "\n[dim]Mock mode enabled - skipping data update[/dim]\n",
        )

    # Build command using backend.main
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "backend.main",
        "--mode",
        "live",
        "--config-name",
        config_name,
        "--host",
        host,
        "--port",
        str(port),
        "--poll-interval",
        str(poll_interval),
        "--trigger-time",
        nyse_trigger_time,
    ]

    if mock:
        cmd.append("--mock")
    if enable_memory:
        cmd.append("--enable-memory")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Live server stopped by user[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(
            f"\n[red]Live server failed with exit code {e.returncode}[/red]",
        )
        raise typer.Exit(1) from e


@app.command()
def frontend(
    port: int = typer.Option(
        8765,
        "--ws-port",
        "-p",
        help="WebSocket server port to connect to",
    ),
    host_mode: bool = typer.Option(
        False,
        "--host",
        help="Allow external access (default: localhost only)",
    ),
):
    """
    Start the frontend development server.

    Example:
        evotraders frontend
        evotraders frontend --ws-port 8765
        evotraders frontend --ws-port 8765 --host
    """
    console.print(
        Panel.fit(
            "[bold cyan]EvoTraders Frontend[/bold cyan]",
            border_style="cyan",
        ),
    )

    project_root = get_project_root()
    frontend_dir = project_root / "frontend"

    # Check if frontend directory exists
    if not frontend_dir.exists():
        console.print(
            f"\n[red]Error: Frontend directory not found: {frontend_dir}[/red]",
        )
        raise typer.Exit(1)

    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        console.print("\n[yellow]Installing frontend dependencies...[/yellow]")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
            )
            console.print("[green]Dependencies installed[/green]\n")
        except subprocess.CalledProcessError as exc:
            console.print("\n[red]Error: Failed to install dependencies[/red]")
            console.print("Make sure Node.js and npm are installed")
            raise typer.Exit(1) from exc

    # Set WebSocket URL environment variable
    ws_url = f"ws://localhost:{port}"
    env = os.environ.copy()
    env["VITE_WS_URL"] = ws_url

    # Display configuration
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"   WebSocket URL: {ws_url}")
    console.print("   Frontend Port: 5173 (Vite default)")
    if host_mode:
        console.print("   Access: External allowed")
    else:
        console.print("   Access: Localhost only")
    console.print("\nAccess at: [cyan]http://localhost:5173[/cyan]")
    console.print("Press Ctrl+C to stop\n")

    # Choose npm command
    npm_cmd = ["npm", "run", "dev:host" if host_mode else "dev"]

    try:
        subprocess.run(
            npm_cmd,
            cwd=frontend_dir,
            env=env,
            check=True,
        )
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Frontend stopped by user[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(
            f"\n[red]Frontend failed with exit code {e.returncode}[/red]",
        )
        raise typer.Exit(1)


@app.command()
def version():
    """Show the version of EvoTraders."""
    console.print(
        "\n[bold cyan]EvoTraders[/bold cyan] version [green]0.1.0[/green]\n",
    )


@app.callback()
def main():
    """
    EvoTraders: A self-evolving multi-agent trading system

    Use 'evotraders --help' to see available commands.
    """


if __name__ == "__main__":
    app()
