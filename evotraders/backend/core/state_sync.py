# -*- coding: utf-8 -*-
"""
StateSync - Centralized state synchronization between agents and frontend
Handles real-time updates, persistence, and replay support
"""
# pylint: disable=R0904
import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..services.storage import StorageService

logger = logging.getLogger(__name__)


class StateSync:
    """
    Central event dispatcher for agent-frontend synchronization

    Responsibilities:
    1. Receive events from agents/pipeline
    2. Persist to storage (feed_history)
    3. Broadcast to frontend via WebSocket
    4. Support replay from saved state
    """

    def __init__(
        self,
        storage: StorageService,
        broadcast_fn: Optional[Callable] = None,
    ):
        """
        Initialize StateSync

        Args:
            storage: Storage service for persistence
            broadcast_fn: Async broadcast function - async def broadcast(event: dict) # noqa: E501
        """
        self.storage = storage
        self._broadcast_fn = broadcast_fn
        self._state: Dict[str, Any] = {}
        self._enabled = True
        self._simulation_date: Optional[str] = None  # For backtest timestamps

    def set_simulation_date(self, date: str):
        """Set current simulation date for backtest-compatible timestamps"""
        self._simulation_date = date

    def _get_timestamp_ms(self) -> int:
        """
        Get timestamp in milliseconds.
        Uses simulation date if set (backtest mode), otherwise current time.
        """
        if self._simulation_date:
            # Parse date and use market close time (16:00) for backtest
            dt = datetime.strptime(
                f"{self._simulation_date}",
                "%Y-%m-%d",
            )
            return int(dt.timestamp() * 1000)
        return int(datetime.now().timestamp() * 1000)

    def load_state(self):
        """Load server state from storage"""
        self._state = self.storage.load_server_state()
        self.storage.update_server_state_from_dashboard(self._state)
        logger.info(
            f"StateSync loaded: {len(self._state.get('feed_history', []))} feeds",  # noqa: E501
        )

    def save_state(self):
        """Save current state to storage"""
        self.storage.save_server_state(self._state)

    @property
    def state(self) -> Dict[str, Any]:
        """Get current state"""
        return self._state

    def set_broadcast_fn(self, fn: Callable):
        """Set broadcast function (supports late binding)"""
        self._broadcast_fn = fn

    def update_state(self, key: str, value: Any):
        """Update a state field"""
        self._state[key] = value

    async def emit(self, event: Dict[str, Any], persist: bool = True):
        """
        Emit an event - persists and broadcasts

        Args:
            event: Event dictionary, must contain "type"
            persist: Whether to persist to feed_history
        """
        if not self._enabled:
            return

        # Ensure timestamp exists (use simulation date if in backtest mode)
        if "timestamp" not in event:
            if self._simulation_date:
                event["timestamp"] = f"{self._simulation_date}"
            else:
                event["timestamp"] = datetime.now().isoformat()

        # Persist to feed_history
        if persist:
            self.storage.add_feed_message(self._state, event)
            self.save_state()

        # Broadcast to frontend
        if self._broadcast_fn:
            await self._broadcast_fn(event)

    # ========== Agent Events ==========

    async def on_agent_complete(
        self,
        agent_id: str,
        content: str,
        **extra,
    ):
        """
        Called when an agent finishes its reply

        Args:
            agent_id: Agent identifier (e.g., "fundamentals_analyst")
            content: Agent's output content
            **extra: Additional fields to include
        """
        ts_ms = self._get_timestamp_ms()

        await self.emit(
            {
                "type": "agent_message",
                "agentId": agent_id,
                "content": content,
                "ts": ts_ms,
                **extra,
            },
        )

        logger.info(f"Agent complete: {agent_id}")

    async def on_memory_retrieved(
        self,
        agent_id: str,
        content: str,
    ):
        """
        Called when long-term memory is retrieved for an agent

        Args:
            agent_id: Agent identifier
            content: Retrieved memory content
        """
        ts_ms = self._get_timestamp_ms()

        await self.emit(
            {
                "type": "memory",
                "agentId": agent_id,
                "content": content,
                "ts": ts_ms,
            },
        )

        logger.info(f"Memory retrieved for: {agent_id}")

    # ========== Conference Events ==========

    async def on_conference_start(self, title: str, date: str):
        """Called when conference discussion starts"""
        ts_ms = self._get_timestamp_ms()

        await self.emit(
            {
                "type": "conference_start",
                "title": title,
                "date": date,
                "ts": ts_ms,
            },
        )

        logger.info(f"Conference started: {title}")

    async def on_conference_cycle_start(self, cycle: int, total_cycles: int):
        """Called when a conference cycle starts"""
        await self.emit(
            {
                "type": "conference_cycle_start",
                "cycle": cycle,
                "totalCycles": total_cycles,
            },
            persist=False,
        )

    async def on_conference_message(self, agent_id: str, content: str):
        """Called when an agent speaks during conference"""
        ts_ms = self._get_timestamp_ms()

        await self.emit(
            {
                "type": "conference_message",
                "agentId": agent_id,
                "content": content,
                "ts": ts_ms,
            },
        )

    async def on_conference_cycle_end(self, cycle: int):
        """Called when a conference cycle ends"""
        await self.emit(
            {
                "type": "conference_cycle_end",
                "cycle": cycle,
            },
            persist=False,
        )

    async def on_conference_end(self):
        """Called when conference discussion ends"""
        ts_ms = self._get_timestamp_ms()

        await self.emit(
            {
                "type": "conference_end",
                "ts": ts_ms,
            },
        )

        logger.info("Conference ended")

    # ========== Cycle Events ==========

    async def on_cycle_start(self, date: str):
        """Called at start of trading cycle"""
        self._state["current_date"] = date
        self._state["status"] = "running"
        self.set_simulation_date(
            date,
        )  # Set for backtest-compatible timestamps

        await self.emit(
            {
                "type": "day_start",
                "date": date,
                "progress": self._calculate_progress(),
            },
        )
        # await self.emit(
        #     {
        #         "type": "system",
        #         "content": f"Starting trading analysis for {date}",
        #     },
        # )

    async def on_cycle_end(self, date: str, portfolio_summary: Dict = None):
        """Called at end of trading cycle"""
        # Update completed count
        self._state["trading_days_completed"] = (
            self._state.get("trading_days_completed", 0) + 1
        )

        # Broadcast team_summary if available
        if portfolio_summary:
            summary_data = {
                "type": "team_summary",
                "balance": portfolio_summary.get(
                    "balance",
                    portfolio_summary.get("total_value", 0),
                ),
                "pnlPct": portfolio_summary.get(
                    "pnlPct",
                    portfolio_summary.get("pnl_percent", 0),
                ),
                "equity": portfolio_summary.get("equity", []),
                "baseline": portfolio_summary.get("baseline", []),
                "baseline_vw": portfolio_summary.get("baseline_vw", []),
                "momentum": portfolio_summary.get("momentum", []),
            }

            # Include live returns if available
            if portfolio_summary.get("equity_return"):
                summary_data["equity_return"] = portfolio_summary[
                    "equity_return"
                ]
            if portfolio_summary.get("baseline_return"):
                summary_data["baseline_return"] = portfolio_summary[
                    "baseline_return"
                ]
            if portfolio_summary.get("baseline_vw_return"):
                summary_data["baseline_vw_return"] = portfolio_summary[
                    "baseline_vw_return"
                ]
            if portfolio_summary.get("momentum_return"):
                summary_data["momentum_return"] = portfolio_summary[
                    "momentum_return"
                ]

            if "portfolio" not in self._state:
                self._state["portfolio"] = {}

            self._state["portfolio"].update(
                {
                    "total_value": summary_data["balance"],
                    "pnl_percent": summary_data["pnlPct"],
                    "equity": summary_data["equity"],
                    "baseline": summary_data["baseline"],
                    "baseline_vw": summary_data["baseline_vw"],
                    "momentum": summary_data["momentum"],
                },
            )

            if summary_data.get("equity_return"):
                self._state["portfolio"]["equity_return"] = summary_data[
                    "equity_return"
                ]
            if summary_data.get("baseline_return"):
                self._state["portfolio"]["baseline_return"] = summary_data[
                    "baseline_return"
                ]
            if summary_data.get("baseline_vw_return"):
                self._state["portfolio"]["baseline_vw_return"] = summary_data[
                    "baseline_vw_return"
                ]
            if summary_data.get("momentum_return"):
                self._state["portfolio"]["momentum_return"] = summary_data[
                    "momentum_return"
                ]

            await self.emit(summary_data, persist=True)

        await self.emit(
            {
                "type": "day_complete",
                "date": date,
                "progress": self._calculate_progress(),
            },
        )

        self.save_state()

    # ========== Portfolio Events ==========

    async def on_holdings_update(self, holdings: List[Dict]):
        """Called when holdings change"""
        self._state["holdings"] = holdings
        await self.emit(
            {
                "type": "team_holdings",
                "data": holdings,
            },
            persist=False,
        )  # Holdings change frequently, don't store all in feed_history

    async def on_trades_executed(self, trades: List[Dict]):
        """Called when trades are executed"""
        # Update state with new trades
        existing = self._state.get("trades", [])
        self._state["trades"] = trades + existing

        await self.emit(
            {
                "type": "team_trades",
                "mode": "incremental",
                "data": trades,
            },
            persist=False,
        )

    async def on_stats_update(self, stats: Dict):
        """Called when stats are updated"""
        self._state["stats"] = stats
        await self.emit(
            {
                "type": "team_stats",
                "data": stats,
            },
            persist=False,
        )

    async def on_leaderboard_update(self, leaderboard: List[Dict]):
        """Called when leaderboard is updated"""
        self._state["leaderboard"] = leaderboard
        await self.emit(
            {
                "type": "team_leaderboard",
                "data": leaderboard,
            },
            persist=False,
        )

    # ========== System Events ==========

    async def on_system_message(self, content: str):
        """Emit a system message"""
        await self.emit(
            {
                "type": "system",
                "content": content,
            },
        )

    # ========== Replay Support ==========

    async def replay_feed_history(self, delay_ms: int = 100):
        """
        Replay events from feed_history

        Useful for: frontend reconnection or restoring from saved state
        """
        feed_history = self._state.get("feed_history", [])

        # feed_history is newest-first, need to reverse for chronological replay # noqa: E501
        for event in reversed(feed_history):
            if self._broadcast_fn:
                await self._broadcast_fn(event)
            await asyncio.sleep(delay_ms / 1000)

        logger.info(f"Replayed {len(feed_history)} events")

    def get_initial_state_payload(
        self,
        include_dashboard: bool = True,
    ) -> Dict[str, Any]:
        """
        Build initial state payload for new client connections

        Args:
            include_dashboard: Whether to load dashboard files

        Returns:
            Dictionary suitable for sending to frontend
        """
        payload = {
            "server_mode": self._state.get("server_mode", "live"),
            "is_mock_mode": self._state.get("is_mock_mode", False),
            "is_backtest": self._state.get("is_backtest", False),
            "feed_history": self._state.get("feed_history", []),
            "current_date": self._state.get("current_date"),
            "trading_days_total": self._state.get("trading_days_total", 0),
            "trading_days_completed": self._state.get(
                "trading_days_completed",
                0,
            ),
            "holdings": self._state.get("holdings", []),
            "trades": self._state.get("trades", []),
            "stats": self._state.get("stats", {}),
            "leaderboard": self._state.get("leaderboard", []),
            "portfolio": self._state.get("portfolio", {}),
            "realtime_prices": self._state.get("realtime_prices", {}),
        }

        if include_dashboard:
            payload["dashboard"] = {
                "summary": self.storage.load_file("summary"),
                "holdings": self.storage.load_file("holdings"),
                "stats": self.storage.load_file("stats"),
                "trades": self.storage.load_file("trades"),
                "leaderboard": self.storage.load_file("leaderboard"),
            }

        return payload

    def _calculate_progress(self) -> float:
        """Calculate backtest progress percentage"""
        total = self._state.get("trading_days_total", 0)
        completed = self._state.get("trading_days_completed", 0)
        return completed / total if total > 0 else 0.0

    def set_backtest_dates(self, dates: List[str]):
        """Set total trading days for backtest progress tracking"""
        self._state["trading_days_total"] = len(dates)
        self._state["trading_days_completed"] = 0
