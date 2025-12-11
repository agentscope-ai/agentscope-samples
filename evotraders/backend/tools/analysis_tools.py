# -*- coding: utf-8 -*-
"""
Analysis tools for fundamental, technical, sentiment, and valuation analysis.

All tools accept tickers as List[str] with default from analysis context.
Returns human-readable text format for easy LLM consumption.
"""
# flake8: noqa: E501
# pylint: disable=C0301,W0613
import logging
import traceback
from datetime import datetime, timedelta
from functools import wraps
from statistics import median
from typing import List, Optional

import numpy as np
import pandas as pd
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from backend.tools.data_tools import (
    get_company_news,
    get_financial_metrics,
    get_insider_trades,
    get_market_cap,
    get_prices,
    prices_to_df,
    search_line_items,
)

logger = logging.getLogger(__name__)


def _to_text_response(text: str) -> ToolResponse:
    """Convert text string to ToolResponse."""
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def _safe_float(value, default=0.0) -> float:
    """Safely convert to float."""
    try:
        if pd.isna(value) or np.isnan(value):
            return default
        return float(value)
    except (ValueError, TypeError, OverflowError):
        return default


def safe(func):
    """Decorator to catch exceptions in tool functions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return _to_text_response(f"[ERROR] {error_msg}")

    return wrapper


def _fmt(val, fmt=".2f", suffix="") -> str:
    """Format value with handling for None."""
    if val is None:
        return "N/A"
    try:
        return f"{val:{fmt}}{suffix}"
    except (ValueError, TypeError):
        return str(val)


def _resolved_date(current_date: Optional[str]) -> str:
    """Ensure we always return a concrete date string."""
    return current_date or datetime.today().strftime("%Y-%m-%d")


# ==================== Fundamental Analysis Tools ====================


@safe
def analyze_efficiency_ratios(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze asset utilization efficiency ratios for stocks.

    Evaluates how efficiently companies use assets to generate revenue.
    Higher ratios generally indicate better operational efficiency.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of efficiency metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Efficiency Ratios Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(ticker=ticker, end_date=current_date)
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        lines.append(f"{ticker}:")
        lines.append(f"  Asset Turnover: {_fmt(m.asset_turnover)}")
        lines.append(f"  Inventory Turnover: {_fmt(m.inventory_turnover)}")
        lines.append(f"  Receivables Turnover: {_fmt(m.receivables_turnover)}")
        lines.append(
            f"  Working Capital Turnover: {_fmt(m.working_capital_turnover)}",
        )
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_profitability(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze profitability metrics for stocks.

    Assesses how effectively companies generate profit from operations and equity.
    Higher margins indicate stronger profitability and better cost management.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of profitability metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Profitability Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(ticker=ticker, end_date=current_date)
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        roe = _safe_float(m.return_on_equity)
        net_margin = _safe_float(m.net_margin)
        op_margin = _safe_float(m.operating_margin)
        lines.append(f"{ticker}:")
        lines.append(f"  Return on Equity (ROE): {_fmt(roe/100, '.1%')}")
        lines.append(f"  Net Margin: {_fmt(net_margin/100, '.1%')}")
        lines.append(f"  Operating Margin: {_fmt(op_margin/100, '.1%')}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_growth(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze growth metrics for stocks.

    Evaluates company growth trajectory across key financial dimensions.
    Higher growth rates may indicate strong business momentum.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of growth metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Growth Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(ticker=ticker, end_date=current_date)
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        lines.append(f"{ticker}:")
        lines.append(f"  Revenue Growth: {_fmt(m.revenue_growth, '.1%')}")
        lines.append(f"  Earnings Growth: {_fmt(m.earnings_growth, '.1%')}")
        lines.append(
            f"  Book Value Growth: {_fmt(m.book_value_growth, '.1%')}",
        )
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_financial_health(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze financial health metrics for stocks.

    Assesses financial stability and ability to meet obligations.
    Strong financial health suggests lower bankruptcy risk.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of financial health metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Financial Health Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(ticker=ticker, end_date=current_date)
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        lines.append(f"{ticker}:")
        lines.append(
            f"  Current Ratio: {_fmt(m.current_ratio)} (>1 is healthy)",
        )
        lines.append(f"  Debt to Equity: {_fmt(m.debt_to_equity)}")
        lines.append(
            f"  Free Cash Flow/Share: ${_fmt(m.free_cash_flow_per_share)}",
        )
        lines.append(f"  EPS: ${_fmt(m.earnings_per_share)}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_valuation_ratios(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze valuation ratios for stocks.

    Evaluates whether stocks are overvalued or undervalued using common multiples.
    Lower ratios may indicate undervaluation but compare with industry peers.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of valuation ratios for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Valuation Ratios Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(ticker=ticker, end_date=current_date)
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        lines.append(f"{ticker}:")
        lines.append(f"  P/E Ratio: {_fmt(m.price_to_earnings_ratio)}")
        lines.append(f"  P/B Ratio: {_fmt(m.price_to_book_ratio)}")
        lines.append(f"  P/S Ratio: {_fmt(m.price_to_sales_ratio)}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def get_financial_metrics_tool(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
    period: str = "ttm",
) -> ToolResponse:
    """
    Get comprehensive financial metrics for stocks.

    Retrieves complete set of financial metrics for fundamental analysis.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.
        period: Time period - 'ttm', 'quarterly', or 'annual'. Default 'ttm'.

    Returns:
        Text summary of all available financial metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [
        f"=== Comprehensive Financial Metrics ({current_date}, {period}) ===\n",
    ]

    for ticker in tickers:
        metrics = get_financial_metrics(
            ticker=ticker,
            end_date=current_date,
            period=period,
        )
        if not metrics:
            lines.append(f"{ticker}: No data available\n")
            continue

        m = metrics[0]
        lines.append(f"{ticker}:")
        lines.append(f"  Market Cap: ${_fmt(m.market_cap, ',.0f')}")
        lines.append(
            f"  P/E: {_fmt(m.price_to_earnings_ratio)} | P/B: {_fmt(m.price_to_book_ratio)} | P/S: {_fmt(m.price_to_sales_ratio)}",
        )
        lines.append(
            f"  ROE: {_fmt(m.return_on_equity, '.1%')} | Net Margin: {_fmt(m.net_margin, '.1%')}",
        )
        lines.append(
            f"  Revenue Growth: {_fmt(m.revenue_growth, '.1%')} | Earnings Growth: {_fmt(m.earnings_growth, '.1%')}",
        )
        lines.append(
            f"  Current Ratio: {_fmt(m.current_ratio)} | D/E: {_fmt(m.debt_to_equity)}",
        )
        lines.append(
            f"  EPS: ${_fmt(m.earnings_per_share)} | FCF/Share: ${_fmt(m.free_cash_flow_per_share)}",
        )
        lines.append("")

    return _to_text_response("\n".join(lines))


# ==================== Technical Analysis Tools ====================


@safe
def analyze_trend_following(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Trend following analysis using moving averages and MACD.

    Identifies market trends using SMA (20/50/200) and MACD indicators.
    Helps determine if stocks are in uptrend, downtrend, or consolidation.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of trend analysis for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Trend Following Analysis ({current_date}) ===\n"]

    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    extended_start = (end_dt - timedelta(days=250)).strftime("%Y-%m-%d")

    for ticker in tickers:
        prices = get_prices(
            ticker=ticker,
            start_date=extended_start,
            end_date=current_date,
        )
        if not prices or len(prices) < 10:
            lines.append(f"{ticker}: Insufficient price data\n")
            continue

        df = prices_to_df(prices)
        n = len(df)

        # Calculate moving averages
        sma_20_win = min(20, n // 2)
        sma_50_win = min(50, n - 5) if n > 25 else min(25, n - 5)
        sma_200_win = min(200, n - 10) if n > 200 else None

        df["SMA_20"] = df["close"].rolling(window=sma_20_win).mean()
        df["SMA_50"] = df["close"].rolling(window=sma_50_win).mean()
        if sma_200_win:
            df["SMA_200"] = df["close"].rolling(window=sma_200_win).mean()

        df["EMA_12"] = df["close"].ewm(span=min(12, n // 3)).mean()
        df["EMA_26"] = df["close"].ewm(span=min(26, n // 2)).mean()
        df["MACD"] = df["EMA_12"] - df["EMA_26"]
        df["MACD_signal"] = df["MACD"].ewm(span=9).mean()

        current_price = _safe_float(df["close"].iloc[-1])
        sma_20 = _safe_float(df["SMA_20"].iloc[-1])
        sma_50 = _safe_float(df["SMA_50"].iloc[-1])
        sma_200 = (
            _safe_float(df["SMA_200"].iloc[-1])
            if "SMA_200" in df.columns
            else None
        )
        macd = _safe_float(df["MACD"].iloc[-1])
        macd_signal = _safe_float(df["MACD_signal"].iloc[-1])

        # Determine trend
        if sma_200:
            trend = "BULLISH" if current_price > sma_200 else "BEARISH"
            distance_200ma = ((current_price - sma_200) / sma_200) * 100
        else:
            trend = "UNKNOWN"
            distance_200ma = None

        macd_signal_str = "BUY" if macd > macd_signal else "SELL"

        lines.append(f"{ticker}: ${current_price:.2f}")
        lines.append(
            f"  SMA20: ${sma_20:.2f} | SMA50: ${sma_50:.2f} | SMA200: {f'${sma_200:.2f}' if sma_200 else 'N/A'}",
        )
        lines.append(
            f"  MACD: {macd:.3f} | Signal: {macd_signal:.3f} -> {macd_signal_str}",
        )
        lines.append(
            f"  Long-term Trend: {trend}"
            + (
                f" ({distance_200ma:+.1f}% from 200MA)"
                if distance_200ma
                else ""
            ),
        )
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_mean_reversion(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Mean reversion analysis using Bollinger Bands and RSI.

    Identifies overbought/oversold conditions.
    RSI >70 = overbought, <30 = oversold.
    Price near bands may signal reversal.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of mean reversion signals for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Mean Reversion Analysis ({current_date}) ===\n"]

    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    extended_start = (end_dt - timedelta(days=60)).strftime("%Y-%m-%d")

    for ticker in tickers:
        prices = get_prices(
            ticker=ticker,
            start_date=extended_start,
            end_date=current_date,
        )
        if not prices or len(prices) < 5:
            lines.append(f"{ticker}: Insufficient price data\n")
            continue

        df = prices_to_df(prices)
        n = len(df)

        # Bollinger Bands
        window = min(20, n - 2)
        df["SMA"] = df["close"].rolling(window=window).mean()
        df["STD"] = df["close"].rolling(window=window).std()
        df["Upper_Band"] = df["SMA"] + (2 * df["STD"])
        df["Lower_Band"] = df["SMA"] - (2 * df["STD"])

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        current_price = _safe_float(df["close"].iloc[-1])
        sma = _safe_float(df["SMA"].iloc[-1])
        upper = _safe_float(df["Upper_Band"].iloc[-1])
        lower = _safe_float(df["Lower_Band"].iloc[-1])
        rsi = _safe_float(df["RSI"].iloc[-1])
        deviation = (current_price - sma) / sma * 100

        # Signal interpretation
        if rsi > 70:
            rsi_signal = "OVERBOUGHT"
        elif rsi < 30:
            rsi_signal = "OVERSOLD"
        else:
            rsi_signal = "NEUTRAL"

        if current_price > upper:
            bb_signal = "ABOVE UPPER BAND (potential sell)"
        elif current_price < lower:
            bb_signal = "BELOW LOWER BAND (potential buy)"
        else:
            bb_signal = "WITHIN BANDS"

        lines.append(f"{ticker}: ${current_price:.2f}")
        lines.append(
            f"  Bollinger: Lower ${lower:.2f} | SMA ${sma:.2f} | Upper ${upper:.2f}",
        )
        lines.append(f"  Position: {bb_signal}")
        lines.append(f"  RSI: {rsi:.1f} -> {rsi_signal}")
        lines.append(f"  Price Deviation from SMA: {deviation:+.1f}%")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_momentum(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Momentum analysis for different time periods.

    Measures price momentum over 5, 10, and 20 day periods.
    Positive momentum indicates upward price pressure.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of momentum indicators for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Momentum Analysis ({current_date}) ===\n"]

    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    extended_start = (end_dt - timedelta(days=45)).strftime("%Y-%m-%d")

    for ticker in tickers:
        prices = get_prices(
            ticker=ticker,
            start_date=extended_start,
            end_date=current_date,
        )
        if not prices or len(prices) < 5:
            lines.append(f"{ticker}: Insufficient price data\n")
            continue

        df = prices_to_df(prices)
        n = len(df)
        df["returns"] = df["close"].pct_change()

        # Adaptive periods
        short_p = min(5, n // 3)
        med_p = min(10, n // 2)
        long_p = min(20, n - 2)

        current_price = _safe_float(df["close"].iloc[-1])
        mom_5 = (
            _safe_float(
                (df["close"].iloc[-1] / df["close"].iloc[-short_p - 1] - 1)
                * 100,
            )
            if n > short_p
            else 0
        )
        mom_10 = (
            _safe_float(
                (df["close"].iloc[-1] / df["close"].iloc[-med_p - 1] - 1)
                * 100,
            )
            if n > med_p
            else 0
        )
        mom_20 = (
            _safe_float(
                (df["close"].iloc[-1] / df["close"].iloc[-long_p - 1] - 1)
                * 100,
            )
            if n > long_p
            else 0
        )
        volatility = _safe_float(
            df["returns"].tail(20).std() * np.sqrt(252) * 100,
        )

        # Overall momentum signal
        avg_mom = (mom_5 + mom_10 + mom_20) / 3
        if avg_mom > 2:
            signal = "STRONG BULLISH"
        elif avg_mom > 0:
            signal = "BULLISH"
        elif avg_mom > -2:
            signal = "BEARISH"
        else:
            signal = "STRONG BEARISH"

        lines.append(f"{ticker}: ${current_price:.2f}")
        lines.append(
            f"  5-day: {mom_5:+.1f}% | 10-day: {mom_10:+.1f}% | 20-day: {mom_20:+.1f}%",
        )
        lines.append(f"  Volatility (annualized): {volatility:.1f}%")
        lines.append(f"  Overall: {signal}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_volatility(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Volatility analysis for different time windows.

    Measures price volatility over 10, 20, and 60 day periods.
    Higher volatility indicates higher risk but potentially higher returns.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date (YYYY-MM-DD). If None, uses date from context.

    Returns:
        Text summary of volatility metrics for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Volatility Analysis ({current_date}) ===\n"]

    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    extended_start = (end_dt - timedelta(days=90)).strftime("%Y-%m-%d")

    for ticker in tickers:
        prices = get_prices(
            ticker=ticker,
            start_date=extended_start,
            end_date=current_date,
        )
        if not prices or len(prices) < 5:
            lines.append(f"{ticker}: Insufficient price data\n")
            continue

        df = prices_to_df(prices)
        n = len(df)
        df["returns"] = df["close"].pct_change()

        # Adaptive windows
        short_w = min(10, n // 2)
        med_w = min(20, n - 2)
        long_w = min(60, n - 1) if n > 30 else med_w

        current_price = _safe_float(df["close"].iloc[-1])
        vol_10 = _safe_float(
            df["returns"].tail(short_w).std() * np.sqrt(252) * 100,
        )
        vol_20 = _safe_float(
            df["returns"].tail(med_w).std() * np.sqrt(252) * 100,
        )
        vol_60 = _safe_float(
            df["returns"].tail(long_w).std() * np.sqrt(252) * 100,
        )

        # Risk assessment
        if vol_20 > 50:
            risk = "HIGH RISK"
        elif vol_20 > 25:
            risk = "MODERATE RISK"
        else:
            risk = "LOW RISK"

        lines.append(f"{ticker}: ${current_price:.2f}")
        lines.append(
            f"  10-day Vol: {vol_10:.1f}% | 20-day Vol: {vol_20:.1f}% | 60-day Vol: {vol_60:.1f}%",
        )
        lines.append(f"  Risk Level: {risk}")
        lines.append("")

    return _to_text_response("\n".join(lines))


# ==================== Sentiment Analysis Tools ====================


@safe
def analyze_insider_trading(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
    start_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze insider trading activity.

    Tracks buying/selling by company insiders (executives, directors).
    Insider buying can signal confidence; selling may indicate concerns.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.
        start_date: Optional start date for lookback period.

    Returns:
        Text summary of insider trading activity for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Insider Trading Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        trades = get_insider_trades(
            ticker=ticker,
            end_date=current_date,
            start_date=start_date,
            limit=1000,
        )

        if not trades:
            lines.append(f"{ticker}: No insider trading data\n")
            continue

        shares = pd.Series([t.transaction_shares for t in trades]).dropna()

        if len(shares) == 0:
            lines.append(f"{ticker}: {len(trades)} trades but no share data\n")
            continue

        buy_count = int((shares > 0).sum())
        sell_count = int((shares < 0).sum())
        buy_vol = float(shares[shares > 0].sum())
        sell_vol = float(abs(shares[shares < 0].sum()))

        # Sentiment interpretation
        if buy_count > sell_count * 2:
            sentiment = "STRONG INSIDER BUYING"
        elif buy_count > sell_count:
            sentiment = "NET INSIDER BUYING"
        elif sell_count > buy_count * 2:
            sentiment = "STRONG INSIDER SELLING"
        elif sell_count > buy_count:
            sentiment = "NET INSIDER SELLING"
        else:
            sentiment = "MIXED INSIDER ACTIVITY"

        lines.append(f"{ticker}:")
        lines.append(f"  Buys: {buy_count} trades ({buy_vol:,.0f} shares)")
        lines.append(f"  Sells: {sell_count} trades ({sell_vol:,.0f} shares)")
        lines.append(f"  Signal: {sentiment}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def analyze_news_sentiment(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
    start_date: Optional[str] = None,
) -> ToolResponse:
    """
    Analyze recent news for stocks.

    Retrieves and summarizes recent news articles.
    Use this to understand recent events and market sentiment.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.
        start_date: Optional start date for lookback period.

    Returns:
        Text summary of recent news for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== News Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        news = get_company_news(
            ticker=ticker,
            end_date=current_date,
            start_date=start_date,
            limit=10,
        )

        if not news:
            lines.append(f"{ticker}: No recent news\n")
            continue

        lines.append(f"{ticker} - {len(news)} recent articles:")
        for i, n in enumerate(news[:5], 1):
            date_str = n.date[:10] if n.date else "N/A"
            lines.append(f"  {i}. [{date_str}] {n.title[:80]}...")
            lines.append(f"     Source: {n.source}")
        if len(news) > 5:
            lines.append(f"  ... and {len(news) - 5} more articles")
        lines.append("")

    return _to_text_response("\n".join(lines))


# ==================== Valuation Analysis Tools ====================


@safe
def dcf_valuation_analysis(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Discounted Cash Flow (DCF) valuation analysis.

    Estimates intrinsic value by projecting future free cash flows.
    Positive value_gap indicates potential undervaluation.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.

    Returns:
        Text summary of DCF valuation for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== DCF Valuation Analysis ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(
            ticker=ticker,
            end_date=current_date,
            limit=8,
        )
        if not metrics:
            lines.append(f"{ticker}: No financial metrics\n")
            continue

        line_items = search_line_items(
            ticker=ticker,
            line_items=["free_cash_flow"],
            end_date=current_date,
            period="ttm",
            limit=2,
        )
        if (
            not line_items
            or not line_items[0].free_cash_flow
            or line_items[0].free_cash_flow <= 0
        ):
            lines.append(f"{ticker}: Invalid free cash flow data\n")
            continue

        market_cap = get_market_cap(ticker, current_date)
        if not market_cap:
            lines.append(f"{ticker}: Market cap unavailable\n")
            continue

        m = metrics[0]
        current_fcf = line_items[0].free_cash_flow
        growth_rate = m.earnings_growth or 0.05
        discount_rate = 0.10
        terminal_growth = 0.03
        num_years = 5

        # DCF calculation
        pv_fcf = sum(
            current_fcf
            * (1 + growth_rate) ** year
            / (1 + discount_rate) ** year
            for year in range(1, num_years + 1)
        )
        terminal_fcf = (
            current_fcf
            * (1 + growth_rate) ** num_years
            * (1 + terminal_growth)
        )
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / (1 + discount_rate) ** num_years
        enterprise_value = pv_fcf + pv_terminal
        value_gap = (enterprise_value - market_cap) / market_cap * 100

        # Assessment
        if value_gap > 20:
            assessment = "SIGNIFICANTLY UNDERVALUED"
        elif value_gap > 0:
            assessment = "POTENTIALLY UNDERVALUED"
        elif value_gap > -20:
            assessment = "POTENTIALLY OVERVALUED"
        else:
            assessment = "SIGNIFICANTLY OVERVALUED"

        lines.append(f"{ticker}:")
        lines.append(f"  Current FCF: ${current_fcf:,.0f}")
        lines.append(f"  DCF Enterprise Value: ${enterprise_value:,.0f}")
        lines.append(f"  Market Cap: ${market_cap:,.0f}")
        lines.append(f"  Value Gap: {value_gap:+.1f}% -> {assessment}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def owner_earnings_valuation_analysis(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Buffett-style owner earnings valuation analysis.

    Owner earnings = Net Income + D&A - CapEx - Working Capital Changes.
    Represents true cash owners could extract from the business.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.

    Returns:
        Text summary of owner earnings valuation for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Owner Earnings Valuation ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(
            ticker=ticker,
            end_date=current_date,
            limit=8,
        )
        if not metrics:
            lines.append(f"{ticker}: No financial metrics\n")
            continue

        line_items = search_line_items(
            ticker=ticker,
            line_items=[
                "net_income",
                "depreciation_and_amortization",
                "capital_expenditure",
                "working_capital",
            ],
            end_date=current_date,
            period="ttm",
            limit=2,
        )
        if len(line_items) < 2:
            lines.append(f"{ticker}: Insufficient financial data\n")
            continue

        market_cap = get_market_cap(ticker, current_date)
        if not market_cap:
            lines.append(f"{ticker}: Market cap unavailable\n")
            continue

        m = metrics[0]
        current, previous = line_items[0], line_items[1]

        net_income = current.net_income or 0
        depreciation = current.depreciation_and_amortization or 0
        capex = current.capital_expenditure or 0
        wc_change = (current.working_capital or 0) - (
            previous.working_capital or 0
        )

        owner_earnings = net_income + depreciation - capex - wc_change
        if owner_earnings <= 0:
            lines.append(
                f"{ticker}: Negative owner earnings (${owner_earnings:,.0f})\n",
            )
            continue

        # Valuation
        growth_rate = m.earnings_growth or 0.05
        required_return = 0.15
        margin_of_safety = 0.25
        num_years = 5

        pv_earnings = sum(
            owner_earnings
            * (1 + growth_rate) ** year
            / (1 + required_return) ** year
            for year in range(1, num_years + 1)
        )
        terminal_growth = min(growth_rate, 0.03)
        terminal_earnings = (
            owner_earnings
            * (1 + growth_rate) ** num_years
            * (1 + terminal_growth)
        )
        terminal_value = terminal_earnings / (
            required_return - terminal_growth
        )
        pv_terminal = terminal_value / (1 + required_return) ** num_years

        intrinsic_value = (pv_earnings + pv_terminal) * (1 - margin_of_safety)
        value_gap = (intrinsic_value - market_cap) / market_cap * 100

        # Assessment
        if value_gap > 20:
            assessment = "SIGNIFICANTLY UNDERVALUED"
        elif value_gap > 0:
            assessment = "POTENTIALLY UNDERVALUED"
        elif value_gap > -20:
            assessment = "POTENTIALLY OVERVALUED"
        else:
            assessment = "SIGNIFICANTLY OVERVALUED"

        lines.append(f"{ticker}:")
        lines.append(f"  Owner Earnings: ${owner_earnings:,.0f}")
        lines.append(
            f"  Intrinsic Value (w/ 25% MoS): ${intrinsic_value:,.0f}",
        )
        lines.append(f"  Market Cap: ${market_cap:,.0f}")
        lines.append(f"  Value Gap: {value_gap:+.1f}% -> {assessment}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def ev_ebitda_valuation_analysis(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    EV/EBITDA multiple valuation analysis.

    Compares current EV/EBITDA to historical median.
    Lower multiples relative to history may indicate undervaluation.

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.

    Returns:
        Text summary of EV/EBITDA valuation for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== EV/EBITDA Valuation ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(
            ticker=ticker,
            end_date=current_date,
            limit=8,
        )
        if not metrics:
            lines.append(f"{ticker}: No financial metrics\n")
            continue

        m = metrics[0]
        if (
            not m.enterprise_value
            or not m.enterprise_value_to_ebitda_ratio
            or m.enterprise_value_to_ebitda_ratio <= 0
        ):
            lines.append(f"{ticker}: Missing EV/EBITDA data\n")
            continue

        market_cap = get_market_cap(ticker, current_date)
        if not market_cap:
            lines.append(f"{ticker}: Market cap unavailable\n")
            continue

        current_ebitda = (
            m.enterprise_value / m.enterprise_value_to_ebitda_ratio
        )

        valid_multiples = [
            x.enterprise_value_to_ebitda_ratio
            for x in metrics
            if x.enterprise_value_to_ebitda_ratio
            and x.enterprise_value_to_ebitda_ratio > 0
        ]
        if len(valid_multiples) < 3:
            lines.append(f"{ticker}: Insufficient historical data\n")
            continue

        median_multiple = median(valid_multiples)
        current_multiple = m.enterprise_value_to_ebitda_ratio

        implied_ev = median_multiple * current_ebitda
        net_debt = m.enterprise_value - market_cap
        implied_equity = max(implied_ev - net_debt, 0)

        value_gap = (
            (implied_equity - market_cap) / market_cap * 100
            if market_cap > 0
            else 0
        )
        multiple_discount = (
            (median_multiple - current_multiple) / median_multiple * 100
        )

        # Assessment
        if multiple_discount > 10:
            assessment = "TRADING BELOW HISTORICAL MULTIPLE"
        elif multiple_discount > -10:
            assessment = "NEAR HISTORICAL AVERAGE"
        else:
            assessment = "TRADING ABOVE HISTORICAL MULTIPLE"

        lines.append(f"{ticker}:")
        lines.append(f"  Current EV/EBITDA: {current_multiple:.1f}x")
        lines.append(f"  Historical Median: {median_multiple:.1f}x")
        lines.append(f"  Multiple vs History: {multiple_discount:+.1f}%")
        lines.append(f"  Implied Equity Value: ${implied_equity:,.0f}")
        lines.append(f"  Value Gap: {value_gap:+.1f}% -> {assessment}")
        lines.append("")

    return _to_text_response("\n".join(lines))


@safe
def residual_income_valuation_analysis(
    tickers: Optional[List[str]] = None,
    current_date: Optional[str] = None,
) -> ToolResponse:
    """
    Residual Income Model (RIM) valuation analysis.

    Values company based on book value plus PV of future residual income.
    Residual income = Net Income - (Cost of Equity x Book Value).

    Args:
        tickers: List of stock tickers. If None, uses all tickers from context.
        current_date: Analysis date. If None, uses date from context.

    Returns:
        Text summary of residual income valuation for all tickers.
    """

    current_date = _resolved_date(current_date)
    lines = [f"=== Residual Income Valuation ({current_date}) ===\n"]

    for ticker in tickers:
        metrics = get_financial_metrics(
            ticker=ticker,
            end_date=current_date,
            limit=8,
        )
        if not metrics:
            lines.append(f"{ticker}: No financial metrics\n")
            continue

        line_items = search_line_items(
            ticker=ticker,
            line_items=["net_income"],
            end_date=current_date,
            period="ttm",
            limit=1,
        )
        if not line_items or not line_items[0].net_income:
            lines.append(f"{ticker}: No net income data\n")
            continue

        market_cap = get_market_cap(ticker, current_date)
        if not market_cap:
            lines.append(f"{ticker}: Market cap unavailable\n")
            continue

        m = metrics[0]
        if not m.price_to_book_ratio or m.price_to_book_ratio <= 0:
            lines.append(f"{ticker}: Invalid P/B ratio\n")
            continue

        net_income = line_items[0].net_income
        pb_ratio = m.price_to_book_ratio
        book_value = market_cap / pb_ratio

        # Model parameters
        cost_of_equity = 0.10
        bv_growth = m.book_value_growth or 0.03
        terminal_growth = 0.03
        num_years = 5
        margin_of_safety = 0.20

        initial_ri = net_income - cost_of_equity * book_value
        if initial_ri <= 0:
            lines.append(f"{ticker}: Negative residual income\n")
            continue

        # PV calculation
        pv_ri = sum(
            initial_ri * (1 + bv_growth) ** year / (1 + cost_of_equity) ** year
            for year in range(1, num_years + 1)
        )
        terminal_ri = initial_ri * (1 + bv_growth) ** (num_years + 1)
        terminal_value = terminal_ri / (cost_of_equity - terminal_growth)
        pv_terminal = terminal_value / (1 + cost_of_equity) ** num_years

        intrinsic_value = (book_value + pv_ri + pv_terminal) * (
            1 - margin_of_safety
        )
        value_gap = (intrinsic_value - market_cap) / market_cap * 100

        lines.append(f"{ticker}:")
        lines.append(f"  Book Value: ${book_value:,.0f}")
        lines.append(f"  Residual Income: ${initial_ri:,.0f}")
        lines.append(
            f"  Intrinsic Value (w/ 20% MoS): ${intrinsic_value:,.0f}",
        )
        lines.append(f"  Value Gap: {value_gap:+.1f}%")
        lines.append("")

    return _to_text_response("\n".join(lines))


# Tool Registry for dynamic toolkit creation
TOOL_REGISTRY = {
    "analyze_efficiency_ratios": analyze_efficiency_ratios,
    "analyze_profitability": analyze_profitability,
    "analyze_growth": analyze_growth,
    "analyze_financial_health": analyze_financial_health,
    "analyze_valuation_ratios": analyze_valuation_ratios,
    "get_financial_metrics_tool": get_financial_metrics_tool,
    "analyze_trend_following": analyze_trend_following,
    "analyze_mean_reversion": analyze_mean_reversion,
    "analyze_momentum": analyze_momentum,
    "analyze_volatility": analyze_volatility,
    "analyze_insider_trading": analyze_insider_trading,
    "analyze_news_sentiment": analyze_news_sentiment,
    "dcf_valuation_analysis": dcf_valuation_analysis,
    "owner_earnings_valuation_analysis": owner_earnings_valuation_analysis,
    "ev_ebitda_valuation_analysis": ev_ebitda_valuation_analysis,
    "residual_income_valuation_analysis": residual_income_valuation_analysis,
}
