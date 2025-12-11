# -*- coding: utf-8 -*-
"""
Storage Service - Data persistence and dashboard file management
Handles reading/writing dashboard JSON files and portfolio state
"""
# pylint: disable=R0904
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageService:
    """
    Storage service for data persistence

    Responsibilities:
    1. Load/save dashboard JSON files
        (summary, holdings, stats, trades, leaderboard)
    2. Load/save internal state (_internal_state.json)
    3. Load/save server state (server_state.json) with feed history
    4. Manage portfolio state persistence
    5. Support loading from saved state to resume execution
    """

    def __init__(
        self,
        dashboard_dir: Path,
        initial_cash: float = 100000.0,
        config_name: str = "mock",
    ):
        """
        Initialize storage service

        Args:
            dashboard_dir: Directory for dashboard files
            initial_cash: Initial cash amount
            config_name: Configuration name for state directory
        """
        self.dashboard_dir = Path(dashboard_dir)
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)
        self.initial_cash = initial_cash
        self.config_name = config_name

        # Dashboard file paths
        self.files = {
            "summary": self.dashboard_dir / "summary.json",
            "holdings": self.dashboard_dir / "holdings.json",
            "stats": self.dashboard_dir / "stats.json",
            "trades": self.dashboard_dir / "trades.json",
            "leaderboard": self.dashboard_dir / "leaderboard.json",
        }

        # Internal state file
        self.internal_state_file = self.dashboard_dir / "_internal_state.json"

        # Server state directory and file
        self.state_dir = self.dashboard_dir.parent / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.server_state_file = self.state_dir / "server_state.json"

        # Feed history (for agent messages)
        self.max_feed_history = 200

        # File modification time cache (for change detection)
        self.file_mtimes: Dict[str, float] = {}

        # Live returns tracking (for current trading session)
        self._session_start_equity: Optional[float] = None
        self._session_start_baseline: Optional[float] = None
        self._session_start_baseline_vw: Optional[float] = None
        self._session_start_momentum: Optional[float] = None
        self._live_return_history: List[Dict[str, Any]] = []

        logger.info(f"Storage service initialized: {self.dashboard_dir}")

    def load_file(self, file_type: str) -> Optional[Any]:
        """
        Load dashboard JSON file

        Args:
            file_type: One of: summary, holdings, stats, trades, leaderboard

        Returns:
            Loaded data or None if file doesn't exist
        """
        file_path = self.files.get(file_type)
        if not file_path or not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {file_type}.json: {e}")
            return None

    def save_file(self, file_type: str, data: Any):
        """
        Save dashboard JSON file

        Args:
            file_type: One of: summary, holdings, stats, trades, leaderboard
            data: Data to save
        """
        file_path = self.files.get(file_type)
        if not file_path:
            logger.error(f"Unknown file type: {file_type}")
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save {file_type}.json: {e}")

    def check_file_updates(self) -> Dict[str, bool]:
        """
        Check which dashboard files have been updated since last check

        Returns:
            Dictionary mapping file_type to whether it was updated
        """
        updated = {}

        for file_type, file_path in self.files.items():
            if not file_path.exists():
                updated[file_type] = False
                continue

            try:
                current_mtime = file_path.stat().st_mtime
                last_mtime = self.file_mtimes.get(file_type, 0)

                if current_mtime > last_mtime:
                    updated[file_type] = True
                    self.file_mtimes[file_type] = current_mtime
                else:
                    updated[file_type] = False
            except Exception as e:
                logger.error(f"Failed to check file update ({file_type}): {e}")
                updated[file_type] = False

        return updated

    def load_internal_state(self) -> Dict[str, Any]:
        """
        Load internal state from file

        Returns:
            Internal state dictionary with default values
        """
        default_state = {
            "baseline_state": {"initialized": False, "initial_allocation": {}},
            "baseline_vw_state": {
                "initialized": False,
                "initial_allocation": {},
            },
            "momentum_state": {
                "positions": {},
                "cash": 0.0,
                "initialized": False,
            },
            "equity_history": [],
            "baseline_history": [],
            "baseline_vw_history": [],
            "momentum_history": [],
            "price_history": {},
            "portfolio_state": {
                "cash": self.initial_cash,
                "positions": {},
                "margin_used": 0.0,
            },
            "all_trades": [],
            "daily_position_history": {},
        }

        if not self.internal_state_file.exists():
            return default_state

        try:
            with open(self.internal_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Merge with defaults
            for key, value in default_state.items():
                data.setdefault(key, value)

            logger.info("Loaded internal state from file")
            return data

        except Exception as e:
            logger.warning(
                f"Failed to load internal state, using defaults: {e}",
            )
            return default_state

    def save_internal_state(self, state: Dict[str, Any]):
        """
        Save internal state to file

        Args:
            state: Internal state dictionary
        """
        if not state:
            return

        try:
            with open(self.internal_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save internal state: {e}")

    def load_portfolio_state(self) -> Dict[str, Any]:
        """
        Load portfolio state from internal state

        Returns:
            Portfolio state dictionary: {cash, positions, margin_used}
        """
        internal_state = self.load_internal_state()
        portfolio_state = internal_state.get("portfolio_state", {})

        return {
            "cash": portfolio_state.get("cash", self.initial_cash),
            "positions": portfolio_state.get("positions", {}),
            "margin_used": portfolio_state.get("margin_used", 0.0),
            "margin_requirement": 0.25,  # Default 25% margin requirement
        }

    def save_portfolio_state(self, portfolio: Dict[str, Any]):
        """
        Save portfolio state to internal state

        Args:
            portfolio: Portfolio dictionary
        """
        internal_state = self.load_internal_state()
        internal_state["portfolio_state"] = {
            "cash": portfolio.get("cash", 0.0),
            "positions": portfolio.get("positions", {}),
            "margin_used": portfolio.get("margin_used", 0.0),
        }
        self.save_internal_state(internal_state)

    def initialize_empty_dashboard(self):
        """Initialize empty dashboard files with default values"""
        # Summary
        self.save_file(
            "summary",
            {
                "totalAssetValue": self.initial_cash,
                "totalReturn": 0.0,
                "cashPosition": self.initial_cash,
                "tickerWeights": {},
                "totalTrades": 0,
                "pnlPct": 0.0,
                "balance": self.initial_cash,
                "equity": [],
                "baseline": [],
                "baseline_vw": [],
                "momentum": [],
            },
        )

        # Holdings
        self.save_file("holdings", [])

        # Stats
        self.save_file(
            "stats",
            {
                "totalAssetValue": self.initial_cash,
                "totalReturn": 0.0,
                "cashPosition": self.initial_cash,
                "tickerWeights": {},
                "totalTrades": 0,
                "winRate": 0.0,
                "bullBear": {
                    "bull": {"n": 0, "win": 0},
                    "bear": {"n": 0, "win": 0},
                },
            },
        )

        # Trades
        self.save_file("trades", [])

        # Leaderboard with model info
        self.generate_leaderboard()

        logger.info("Initialized empty dashboard")

    def generate_leaderboard(self):
        """Generate leaderboard with agent model info from environment"""
        from ..config.constants import AGENT_CONFIG
        from ..llm.models import get_agent_model_info

        leaderboard = []
        ranking_entries = []
        team_entries = []

        for agent_id, config in AGENT_CONFIG.items():
            model_name, model_provider = get_agent_model_info(agent_id)

            entry = {
                "agentId": agent_id,
                "name": config["name"],
                "role": config["role"],
                "avatar": config["avatar"],
                "rank": None if config["is_team_role"] else 0,
                "winRate": None,
                "bull": {"n": 0, "win": 0, "unknown": 0},
                "bear": {"n": 0, "win": 0, "unknown": 0},
                "logs": [],
                "signals": [],
                "modelName": model_name,
                "modelProvider": model_provider,
            }

            if config["is_team_role"]:
                team_entries.append(entry)
            else:
                ranking_entries.append(entry)

        leaderboard = team_entries + ranking_entries
        self.save_file("leaderboard", leaderboard)
        logger.info("Leaderboard generated with model info")

    def update_leaderboard_model_info(self):
        """
        Update model info in existing leaderboard (preserves performance data)
        """
        from ..config.constants import AGENT_CONFIG
        from ..llm.models import get_agent_model_info

        existing = self.load_file("leaderboard") or []

        if not existing:
            self.generate_leaderboard()
            return

        for entry in existing:
            agent_id = entry.get("agentId")
            if agent_id and agent_id in AGENT_CONFIG:
                model_name, model_provider = get_agent_model_info(agent_id)
                entry["modelName"] = model_name
                entry["modelProvider"] = model_provider

        self.save_file("leaderboard", existing)
        logger.info("Leaderboard model info updated")

    def get_current_timestamp_ms(self, date: str = None) -> int:
        """
        Get timestamp in milliseconds from date string or current time

        Args:
            date: Optional date string (YYYY-MM-DD) for backtest compatibility.
                  Uses market close time (16:00) for the timestamp.

        Returns:
            Timestamp in milliseconds
        """
        if date:
            # Parse date and use market close time (16:00) for backtest
            dt = datetime.strptime(f"{date} 16:00:00", "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp() * 1000)
        return int(datetime.now().timestamp() * 1000)

    def calculate_portfolio_value(
        self,
        portfolio: Dict[str, Any],
        prices: Dict[str, float],
    ) -> float:
        """
        Calculate total portfolio value (net asset value)

        Args:
            portfolio: Portfolio state with cash and positions
            prices: Current prices for each ticker

        Returns:
            Total portfolio value
        """
        cash = portfolio.get("cash", 0.0)
        margin_used = portfolio.get("margin_used", 0.0)
        total = cash + margin_used

        positions = portfolio.get("positions", {})
        for ticker, position in positions.items():
            price = prices.get(ticker, 0)
            if price > 0:
                long_qty = position.get("long", 0)
                short_qty = position.get("short", 0)
                total += long_qty * price
                total -= short_qty * price

        return total

    def update_dashboard_after_cycle(
        self,
        portfolio: Dict[str, Any],
        prices: Dict[str, float],
        date: str,
        executed_trades: List[Dict[str, Any]] = None,
        baseline_values: Optional[Dict[str, float]] = None,
    ):
        """
        Update all dashboard files after a trading cycle

        Args:
            portfolio: Current portfolio state
            prices: Current prices for each ticker
            date: Trading date (YYYY-MM-DD)
            executed_trades: List of executed trades
            [{ticker, action, quantity, price}]
            baseline_values: Optional baseline portfolio values from settlement
                {equal_weight, market_cap_weighted, momentum}
        """
        # Use provided date for timestamp (backtest compatible)
        timestamp_ms = self.get_current_timestamp_ms(date)

        net_value = self.calculate_portfolio_value(portfolio, prices)

        state = self.load_internal_state()

        # Initialize all histories
        for key in [
            "equity_history",
            "baseline_history",
            "baseline_vw_history",
            "momentum_history",
        ]:
            if key not in state:
                state[key] = []

        # Add initial points if empty (all histories should start together)
        if len(state["equity_history"]) == 0:
            initial_point = {
                "t": timestamp_ms - 86400000,
                "v": round(self.initial_cash, 2),
            }
            state["equity_history"].append(initial_point)
            state["baseline_history"].append(initial_point.copy())
            state["baseline_vw_history"].append(initial_point.copy())
            state["momentum_history"].append(initial_point.copy())

        # Add current data points - all histories updated together
        state["equity_history"].append(
            {
                "t": timestamp_ms,
                "v": round(net_value, 2),
            },
        )

        # If baseline_values provided, use them;
        # otherwise forward-fill from last value
        if baseline_values:
            state["baseline_history"].append(
                {
                    "t": timestamp_ms,
                    "v": round(
                        baseline_values.get("equal_weight", self.initial_cash),
                        2,
                    ),
                },
            )
            state["baseline_vw_history"].append(
                {
                    "t": timestamp_ms,
                    "v": round(
                        baseline_values.get(
                            "market_cap_weighted",
                            self.initial_cash,
                        ),
                        2,
                    ),
                },
            )
            state["momentum_history"].append(
                {
                    "t": timestamp_ms,
                    "v": round(
                        baseline_values.get("momentum", self.initial_cash),
                        2,
                    ),
                },
            )
        else:
            # Forward-fill: use last known value
            last_baseline = (
                state["baseline_history"][-1]["v"]
                if state["baseline_history"]
                else self.initial_cash
            )
            last_baseline_vw = (
                state["baseline_vw_history"][-1]["v"]
                if state["baseline_vw_history"]
                else self.initial_cash
            )
            last_momentum = (
                state["momentum_history"][-1]["v"]
                if state["momentum_history"]
                else self.initial_cash
            )

            state["baseline_history"].append(
                {"t": timestamp_ms, "v": last_baseline},
            )
            state["baseline_vw_history"].append(
                {"t": timestamp_ms, "v": last_baseline_vw},
            )
            state["momentum_history"].append(
                {"t": timestamp_ms, "v": last_momentum},
            )

        state["portfolio_state"] = {
            "cash": portfolio.get("cash", 0.0),
            "positions": portfolio.get("positions", {}),
            "margin_used": portfolio.get("margin_used", 0.0),
        }

        # Update trades with structured data
        if executed_trades:
            if "all_trades" not in state:
                state["all_trades"] = []

            for i, trade in enumerate(executed_trades):
                action = trade.get("action", "hold")
                side = (
                    "LONG"
                    if action == "long"
                    else "SHORT"
                    if action == "short"
                    else "HOLD"
                )

                trade_id = (
                    f"t_{date.replace('-', '')}_{trade.get('ticker', '')}_{i}"
                )
                state["all_trades"].append(
                    {
                        "id": trade_id,
                        "ts": timestamp_ms,
                        "trading_date": date,
                        "side": side,
                        "ticker": trade.get("ticker", ""),
                        "qty": trade.get("quantity", 0),
                        "price": round(trade.get("price", 0), 2),
                    },
                )

        state["last_update_date"] = date

        self.save_internal_state(state)

        self._generate_summary(state, net_value, prices)
        self._generate_holdings(state, prices)
        self._generate_stats(state, net_value)
        self._generate_trades(state)

        logger.info(f"Dashboard updated: net_value=${net_value:,.2f}")

    def _generate_summary(
        self,
        state: Dict[str, Any],
        net_value: float,
        prices: Dict[str, float],
    ):
        """Generate summary.json"""
        portfolio_state = state.get("portfolio_state", {})
        cash = portfolio_state.get("cash", self.initial_cash)

        # Calculate ticker weights
        positions = portfolio_state.get("positions", {})
        ticker_weights = {}

        for ticker, position in positions.items():
            price = prices.get(ticker, 0)
            if price > 0 and net_value > 0:
                long_qty = position.get("long", 0)
                short_qty = position.get("short", 0)
                position_value = (long_qty - short_qty) * price
                ticker_weights[ticker] = round(position_value / net_value, 4)

        # Calculate return
        total_return = (
            (net_value - self.initial_cash) / self.initial_cash
        ) * 100

        summary = {
            "totalAssetValue": round(net_value, 2),
            "totalReturn": round(total_return, 2),
            "cashPosition": round(cash, 2),
            "tickerWeights": ticker_weights,
            "totalTrades": len(state.get("all_trades", [])),
            "pnlPct": round(total_return, 2),
            "balance": round(net_value, 2),
            "equity": state.get("equity_history", []),
            "baseline": state.get("baseline_history", []),
            "baseline_vw": state.get("baseline_vw_history", []),
            "momentum": state.get("momentum_history", []),
        }

        self.save_file("summary", summary)

    def _generate_holdings(
        self,
        state: Dict[str, Any],
        prices: Dict[str, float],
    ):
        """Generate holdings.json"""
        portfolio_state = state.get("portfolio_state", {})
        positions = portfolio_state.get("positions", {})
        cash = portfolio_state.get("cash", self.initial_cash)
        margin_used = portfolio_state.get("margin_used", 0.0)

        # Calculate total value
        total_value = cash + margin_used
        for ticker, position in positions.items():
            price = prices.get(ticker, 0)
            if price > 0:
                long_qty = position.get("long", 0)
                short_qty = position.get("short", 0)
                total_value += (long_qty - short_qty) * price

        holdings = []

        # Add stock positions
        for ticker, position in positions.items():
            price = prices.get(ticker, 0)
            long_qty = position.get("long", 0)
            short_qty = position.get("short", 0)
            net_qty = long_qty - short_qty

            if net_qty != 0 and price > 0:
                market_value = net_qty * price
                weight = (
                    abs(market_value) / total_value if total_value > 0 else 0
                )

                holdings.append(
                    {
                        "ticker": ticker,
                        "quantity": net_qty,
                        "currentPrice": round(price, 2),
                        "marketValue": round(market_value, 2),
                        "weight": round(weight, 4),
                    },
                )

        # Add cash
        cash_weight = cash / total_value if total_value > 0 else 0
        holdings.append(
            {
                "ticker": "CASH",
                "quantity": 1,
                "currentPrice": round(cash, 2),
                "marketValue": round(cash, 2),
                "weight": round(cash_weight, 4),
            },
        )

        # Sort by weight
        holdings.sort(key=lambda x: abs(x["weight"]), reverse=True)

        self.save_file("holdings", holdings)

    def _generate_stats(self, state: Dict[str, Any], net_value: float):
        """Generate stats.json"""
        portfolio_state = state.get("portfolio_state", {})
        cash = portfolio_state.get("cash", self.initial_cash)
        total_return = (
            (net_value - self.initial_cash) / self.initial_cash
        ) * 100

        stats = {
            "totalAssetValue": round(net_value, 2),
            "totalReturn": round(total_return, 2),
            "cashPosition": round(cash, 2),
            "tickerWeights": {},
            "totalTrades": len(state.get("all_trades", [])),
            "winRate": 0.0,
            "bullBear": {
                "bull": {"n": 0, "win": 0},
                "bear": {"n": 0, "win": 0},
            },
        }

        self.save_file("stats", stats)

    def _generate_trades(self, state: Dict[str, Any]):
        """Generate trades.json"""
        all_trades = state.get("all_trades", [])

        sorted_trades = sorted(
            all_trades,
            key=lambda x: x.get("ts", 0),
            reverse=True,
        )

        trades = []
        for trade in sorted_trades[:100]:
            trades.append(
                {
                    "id": trade.get("id"),
                    "timestamp": trade.get("ts"),
                    "trading_date": trade.get("trading_date"),
                    "side": trade.get("side", ""),
                    "ticker": trade.get("ticker", ""),
                    "qty": trade.get("qty", 0),
                    "price": trade.get("price", 0),
                },
            )

        self.save_file("trades", trades)

    # Server State Management Methods

    def load_server_state(self) -> Dict[str, Any]:
        """
        Load server state from file

        Returns:
            Server state dictionary with feed_history and other data
        """
        default_state = {
            "status": "initializing",
            "current_date": None,
            "portfolio": {
                "total_value": self.initial_cash,
                "cash": self.initial_cash,
                "pnl_percent": 0.0,
                "equity": [],
                "baseline": [],
                "baseline_vw": [],
                "momentum": [],
                "strategies": [],
            },
            "holdings": [],
            "trades": [],
            "stats": self._get_default_stats(),
            "leaderboard": [],
            "realtime_prices": {},
            "system_started": datetime.now().isoformat(),
            "feed_history": [],
            "last_day_history": [],
            "trading_days_total": 0,
            "trading_days_completed": 0,
        }

        if not self.server_state_file.exists():
            return default_state

        with open(self.server_state_file, "r", encoding="utf-8") as f:
            saved_state = json.load(f)

        # Merge with defaults to ensure all fields exist
        for key, value in default_state.items():
            saved_state.setdefault(key, value)

        logger.info(f"Server state loaded from: {self.server_state_file}")
        logger.info(
            f"Feed history: {len(saved_state.get('feed_history', []))} messages",  # noqa: E501
        )
        logger.info(
            f"Holdings: {len(saved_state.get('holdings', []))} items",
        )
        logger.info(f"Trades: {len(saved_state.get('trades', []))} records")

        return saved_state

    def save_server_state(self, state: Dict[str, Any]):
        """
        Save server state to file

        Args:
            state: Server state dictionary
        """
        state_to_save = {
            **state,
            "last_saved": datetime.now().isoformat(),
        }

        # Limit feed_history size
        if "feed_history" in state_to_save:
            state_to_save["feed_history"] = state_to_save["feed_history"][
                : self.max_feed_history
            ]

        # Limit trades
        if "trades" in state_to_save:
            state_to_save["trades"] = state_to_save["trades"][:100]

        with open(self.server_state_file, "w", encoding="utf-8") as f:
            json.dump(
                state_to_save,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        logger.debug(f"Server state saved to: {self.server_state_file}")

    def add_feed_message(
        self,
        state: Dict[str, Any],
        event: Dict[str, Any],
    ) -> bool:
        """
        Add a message to feed history

        Args:
            state: Server state dictionary to update
            event: Event dictionary with type, content, etc.

        Returns:
            True if message was added, False if filtered out
        """
        event_type = event.get("type", "")

        # Types to save in feed history
        save_types = {
            "system",
            "agent_message",
            "day_start",
            "day_complete",
            "day_error",
            "team_summary",
            "conference_start",
            "conference_message",
            "conference_end",
            "memory",
        }

        if event_type not in save_types:
            return False

        # Ensure timestamp exists
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()

        # Store event directly (flat structure, no metadata wrapper)
        feed_msg = dict(event)

        # Insert at beginning (newest first)
        if "feed_history" not in state:
            state["feed_history"] = []

        state["feed_history"].insert(0, feed_msg)

        # Trim to max size
        if len(state["feed_history"]) > self.max_feed_history:
            state["feed_history"] = state["feed_history"][
                : self.max_feed_history
            ]

        return True

    def _get_default_stats(self) -> Dict[str, Any]:
        """Get default stats structure"""
        return {
            "totalAssetValue": 0.0,
            "totalReturn": -100.0,
            "cashPosition": 0.0,
            "tickerWeights": {},
            "totalTrades": 0,
            "winRate": 0.0,
            "bullBear": {
                "bull": {"n": 0, "win": 0},
                "bear": {"n": 0, "win": 0},
            },
        }

    def update_server_state_from_dashboard(self, state: Dict[str, Any]):
        """
        Update server state with current dashboard data

        Args:
            state: Server state dictionary to update
        """
        # Load dashboard data
        summary = self.load_file("summary") or {}
        holdings = self.load_file("holdings") or []
        stats = self.load_file("stats") or self._get_default_stats()
        trades = self.load_file("trades") or []
        leaderboard = self.load_file("leaderboard") or []

        # Update state
        state["portfolio"] = {
            "total_value": summary.get("totalAssetValue", self.initial_cash),
            "cash": summary.get("cashPosition", self.initial_cash),
            "pnl_percent": summary.get("pnlPct", 0.0),
            "equity": summary.get("equity", []),
            "baseline": summary.get("baseline", []),
            "baseline_vw": summary.get("baseline_vw", []),
            "momentum": summary.get("momentum", []),
            "strategies": [],
            # Live returns (will be populated when session is active)
            "equity_return": [],
            "baseline_return": [],
            "baseline_vw_return": [],
            "momentum_return": [],
        }
        state["holdings"] = holdings
        state["stats"] = stats
        state["trades"] = trades
        state["leaderboard"] = leaderboard

    # ========== Live Returns Tracking ==========

    def start_live_session(self):
        """
        Start tracking live returns for current trading session.
        Captures current values as session start baseline.
        """
        summary = self.load_file("summary") or {}
        state = self.load_internal_state()

        # Capture current values as session start
        equity_history = state.get("equity_history", [])
        baseline_history = state.get("baseline_history", [])
        baseline_vw_history = state.get("baseline_vw_history", [])
        momentum_history = state.get("momentum_history", [])

        self._session_start_equity = (
            equity_history[-1]["v"]
            if equity_history
            else summary.get("totalAssetValue", self.initial_cash)
        )
        self._session_start_baseline = (
            baseline_history[-1]["v"]
            if baseline_history
            else self.initial_cash
        )
        self._session_start_baseline_vw = (
            baseline_vw_history[-1]["v"]
            if baseline_vw_history
            else self.initial_cash
        )
        self._session_start_momentum = (
            momentum_history[-1]["v"]
            if momentum_history
            else self.initial_cash
        )

        # Clear live return history
        self._live_return_history = []

        # Add starting point at 0%
        timestamp = int(datetime.now().timestamp() * 1000)
        self._live_return_history.append(
            {
                "t": timestamp,
                "equity": 0.0,
                "baseline": 0.0,
                "baseline_vw": 0.0,
                "momentum": 0.0,
            },
        )

        logger.info(
            "Live session started: "
            f"equity=${self._session_start_equity:,.2f}, "
            f"baseline=${self._session_start_baseline:,.2f}",
        )

    def end_live_session(self):
        """End live returns tracking session"""
        self._session_start_equity = None
        self._session_start_baseline = None
        self._session_start_baseline_vw = None
        self._session_start_momentum = None
        self._live_return_history = []
        logger.info("Live session ended")

    def update_live_returns(
        self,
        current_equity: Optional[float] = None,
        current_baseline: Optional[float] = None,
        current_baseline_vw: Optional[float] = None,
        current_momentum: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update live returns with current values.

        Args:
            current_equity: Current portfolio value
            current_baseline: Current EW baseline value
            current_baseline_vw: Current VW baseline value
            current_momentum: Current momentum strategy value

        Returns:
            Dict with live return data point or None if session not active
        """
        if (
            self._session_start_equity is None
            or self._session_start_baseline is None
            or self._session_start_baseline_vw is None
            or self._session_start_momentum is None
        ):
            return None

        timestamp = int(datetime.now().timestamp() * 1000)
        point = {"t": timestamp}

        # Calculate returns (only if we have valid values)
        if current_equity is not None and self._session_start_equity > 0:
            ret = (
                (current_equity - self._session_start_equity)
                / self._session_start_equity
            ) * 100
            point["equity"] = round(ret, 4)

        if current_baseline is not None and self._session_start_baseline > 0:
            ret = (
                (current_baseline - self._session_start_baseline)
                / self._session_start_baseline
            ) * 100
            point["baseline"] = round(ret, 4)

        if (
            current_baseline_vw is not None
            and self._session_start_baseline_vw > 0
        ):
            ret = (
                (current_baseline_vw - self._session_start_baseline_vw)
                / self._session_start_baseline_vw
            ) * 100
            point["baseline_vw"] = round(ret, 4)

        if current_momentum is not None and self._session_start_momentum > 0:
            ret = (
                (current_momentum - self._session_start_momentum)
                / self._session_start_momentum
            ) * 100
            point["momentum"] = round(ret, 4)

        # Only add point if we have at least one return value
        if any(k != "t" for k in point):
            self._live_return_history.append(point)
            # Limit history size
            if len(self._live_return_history) > 500:
                self._live_return_history = self._live_return_history[-500:]
            return point

        return None

    def get_live_returns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get live return curves for the current session.

        Returns:
            Dict with separate arrays for each strategy:
            - equity_return: [{t, v}, ...]
            - baseline_return: [{t, v}, ...]
            - baseline_vw_return: [{t, v}, ...]
            - momentum_return: [{t, v}, ...]
        """
        if not self._live_return_history:
            return {
                "equity_return": [],
                "baseline_return": [],
                "baseline_vw_return": [],
                "momentum_return": [],
            }

        # Convert combined history to separate arrays
        equity_return = []
        baseline_return = []
        baseline_vw_return = []
        momentum_return = []

        for point in self._live_return_history:
            t = point["t"]
            if "equity" in point:
                equity_return.append({"t": t, "v": point["equity"]})
            if "baseline" in point:
                baseline_return.append({"t": t, "v": point["baseline"]})
            if "baseline_vw" in point:
                baseline_vw_return.append({"t": t, "v": point["baseline_vw"]})
            if "momentum" in point:
                momentum_return.append({"t": t, "v": point["momentum"]})

        return {
            "equity_return": equity_return,
            "baseline_return": baseline_return,
            "baseline_vw_return": baseline_vw_return,
            "momentum_return": momentum_return,
        }

    @property
    def is_live_session_active(self) -> bool:
        """Check if live session is active"""
        return self._session_start_equity is not None
