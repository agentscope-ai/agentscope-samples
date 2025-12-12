# -*- coding: utf-8 -*-
"""
Settlement Coordinator
Unified daily settlement logic for agent portfolio, baselines, and analyst tracking
"""
# flake8: noqa: E501
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.services.storage import StorageService
from backend.utils.analyst_tracker import (
    AnalystPerformanceTracker,
    update_leaderboard_with_evaluations,
)
from backend.utils.baselines import (
    BaselineCalculator,
    calculate_momentum_scores,
)

logger = logging.getLogger(__name__)


class SettlementCoordinator:
    """
    Coordinates daily settlement after market close

    Responsibilities:
    1. Calculate agent portfolio P&L
    2. Update baseline portfolios (equal-weight, market-cap, momentum)
    3. Evaluate analyst predictions and update leaderboard
    4. Update summary.json with all portfolio values
    5. Persist state to storage
    """

    def __init__(
        self,
        storage: "StorageService",
        initial_capital: float = 100000.0,
    ):
        self.storage = storage
        self.initial_capital = initial_capital
        self.baseline_calculator = BaselineCalculator(initial_capital)
        self.analyst_tracker = AnalystPerformanceTracker()

        self.price_history: Dict[str, List[tuple]] = {}

        # Load persisted state from storage
        self._load_persisted_state()

    def _load_persisted_state(self):
        """
        Load persisted baseline and price history state from storage

        This restores the baseline calculator state so that backtest/live mode
        can resume from where it left off.
        """
        internal_state = self.storage.load_internal_state()

        # Load baseline calculator state
        baseline_state = {
            "baseline_state": internal_state.get("baseline_state", {}),
            "baseline_vw_state": internal_state.get("baseline_vw_state", {}),
            "momentum_state": internal_state.get("momentum_state", {}),
        }
        self.baseline_calculator.load_state(baseline_state)

        # Load price history for momentum calculation
        saved_price_history = internal_state.get("price_history", {})
        if saved_price_history:
            # Convert saved format back to list of tuples
            for ticker, history in saved_price_history.items():
                converted_history = []
                for entry in history:
                    if isinstance(entry, dict):
                        converted_history.append(
                            (entry["date"], entry["price"]),
                        )
                    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        converted_history.append((entry[0], entry[1]))
                    else:
                        continue
                self.price_history[ticker] = converted_history
            logger.info(
                f"Restored price history for {len(self.price_history)} tickers",
            )

    def _save_persisted_state(self):
        """
        Save baseline and price history state to storage

        This persists the baseline calculator state so that backtest/live mode
        can resume from where it left off after restart.
        """
        internal_state = self.storage.load_internal_state()

        # Export baseline calculator state
        baseline_state = self.baseline_calculator.export_state()
        internal_state["baseline_state"] = baseline_state["baseline_state"]
        internal_state["baseline_vw_state"] = baseline_state[
            "baseline_vw_state"
        ]
        internal_state["momentum_state"] = baseline_state["momentum_state"]

        # Save price history (convert tuples to dicts for JSON serialization)
        price_history_serializable = {}
        for ticker, history in self.price_history.items():
            price_history_serializable[ticker] = [
                {"date": date, "price": price} for date, price in history
            ]
        internal_state["price_history"] = price_history_serializable

        self.storage.save_internal_state(internal_state)
        logger.info("Persisted baseline calculator and price history state")

    def record_analyst_predictions(
        self,
        final_predictions: List[Dict[str, Any]],
    ):
        """
        Record structured analyst predictions before market close

        Args:
            final_predictions: Structured prediction results from analysts
                Format: [
                    {
                        'agent': 'analyst_name',
                        'predictions': [
                            {'ticker': 'AAPL', 'direction': 'up', 'confidence': 0.75},
                            ...
                        ]
                    },
                    ...
                ]
            tickers: List of tickers being analyzed
        """
        self.analyst_tracker.record_analyst_predictions(final_predictions)

    def update_price_history(
        self,
        date: str,
        prices: Dict[str, float],
    ):
        """
        Update price history for momentum calculation

        Args:
            date: Trading date (YYYY-MM-DD)
            prices: Current prices for each ticker
        """
        for ticker, price in prices.items():
            if ticker not in self.price_history:
                self.price_history[ticker] = []
            self.price_history[ticker].append((date, price))

            self.price_history[ticker] = self.price_history[ticker][-60:]

    def run_daily_settlement(
        self,
        date: str,
        tickers: List[str],
        open_prices: Optional[Dict[str, float]],
        close_prices: Dict[str, float],
        market_caps: Dict[str, float],
        agent_portfolio: Dict[str, Any],
        analyst_results: List[Dict[str, Any]],  # pylint: disable=W0613
        pm_decisions: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Run complete daily settlement

        Args:
            date: Trading date (YYYY-MM-DD)
            tickers: List of tickers
            open_prices: Opening prices
            close_prices: Closing prices
            market_caps: Market caps for each ticker
            agent_portfolio: Current agent portfolio state
            analyst_results: Analyst analysis results
            pm_decisions: PM's trading decisions

        Returns:
            Settlement results including all portfolio values and evaluations
        """
        logger.info(f"Running daily settlement for {date}")

        self.update_price_history(date, close_prices)

        momentum_scores = calculate_momentum_scores(
            tickers,
            self.price_history,
            lookback_days=20,
        )

        rebalance_momentum = self._should_rebalance_momentum(date)

        baseline_values = self.baseline_calculator.get_all_baseline_values(
            tickers=tickers,
            open_prices=open_prices if open_prices else close_prices,
            close_prices=close_prices,
            market_caps=market_caps,
            momentum_scores=momentum_scores,
            date=date,
            rebalance_momentum=rebalance_momentum,
        )

        logger.info(f"Baseline values calculated: {baseline_values}")

        agent_value = self.storage.calculate_portfolio_value(
            agent_portfolio,
            close_prices,
        )

        analyst_evaluations = self.analyst_tracker.evaluate_predictions(
            open_prices,
            close_prices,
            date,
        )

        pm_evaluations = {}
        if pm_decisions:
            pm_evaluations = self.analyst_tracker.evaluate_pm_decisions(
                pm_decisions,
                open_prices,
                close_prices,
                date,
            )

        all_evaluations = {**analyst_evaluations, **pm_evaluations}

        leaderboard = self.storage.load_file("leaderboard") or []
        updated_leaderboard = update_leaderboard_with_evaluations(
            leaderboard,
            all_evaluations,
        )
        self.storage.save_file("leaderboard", updated_leaderboard)

        self._update_summary_with_baselines(
            date,
            agent_value,
            baseline_values,
        )

        self.analyst_tracker.clear_daily_predictions()

        # Persist baseline calculator and price history state
        self._save_persisted_state()

        return {
            "date": date,
            "agent_portfolio_value": agent_value,
            "baseline_values": baseline_values,
            "analyst_evaluations": analyst_evaluations,
            "baselines_updated": True,
            "leaderboard_updated": True,
        }

    def _should_rebalance_momentum(self, date: str) -> bool:
        """
        Check if momentum portfolio should rebalance

        Returns True if it's a new month
        """
        last_rebalance = self.baseline_calculator.momentum_last_rebalance_date
        if last_rebalance is None:
            return True

        last_date = datetime.strptime(last_rebalance, "%Y-%m-%d")
        current_date = datetime.strptime(date, "%Y-%m-%d")

        return (current_date.year, current_date.month) != (
            last_date.year,
            last_date.month,
        )

    def _update_summary_with_baselines(
        self,
        date: str,
        agent_value: float,
        baseline_values: Dict[str, float],
    ):
        """
        Update summary.json with agent and baseline portfolio values

        NOTE: History updates are now handled centrally by storage.update_dashboard_after_cycle()
        to ensure all histories (equity, baseline, baseline_vw, momentum) stay synchronized.
        baseline_values are returned in run_daily_settlement() and passed to storage.

        Args:
            date: Trading date (used for backtest-compatible timestamps)
            agent_value: Agent portfolio value
            baseline_values: Baseline portfolio values
        """
        # History updates are now handled by storage.update_dashboard_after_cycle()
        # which receives baseline_values from settlement_result and updates all histories together.
        # This ensures equity and baseline data points are always synchronized.

    def update_intraday_values(
        self,
        tickers: List[str],
        current_prices: Dict[str, float],
        market_caps: Dict[str, float],
        agent_portfolio: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Update portfolio values with current prices (for live mode intraday updates)

        Args:
            tickers: List of tickers
            current_prices: Current prices
            market_caps: Market caps
            agent_portfolio: Current agent portfolio

        Returns:
            Dict with current portfolio values
        """
        agent_value = self.storage.calculate_portfolio_value(
            agent_portfolio,
            current_prices,
        )

        equal_weight = self.baseline_calculator.calculate_equal_weight_value(
            tickers,
            current_prices,
            current_prices,
        )
        market_cap = (
            self.baseline_calculator.calculate_market_cap_weighted_value(
                tickers,
                current_prices,
                current_prices,
                market_caps,
            )
        )

        momentum_scores = calculate_momentum_scores(
            tickers,
            self.price_history,
            lookback_days=20,
        )

        last_date = (
            list(self.price_history.values())[0][-1][0]
            if self.price_history
            else ""
        )

        momentum = self.baseline_calculator.calculate_momentum_value(
            tickers,
            current_prices,
            current_prices,
            momentum_scores,
            date=last_date,
            rebalance=False,
        )

        return {
            "agent": agent_value,
            "equal_weight": equal_weight,
            "market_cap_weighted": market_cap,
            "momentum": momentum,
        }
