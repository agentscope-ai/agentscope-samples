# -*- coding: utf-8 -*-
"""
Analyst Performance Tracker
Tracks analyst predictions and calculates win rates for leaderboard
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnalystPerformanceTracker:
    """
    Tracks analyst predictions and evaluates accuracy

    Workflow:
    1. Record analyst predictions for each ticker before market close
    2. After market close, evaluate predictions against actual returns
    3. Update leaderboard with win rates and statistics
    """

    def __init__(self):
        self.daily_predictions = {}

    def record_analyst_predictions(
        self,
        final_predictions: List[Dict[str, Any]],
    ):
        """
        Record predictions from analysts for the current trading day

        Args:
            final_predictions: List of structured prediction results
                Format: [
                    {
                        'agent': 'analyst_name',
                        'predictions': [
                            {'ticker': 'AAPL', '
                            direction': 'up',
                            'confidence': 0.75},
                            ...
                        ]
                    },
                    ...
                ]
            tickers: List of tickers being analyzed
        """
        self.daily_predictions = {}

        direction_mapping = {
            "up": "long",
            "down": "short",
            "neutral": "hold",
        }

        for result in final_predictions:
            analyst_id = result.get("agent")
            if not analyst_id:
                continue

            predictions = result.get("predictions", [])

            self.daily_predictions[analyst_id] = {}

            for pred in predictions:
                ticker = pred.get("ticker")
                direction = pred.get("direction", "neutral")

                if ticker:
                    signal = direction_mapping.get(direction, "hold")
                    self.daily_predictions[analyst_id][ticker] = signal

    def evaluate_predictions(
        self,
        open_prices: Optional[Dict[str, float]],
        close_prices: Dict[str, float],
        date: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate analyst predictions against actual market moves

        Args:
            open_prices: Opening prices for each ticker
            close_prices: Closing prices for each ticker
            date: Trading date string (YYYY-MM-DD)

        Returns:
            Dict mapping analyst_id to evaluation results
        """
        evaluation_results = {}

        # Map internal signal types to frontend display names
        signal_display_map = {
            "long": "bull",
            "short": "bear",
            "hold": "neutral",
        }

        for analyst_id, predictions in self.daily_predictions.items():
            correct_long = 0
            correct_short = 0
            incorrect_long = 0
            incorrect_short = 0
            unknown_long = 0
            unknown_short = 0
            hold_count = 0

            # Individual signal records for frontend display
            individual_signals: List[Dict[str, Any]] = []

            for ticker, prediction in predictions.items():
                open_price = open_prices.get(ticker, 0)
                close_price = close_prices.get(ticker, 0)

                signal_type = signal_display_map.get(prediction, "neutral")

                # Cannot evaluate if prices are missing
                if open_price <= 0 or close_price <= 0:
                    if prediction == "long":
                        unknown_long += 1
                    elif prediction == "short":
                        unknown_short += 1

                    individual_signals.append(
                        {
                            "ticker": ticker,
                            "signal": signal_type,
                            "date": date,
                            "is_correct": "unknown",
                        },
                    )
                    continue

                actual_return = (close_price - open_price) / open_price

                if prediction == "long":
                    is_correct = actual_return > 0
                    if is_correct:
                        correct_long += 1
                    else:
                        incorrect_long += 1

                    individual_signals.append(
                        {
                            "ticker": ticker,
                            "signal": signal_type,
                            "date": date,
                            "is_correct": is_correct,
                        },
                    )

                elif prediction == "short":
                    is_correct = actual_return < 0
                    if is_correct:
                        correct_short += 1
                    else:
                        incorrect_short += 1

                    individual_signals.append(
                        {
                            "ticker": ticker,
                            "signal": signal_type,
                            "date": date,
                            "is_correct": is_correct,
                        },
                    )

                elif prediction == "hold":
                    hold_count += 1
                    individual_signals.append(
                        {
                            "ticker": ticker,
                            "signal": signal_type,
                            "date": date,
                            "is_correct": None,
                        },
                    )

            total_long = correct_long + incorrect_long + unknown_long
            total_short = correct_short + incorrect_short + unknown_short
            evaluated_long = correct_long + incorrect_long
            evaluated_short = correct_short + incorrect_short
            total_evaluated = evaluated_long + evaluated_short
            correct_predictions = correct_long + correct_short

            win_rate = (
                correct_predictions / total_evaluated
                if total_evaluated > 0
                else None
            )

            evaluation_results[analyst_id] = {
                "total_predictions": total_evaluated,
                "correct_predictions": correct_predictions,
                "win_rate": win_rate,
                "bull": {
                    "n": total_long,
                    "win": correct_long,
                    "unknown": unknown_long,
                },
                "bear": {
                    "n": total_short,
                    "win": correct_short,
                    "unknown": unknown_short,
                },
                "hold": hold_count,
                "signals": individual_signals,
            }

        return evaluation_results

    def clear_daily_predictions(self):
        """Clear predictions after evaluation"""
        self.daily_predictions = {}

    def _process_single_pm_decision(
        self,
        _ticker: str,
        decision: Dict,
        open_price: float,
        close_price: float,
        _date: str,
    ) -> Tuple[str, Optional[bool], str]:
        """
        Process a single PM decision and evaluate correctness

        Returns:
            Tuple of (prediction, is_correct, signal_type)
        """
        action = decision.get("action", "hold")

        # Convert action to prediction format
        if action in ["buy", "long"]:
            prediction = "long"
        elif action in ["sell", "short"]:
            prediction = "short"
        else:
            prediction = "hold"

        signal_display_map = {
            "long": "bull",
            "short": "bear",
            "hold": "neutral",
        }
        signal_type = signal_display_map.get(prediction, "neutral")

        # Handle invalid prices
        if open_price <= 0 or close_price <= 0:
            return prediction, None, signal_type

        # Evaluate correctness
        actual_return = (close_price - open_price) / open_price

        if prediction == "long":
            is_correct = actual_return > 0
        elif prediction == "short":
            is_correct = actual_return < 0
        else:  # hold
            is_correct = None

        return prediction, is_correct, signal_type

    def evaluate_pm_decisions(
        self,
        pm_decisions: Dict[str, Dict],
        open_prices: Optional[Dict[str, float]],
        close_prices: Dict[str, float],
        date: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate PM's trading decisions against actual market moves

        Args:
            pm_decisions: PM decisions {ticker: {action, quantity, ...}}
            open_prices: Opening prices for each ticker
            close_prices: Closing prices for each ticker
            date: Trading date string (YYYY-MM-DD)

        Returns:
            Dict with 'portfolio_manager' key containing evaluation results
        """
        if not pm_decisions or not open_prices or not close_prices:
            return {}

        correct_long = 0
        correct_short = 0
        incorrect_long = 0
        incorrect_short = 0
        unknown_long = 0
        unknown_short = 0
        hold_count = 0

        individual_signals: List[Dict[str, Any]] = []

        for ticker, decision in pm_decisions.items():
            open_price = open_prices.get(ticker, 0)
            close_price = close_prices.get(ticker, 0)

            (
                prediction,
                is_correct,
                signal_type,
            ) = self._process_single_pm_decision(
                ticker,
                decision,
                open_price,
                close_price,
                date,
            )

            if is_correct is None and (open_price <= 0 or close_price <= 0):
                if prediction == "long":
                    unknown_long += 1
                elif prediction == "short":
                    unknown_short += 1
                individual_signals.append(
                    {
                        "ticker": ticker,
                        "signal": signal_type,
                        "date": date,
                        "is_correct": "unknown",
                    },
                )
            elif prediction == "hold":
                hold_count += 1
                individual_signals.append(
                    {
                        "ticker": ticker,
                        "signal": signal_type,
                        "date": date,
                        "is_correct": None,
                    },
                )
            else:
                if prediction == "long":
                    if is_correct:
                        correct_long += 1
                    else:
                        incorrect_long += 1
                else:
                    if is_correct:
                        correct_short += 1
                    else:
                        incorrect_short += 1

                individual_signals.append(
                    {
                        "ticker": ticker,
                        "signal": signal_type,
                        "date": date,
                        "is_correct": is_correct,
                    },
                )

        total_long = correct_long + incorrect_long + unknown_long
        total_short = correct_short + incorrect_short + unknown_short
        evaluated_long = correct_long + incorrect_long
        evaluated_short = correct_short + incorrect_short
        total_evaluated = evaluated_long + evaluated_short
        correct_predictions = correct_long + correct_short

        win_rate = (
            correct_predictions / total_evaluated
            if total_evaluated > 0
            else None
        )

        return {
            "portfolio_manager": {
                "total_predictions": total_evaluated,
                "correct_predictions": correct_predictions,
                "win_rate": win_rate,
                "bull": {
                    "n": total_long,
                    "win": correct_long,
                    "unknown": unknown_long,
                },
                "bear": {
                    "n": total_short,
                    "win": correct_short,
                    "unknown": unknown_short,
                },
                "hold": hold_count,
                "signals": individual_signals,
            },
        }


def update_leaderboard_with_evaluations(
    leaderboard: List[Dict[str, Any]],
    evaluations: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Update leaderboard with new evaluation results

    Args:
        leaderboard: Current leaderboard data
        evaluations: Evaluation results for the day

    Returns:
        Updated leaderboard
    """
    for entry in leaderboard:
        agent_id = entry.get("agentId")
        if not agent_id or agent_id not in evaluations:
            continue

        eval_result = evaluations[agent_id]

        # Update aggregate stats
        entry["bull"]["n"] += eval_result["bull"]["n"]
        entry["bull"]["win"] += eval_result["bull"]["win"]
        entry["bull"]["unknown"] = (
            entry["bull"].get("unknown", 0) + eval_result["bull"]["unknown"]
        )
        entry["bear"]["n"] += eval_result["bear"]["n"]
        entry["bear"]["win"] += eval_result["bear"]["win"]
        entry["bear"]["unknown"] = (
            entry["bear"].get("unknown", 0) + eval_result["bear"]["unknown"]
        )

        # Calculate win rate based on evaluated signals only
        # evaluated = total - unknown
        evaluated_bull = entry["bull"]["n"] - entry["bull"]["unknown"]
        evaluated_bear = entry["bear"]["n"] - entry["bear"]["unknown"]
        total_evaluated = evaluated_bull + evaluated_bear
        total_wins = entry["bull"]["win"] + entry["bear"]["win"]

        if total_evaluated > 0:
            entry["winRate"] = round(total_wins / total_evaluated, 4)

        # Add individual signal records
        if "signals" not in entry:
            entry["signals"] = []

        for signal in eval_result.get("signals", []):
            entry["signals"].append(signal)

        # Keep only recent signals (e.g., last 100 individual signals)
        entry["signals"] = entry["signals"][-100:]

    # Re-rank analysts by win rate (rank starts from 1)
    analyst_entries = [e for e in leaderboard if e.get("rank") is not None]
    analyst_entries.sort(key=lambda e: e.get("winRate", 0), reverse=True)
    for idx, entry in enumerate(analyst_entries):
        entry["rank"] = idx + 1  # Rank 1 = highest win rate (gold medal)

    return leaderboard
