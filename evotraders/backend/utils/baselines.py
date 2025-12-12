# -*- coding: utf-8 -*-
"""
Baseline Strategy Calculators
Tracks performance of simple baseline strategies for comparison
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple, TypedDict

logger = logging.getLogger(__name__)


class Portfolio(TypedDict):
    cash: float
    positions: Dict[str, float]


class BaselineCalculator:
    """
    Calculates baseline strategy returns for comparison

    Strategies:
    1. Equal-weight: Allocate equal weight to all tickers
    2. Market-cap-weighted: Allocate proportional to market cap
    3. Simple momentum: Monthly rebalance,
                        long top 50% momentum, short bottom 50%
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital

        self.equal_weight_portfolio: Portfolio = {"cash": 0.0, "positions": {}}
        self.market_cap_portfolio: Portfolio = {"cash": 0.0, "positions": {}}
        self.momentum_portfolio: Portfolio = {
            "cash": initial_capital,
            "positions": {},
        }

        self.equal_weight_initialized = False
        self.market_cap_initialized = False
        self.momentum_last_rebalance_date = None

    def calculate_equal_weight_value(
        self,
        tickers: List[str],
        open_prices: Dict[str, float],
        close_prices: Dict[str, float],
    ) -> float:
        """
        Calculate equal-weight portfolio value

        On first call, initialize positions with equal allocation using
        open prices. Subsequently, mark-to-market existing positions
        using close prices.

        Args:
            tickers: List of stock tickers
            open_prices: Opening prices (used for initial purchase)
            close_prices: Closing prices (used for valuation)
        """
        if not self.equal_weight_initialized:
            allocation_per_ticker = self.initial_capital / len(tickers)
            self.equal_weight_portfolio["cash"] = 0.0
            for ticker in tickers:
                price = open_prices.get(ticker, 0)  # Use OPEN price for buying
                if price > 0:
                    shares = allocation_per_ticker / price
                    self.equal_weight_portfolio["positions"][ticker] = shares
                    logger.info(
                        f"Equal Weight: Initialized {ticker} with "
                        f"{shares:.2f} shares @ ${price:.2f} (open)",
                    )
            self.equal_weight_initialized = True

        total_value = self.equal_weight_portfolio["cash"]
        positions: Dict[str, float] = self.equal_weight_portfolio["positions"]
        for ticker, shares in positions.items():
            price = close_prices.get(ticker, 0)
            total_value += shares * price

        return total_value

    def calculate_market_cap_weighted_value(
        self,
        tickers: List[str],
        open_prices: Dict[str, float],
        close_prices: Dict[str, float],
        market_caps: Dict[str, float],
    ) -> float:
        """
        Calculate market-cap-weighted portfolio value

        On first call, initialize positions weighted by market cap using
        open prices. Subsequently, mark-to-market existing positions
        using close prices.

        Args:
            tickers: List of stock tickers
            open_prices: Opening prices (used for initial purchase)
            close_prices: Closing prices (used for valuation)
            market_caps: Market capitalization for each ticker
        """
        if not self.market_cap_initialized:
            total_market_cap = sum(market_caps.get(t, 0) for t in tickers)
            if total_market_cap <= 0:
                logger.warning("No market cap data, using equal weight")
                return self.calculate_equal_weight_value(
                    tickers,
                    open_prices,
                    close_prices,
                )

            self.market_cap_portfolio["cash"] = 0.0
            for ticker in tickers:
                market_cap = market_caps.get(ticker, 0)
                price = open_prices.get(ticker, 0)  # Use OPEN price for buying
                if market_cap > 0 and price > 0:
                    weight = market_cap / total_market_cap
                    allocation = self.initial_capital * weight
                    shares = allocation / price
                    self.market_cap_portfolio["positions"][ticker] = shares
                    logger.info(
                        f"Market Cap Weighted: Initialized {ticker} with "
                        f"{shares:.2f} shares @ ${price:.2f} (open), "
                        f"weight={weight:.2%}",
                    )
            self.market_cap_initialized = True

        total_value = self.market_cap_portfolio["cash"]
        positions: Dict[str, float] = self.market_cap_portfolio["positions"]
        for ticker, shares in positions.items():
            price = close_prices.get(ticker, 0)
            total_value += shares * price

        return total_value

    def calculate_momentum_value(
        self,
        tickers: List[str],
        open_prices: Dict[str, float],
        close_prices: Dict[str, float],
        momentum_scores: Dict[str, float],
        date: str,
        rebalance: bool = False,
    ) -> float:
        """
        Calculate momentum strategy portfolio value

        Strategy: Monthly rebalance
        - Long top 50% momentum stocks
        - Short bottom 50% momentum stocks (if shorting enabled)
        - Equal weight within each group

        Args:
            tickers: List of tickers
            open_prices: Opening prices (used for rebalancing trades)
            close_prices: Closing prices (used for valuation)
            momentum_scores: Momentum scores for each ticker
            date: Current date (YYYY-MM-DD)
            rebalance: Force rebalance if True
        """
        should_rebalance = rebalance
        if self.momentum_last_rebalance_date is None:
            should_rebalance = True
        elif not rebalance:
            last_date = datetime.strptime(
                self.momentum_last_rebalance_date,
                "%Y-%m-%d",
            )
            current_date = datetime.strptime(date, "%Y-%m-%d")
            if (current_date.year, current_date.month) != (
                last_date.year,
                last_date.month,
            ):
                should_rebalance = True

        if should_rebalance:
            self._rebalance_momentum_portfolio(
                tickers,
                open_prices,
                momentum_scores,
            )
            self.momentum_last_rebalance_date = date

        total_value = self.momentum_portfolio["cash"]
        positions: Dict[str, float] = self.momentum_portfolio["positions"]
        for ticker, shares in positions.items():
            price = close_prices.get(ticker, 0)
            total_value += shares * price

        return total_value

    def _rebalance_momentum_portfolio(
        self,
        tickers: List[str],
        prices: Dict[str, float],
        momentum_scores: Dict[str, float],
    ):
        """Rebalance momentum portfolio based on current momentum scores"""
        current_value = self.momentum_portfolio["cash"]
        for ticker, shares in self.momentum_portfolio["positions"].items():
            price = prices.get(ticker, 0)
            current_value += shares * price

        self.momentum_portfolio["positions"] = {}

        sorted_tickers = sorted(
            tickers,
            key=lambda t: momentum_scores.get(t, 0),
            reverse=True,
        )

        mid_point = len(sorted_tickers) // 2
        long_tickers = (
            sorted_tickers[:mid_point] if mid_point > 0 else sorted_tickers
        )

        if len(long_tickers) == 0:
            self.momentum_portfolio["cash"] = current_value
            return

        allocation_per_ticker = current_value / len(long_tickers)
        used_capital = 0.0

        for ticker in long_tickers:
            price = prices.get(ticker, 0)
            if price > 0:
                shares = allocation_per_ticker / price
                self.momentum_portfolio["positions"][ticker] = shares
                used_capital += allocation_per_ticker

        self.momentum_portfolio["cash"] = current_value - used_capital

    def get_all_baseline_values(
        self,
        tickers: List[str],
        open_prices: Dict[str, float],
        close_prices: Dict[str, float],
        market_caps: Dict[str, float],
        momentum_scores: Dict[str, float],
        date: str,
        rebalance_momentum: bool = False,
    ) -> Dict[str, float]:
        """
        Get all baseline portfolio values in one call

        Args:
            tickers: List of stock tickers
            open_prices: Opening prices (used for initial purchase/rebalancing)
            close_prices: Closing prices (used for valuation)
            market_caps: Market caps for each ticker
            momentum_scores: Momentum scores for rebalancing
            date: Current date
            rebalance_momentum: Whether to rebalance momentum portfolio

        Returns:
            Dict with keys: equal_weight, market_cap_weighted, momentum
        """
        equal_weight_value = self.calculate_equal_weight_value(
            tickers,
            open_prices,
            close_prices,
        )
        market_cap_value = self.calculate_market_cap_weighted_value(
            tickers,
            open_prices,
            close_prices,
            market_caps,
        )
        momentum_value = self.calculate_momentum_value(
            tickers,
            open_prices,
            close_prices,
            momentum_scores,
            date,
            rebalance_momentum,
        )

        return {
            "equal_weight": equal_weight_value,
            "market_cap_weighted": market_cap_value,
            "momentum": momentum_value,
        }

    def export_state(self) -> Dict[str, Any]:
        """
        Export calculator state for persistence

        Returns:
            Dictionary containing all portfolio states for serialization
        """
        return {
            "baseline_state": {
                "initialized": self.equal_weight_initialized,
                "initial_allocation": dict(
                    self.equal_weight_portfolio["positions"],
                ),
            },
            "baseline_vw_state": {
                "initialized": self.market_cap_initialized,
                "initial_allocation": dict(
                    self.market_cap_portfolio["positions"],
                ),
            },
            "momentum_state": {
                "positions": dict(self.momentum_portfolio["positions"]),
                "cash": self.momentum_portfolio["cash"],
                "initialized": self.momentum_last_rebalance_date is not None,
                "last_rebalance_date": self.momentum_last_rebalance_date,
            },
        }

    def load_state(self, state: Dict[str, Any]):
        """
        Load calculator state from persistence

        Args:
            state: Dictionary containing baseline_state, baseline_vw_state,
                   momentum_state from storage
        """
        # Load equal-weight state
        baseline_state = state.get("baseline_state", {})
        if baseline_state.get("initialized", False):
            self.equal_weight_initialized = True
            self.equal_weight_portfolio["positions"] = dict(
                baseline_state.get("initial_allocation", {}),
            )
            self.equal_weight_portfolio["cash"] = 0.0
            logger.info(
                f"Restored equal-weight portfolio with "
                f"{len(self.equal_weight_portfolio['positions'])} positions",
            )

        # Load market-cap-weighted state
        baseline_vw_state = state.get("baseline_vw_state", {})
        if baseline_vw_state.get("initialized", False):
            self.market_cap_initialized = True
            self.market_cap_portfolio["positions"] = dict(
                baseline_vw_state.get("initial_allocation", {}),
            )
            self.market_cap_portfolio["cash"] = 0.0
            logger.info(
                f"Restored market-cap portfolio with "
                f"{len(self.market_cap_portfolio['positions'])} positions",
            )

        # Load momentum state
        momentum_state = state.get("momentum_state", {})
        if momentum_state.get("initialized", False):
            self.momentum_portfolio["positions"] = dict(
                momentum_state.get("positions", {}),
            )
            self.momentum_portfolio["cash"] = momentum_state.get(
                "cash",
                self.initial_capital,
            )
            self.momentum_last_rebalance_date = momentum_state.get(
                "last_rebalance_date",
            )
            logger.info(
                f"Restored momentum portfolio with "
                f"{len(self.momentum_portfolio['positions'])} positions, "
                f"last rebalance: {self.momentum_last_rebalance_date}",
            )


def calculate_momentum_scores(
    tickers: List[str],
    prices_history: Dict[str, List[Tuple[str, float]]],
    lookback_days: int = 20,
) -> Dict[str, float]:
    """
    Calculate momentum scores for tickers

    Args:
        tickers: List of tickers
        prices_history: Dict mapping ticker to list of (date, price) tuples
        lookback_days: Number of days to calculate momentum

    Returns:
        Dict mapping ticker to momentum score (percentage return)
    """
    momentum_scores = {}

    for ticker in tickers:
        history = prices_history.get(ticker, [])
        if len(history) < 2:
            momentum_scores[ticker] = 0.0
            continue

        sorted_history = sorted(history, key=lambda x: x[0])

        if len(sorted_history) < lookback_days:
            start_price = sorted_history[0][1]
            end_price = sorted_history[-1][1]
        else:
            start_price = sorted_history[-lookback_days][1]
            end_price = sorted_history[-1][1]

        if start_price > 0:
            momentum_scores[ticker] = (end_price - start_price) / start_price
        else:
            momentum_scores[ticker] = 0.0

    return momentum_scores
