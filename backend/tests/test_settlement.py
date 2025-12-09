# -*- coding: utf-8 -*-
"""
Test Settlement Coordinator and Baseline Calculations
"""

from backend.utils.baselines import (
    BaselineCalculator,
    calculate_momentum_scores,
)
from backend.utils.analyst_tracker import (
    AnalystPerformanceTracker,
    update_leaderboard_with_evaluations,
)


def test_baseline_equal_weight():
    """Test equal weight baseline calculation"""
    calculator = BaselineCalculator(initial_capital=100000.0)

    tickers = ["AAPL", "MSFT", "GOOGL"]
    prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 120.0}
    openprices = {"AAPL": 160.0, "MSFT": 310.0, "GOOGL": 110.0}
    value = calculator.calculate_equal_weight_value(
        tickers,
        openprices,
        prices,
    )

    assert value > 0
    assert calculator.equal_weight_initialized is True


def test_baseline_market_cap_weighted():
    """Test market cap weighted baseline calculation"""
    calculator = BaselineCalculator(initial_capital=100000.0)

    tickers = ["AAPL", "MSFT", "GOOGL"]
    prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 120.0}
    openprices = {"AAPL": 160.0, "MSFT": 310.0, "GOOGL": 110.0}
    market_caps = {"AAPL": 3e12, "MSFT": 2e12, "GOOGL": 1.5e12}

    value = calculator.calculate_market_cap_weighted_value(
        tickers,
        openprices,
        prices,
        market_caps,
    )

    assert value > 0
    assert calculator.market_cap_initialized is True


def test_momentum_scores():
    """Test momentum score calculation"""
    tickers = ["AAPL", "MSFT"]
    prices_history = {
        "AAPL": [
            ("2024-01-01", 100.0),
            ("2024-01-02", 105.0),
            ("2024-01-03", 110.0),
        ],
        "MSFT": [
            ("2024-01-01", 200.0),
            ("2024-01-02", 195.0),
            ("2024-01-03", 190.0),
        ],
    }

    scores = calculate_momentum_scores(
        tickers,
        prices_history,
        lookback_days=2,
    )

    assert scores["AAPL"] > 0
    assert scores["MSFT"] < 0


def test_analyst_tracker_predictions():
    """Test analyst prediction recording with structured format"""
    tracker = AnalystPerformanceTracker()

    final_predictions = [
        {
            "agent": "technical_analyst",
            "predictions": [
                {"ticker": "AAPL", "direction": "up", "confidence": 0.8},
                {"ticker": "MSFT", "direction": "down", "confidence": 0.7},
                {"ticker": "GOOGL", "direction": "neutral", "confidence": 0.5},
            ],
        },
        {
            "agent": "fundamentals_analyst",
            "predictions": [
                {"ticker": "AAPL", "direction": "up", "confidence": 0.9},
                {"ticker": "MSFT", "direction": "up", "confidence": 0.6},
                {"ticker": "GOOGL", "direction": "down", "confidence": 0.75},
            ],
        },
    ]

    tracker.record_analyst_predictions(final_predictions)

    assert "technical_analyst" in tracker.daily_predictions
    assert "fundamentals_analyst" in tracker.daily_predictions
    assert tracker.daily_predictions["technical_analyst"]["AAPL"] == "long"
    assert tracker.daily_predictions["technical_analyst"]["MSFT"] == "short"
    assert tracker.daily_predictions["technical_analyst"]["GOOGL"] == "hold"


def test_analyst_evaluation():
    """Test analyst prediction evaluation"""
    tracker = AnalystPerformanceTracker()

    tracker.daily_predictions = {
        "technical_analyst": {
            "AAPL": "long",
            "MSFT": "short",
        },
    }

    open_prices = {"AAPL": 100.0, "MSFT": 200.0}
    close_prices = {"AAPL": 105.0, "MSFT": 195.0}

    evaluations = tracker.evaluate_predictions(
        open_prices,
        close_prices,
        "2024-01-15",
    )

    assert "technical_analyst" in evaluations
    eval_result = evaluations["technical_analyst"]
    assert eval_result["correct_predictions"] == 2
    assert eval_result["win_rate"] == 1.0

    # Verify individual signals format
    assert "signals" in eval_result
    assert len(eval_result["signals"]) == 2
    for signal in eval_result["signals"]:
        assert "ticker" in signal
        assert "signal" in signal
        assert "date" in signal
        assert "is_correct" in signal
        assert signal["date"] == "2024-01-15"


def test_leaderboard_update():
    """Test leaderboard update with evaluations"""
    leaderboard = [
        {
            "agentId": "technical_analyst",
            "name": "Technical Analyst",
            "rank": 0,
            "winRate": None,
            "bull": {"n": 0, "win": 0, "unknown": 0},
            "bear": {"n": 0, "win": 0, "unknown": 0},
            "signals": [],
        },
    ]

    evaluations = {
        "technical_analyst": {
            "total_predictions": 2,
            "correct_predictions": 1,
            "win_rate": 0.5,
            "bull": {"n": 1, "win": 1, "unknown": 0},
            "bear": {"n": 1, "win": 0, "unknown": 0},
            "hold": 0,
            "signals": [
                {
                    "ticker": "AAPL",
                    "signal": "bull",
                    "date": "2024-01-01",
                    "is_correct": True,
                },
                {
                    "ticker": "MSFT",
                    "signal": "bear",
                    "date": "2024-01-01",
                    "is_correct": False,
                },
            ],
        },
    }

    updated = update_leaderboard_with_evaluations(
        leaderboard,
        evaluations,
    )

    assert updated[0]["bull"]["n"] == 1
    assert updated[0]["bull"]["win"] == 1
    assert updated[0]["winRate"] == 0.5
    assert len(updated[0]["signals"]) == 2

    # Verify signal format matches frontend expectations
    for signal in updated[0]["signals"]:
        assert "ticker" in signal
        assert "signal" in signal
        assert "date" in signal
        assert "is_correct" in signal
