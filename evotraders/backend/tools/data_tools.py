# -*- coding: utf-8 -*-
# flake8: noqa: E501
# pylint: disable=C0301
"""
Data fetching tools for financial data.

All functions use centralized data source configuration from data_config.py.
The data source is automatically determined based on available API keys:
- Priority: FINNHUB_API_KEY > FINANCIAL_DATASETS_API_KEY
"""
import datetime
import time

import finnhub
import pandas as pd
import pandas_market_calendars as mcal
import requests

from backend.config.data_config import (
    get_config,
    get_api_key,
)
from backend.data.cache import get_cache
from backend.data.schema import (
    CompanyFactsResponse,
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    InsiderTrade,
    InsiderTradeResponse,
    LineItem,
    LineItemResponse,
    Price,
    PriceResponse,
)
from backend.utils.settlement import logger

# Global cache instance
_cache = get_cache()


def get_last_tradeday(date: str) -> str:
    """
    Get the previous trading day for the specified date

    Args:
        date: Date string (YYYY-MM-DD)

    Returns:
        Previous trading day date string (YYYY-MM-DD)
    """
    current_date = datetime.datetime.strptime(date, "%Y-%m-%d")
    _NYSE_CALENDAR = mcal.get_calendar("NYSE")

    if _NYSE_CALENDAR is not None:
        # Get trading days before current date
        # Go back 90 days from current date to get all trading days
        start_search = current_date - datetime.timedelta(days=90)

        if hasattr(_NYSE_CALENDAR, "valid_days"):
            # pandas_market_calendars
            trading_dates = _NYSE_CALENDAR.valid_days(
                start_date=start_search.strftime("%Y-%m-%d"),
                end_date=current_date.strftime("%Y-%m-%d"),
            )
        else:
            # exchange_calendars
            trading_dates = _NYSE_CALENDAR.sessions_in_range(
                start_search.strftime("%Y-%m-%d"),
                current_date.strftime("%Y-%m-%d"),
            )

        # Convert to date list
        trading_dates_list = [
            pd.Timestamp(d).strftime("%Y-%m-%d") for d in trading_dates
        ]

        # Find current date position in the list
        if date in trading_dates_list:
            # If current date is a trading day, return previous trading day
            idx = trading_dates_list.index(date)
            if idx > 0:
                return trading_dates_list[idx - 1]
            else:
                # If it's the first trading day, go back further
                prev_date = current_date - datetime.timedelta(days=1)
                return get_last_tradeday(prev_date.strftime("%Y-%m-%d"))
        else:
            # If current date is not a trading day, return the nearest trading day
            if trading_dates_list:
                return trading_dates_list[-1]

    return prev_date.strftime("%Y-%m-%d")


def _make_api_request(
    url: str,
    headers: dict,
    method: str = "GET",
    json_data: dict = None,
    max_retries: int = 3,
) -> requests.Response:
    """
    Make an API request with rate limiting handling and moderate backoff.

    Args:
        url: The URL to request
        headers: Headers to include in the request
        method: HTTP method (GET or POST)
        json_data: JSON data for POST requests
        max_retries: Maximum number of retries (default: 3)

    Returns:
        requests.Response: The response object

    Raises:
        Exception: If the request fails with a non-429 error
    """
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)

        if response.status_code == 429 and attempt < max_retries:
            # Linear backoff: 60s, 90s, 120s, 150s...
            delay = 60 + (30 * attempt)
            print(
                f"Rate limited (429). Attempt {attempt + 1}/{max_retries + 1}. Waiting {delay}s before retrying...",
            )
            time.sleep(delay)
            continue

        # Return the response (whether success, other errors, or final 429)
        return response


def get_prices(
    ticker: str,
    start_date: str,
    end_date: str,
) -> list[Price]:
    """
    Fetch price data from cache or API.

    Uses centralized data source configuration (FINNHUB_API_KEY prioritized).

    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        list[Price]: List of Price objects
    """
    config = get_config()
    data_source = config.source
    api_key = config.api_key

    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{start_date}_{end_date}_{data_source}"

    # Check cache first - simple exact match
    if cached_data := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached_data]

    prices = []

    if data_source == "finnhub":
        # Use Finnhub API
        client = finnhub.Client(api_key=api_key)

        # Convert dates to timestamps
        start_timestamp = int(
            datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp(),
        )
        end_timestamp = int(
            (
                datetime.datetime.strptime(end_date, "%Y-%m-%d")
                + datetime.timedelta(days=1)
            ).timestamp(),
        )

        # Fetch candle data from Finnhub
        candles = client.stock_candles(
            ticker,
            "D",
            start_timestamp,
            end_timestamp,
        )

        # Convert to Price objects
        for i in range(len(candles["t"])):
            price = Price(
                open=candles["o"][i],
                close=candles["c"][i],
                high=candles["h"][i],
                low=candles["l"][i],
                volume=int(candles["v"][i]),
                time=datetime.datetime.fromtimestamp(candles["t"][i]).strftime(
                    "%Y-%m-%d",
                ),
            )
            prices.append(price)

    else:  # financial_datasets
        # Use Financial Datasets API
        headers = {"X-API-KEY": api_key}

        url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            raise ValueError(
                f"Error fetching data: {ticker} - {response.status_code} - {response.text}",
            )

        # Parse response with Pydantic model
        price_response = PriceResponse(**response.json())
        prices = price_response.prices

    if not prices:
        return []

    # Cache the results using the comprehensive cache key
    _cache.set_prices(cache_key, [p.model_dump() for p in prices])
    return prices


def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
) -> list[FinancialMetrics]:
    """
    Fetch financial metrics from cache or API.

    Uses centralized data source configuration (FINNHUB_API_KEY prioritized).

    Args:
        ticker: Stock ticker symbol
        end_date: End date (YYYY-MM-DD)
        period: Period type (default: "ttm")
        limit: Number of records to fetch

    Returns:
        list[FinancialMetrics]: List of financial metrics
    """
    config = get_config()
    data_source = config.source
    api_key = config.api_key

    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{period}_{end_date}_{limit}_{data_source}"

    # Check cache first - simple exact match
    if cached_data := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**metric) for metric in cached_data]

    financial_metrics = []

    if data_source == "finnhub":
        # Use Finnhub API - Basic Financials
        client = finnhub.Client(api_key=api_key)

        # Fetch basic financials from Finnhub
        # metric='all' returns all available metrics
        financials = client.company_basic_financials(ticker, "all")

        if not financials or "metric" not in financials:
            return []

        # Finnhub returns {series: {...}, metric: {...}, metricType: ..., symbol: ...}
        # We need to create a FinancialMetrics object from this
        metric_data = financials.get("metric", {})

        # Create a FinancialMetrics object with available data
        metric = _map_finnhub_metrics(ticker, end_date, period, metric_data)

        financial_metrics = [metric]

    else:  # financial_datasets
        # Use Financial Datasets API
        headers = {"X-API-KEY": api_key}

        url = f"https://api.financialdatasets.ai/financial-metrics/?ticker={ticker}&report_period_lte={end_date}&limit={limit}&period={period}"
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            raise ValueError(
                f"Error fetching data: {ticker} - {response.status_code} - {response.text}",
            )

        # Parse response with Pydantic model
        metrics_response = FinancialMetricsResponse(**response.json())
        financial_metrics = metrics_response.financial_metrics

    if not financial_metrics:
        return []

    # Cache the results as dicts using the comprehensive cache key
    _cache.set_financial_metrics(
        cache_key,
        [m.model_dump() for m in financial_metrics],
    )
    return financial_metrics


def _map_finnhub_metrics(
    ticker: str,
    end_date: str,
    period: str,
    metric_data: dict,
) -> FinancialMetrics:
    """Map Finnhub metric data to FinancialMetrics model."""
    return FinancialMetrics(
        ticker=ticker,
        report_period=end_date,
        period=period,
        currency="USD",
        market_cap=metric_data.get("marketCapitalization"),
        enterprise_value=None,
        price_to_earnings_ratio=metric_data.get("peBasicExclExtraTTM"),
        price_to_book_ratio=metric_data.get("pbAnnual"),
        price_to_sales_ratio=metric_data.get("psAnnual"),
        enterprise_value_to_ebitda_ratio=None,
        enterprise_value_to_revenue_ratio=None,
        free_cash_flow_yield=None,
        peg_ratio=None,
        gross_margin=metric_data.get("grossMarginTTM"),
        operating_margin=metric_data.get("operatingMarginTTM"),
        net_margin=metric_data.get("netProfitMarginTTM"),
        return_on_equity=metric_data.get("roeTTM"),
        return_on_assets=metric_data.get("roaTTM"),
        return_on_invested_capital=metric_data.get("roicTTM"),
        asset_turnover=metric_data.get("assetTurnoverTTM"),
        inventory_turnover=metric_data.get("inventoryTurnoverTTM"),
        receivables_turnover=metric_data.get("receivablesTurnoverTTM"),
        days_sales_outstanding=None,
        operating_cycle=None,
        working_capital_turnover=None,
        current_ratio=metric_data.get("currentRatioAnnual"),
        quick_ratio=metric_data.get("quickRatioAnnual"),
        cash_ratio=None,
        operating_cash_flow_ratio=None,
        debt_to_equity=metric_data.get("totalDebt/totalEquityAnnual"),
        debt_to_assets=None,
        interest_coverage=None,
        revenue_growth=metric_data.get("revenueGrowthTTMYoy"),
        earnings_growth=None,
        book_value_growth=None,
        earnings_per_share_growth=metric_data.get("epsGrowthTTMYoy"),
        free_cash_flow_growth=None,
        operating_income_growth=None,
        ebitda_growth=None,
        payout_ratio=metric_data.get("payoutRatioAnnual"),
        earnings_per_share=metric_data.get("epsBasicExclExtraItemsTTM"),
        book_value_per_share=metric_data.get("bookValuePerShareAnnual"),
        free_cash_flow_per_share=None,
    )


def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
) -> list[LineItem]:
    """
    Fetch line items from Financial Datasets API (only supported source).

    Returns empty list on API errors to allow graceful degradation.
    """
    try:
        api_key = get_api_key()
        headers = {"X-API-KEY": api_key}

        url = "https://api.financialdatasets.ai/financials/search/line-items"
        body = {
            "tickers": [ticker],
            "line_items": line_items,
            "end_date": end_date,
            "period": period,
            "limit": limit,
        }
        response = _make_api_request(
            url,
            headers,
            method="POST",
            json_data=body,
        )

        if response.status_code != 200:
            logger.info(
                f"Warning: Failed to fetch line items for {ticker}: "
                f"{response.status_code} - {response.text}",
            )
            return []

        data = response.json()
        response_model = LineItemResponse(**data)
        search_results = response_model.search_results

        if not search_results:
            return []

        return search_results[:limit]

    except Exception as e:
        logger.info(
            f"Warning: Exception while fetching line items for {ticker}: {str(e)}",
        )
        return []


def _fetch_finnhub_insider_trades(
    ticker: str,
    start_date: str | None,
    end_date: str,
    limit: int,
    api_key: str,
) -> list[InsiderTrade]:
    """Fetch insider trades from Finnhub API."""
    client = finnhub.Client(api_key=api_key)

    from_date = start_date or (
        datetime.datetime.strptime(end_date, "%Y-%m-%d")
        - datetime.timedelta(days=365)
    ).strftime("%Y-%m-%d")

    insider_data = client.stock_insider_transactions(
        ticker,
        from_date,
        end_date,
    )

    if not insider_data or "data" not in insider_data:
        return []

    return [
        _convert_finnhub_insider_trade(ticker, trade)
        for trade in insider_data["data"][:limit]
    ]


def _fetch_fd_insider_trades(
    ticker: str,
    start_date: str | None,
    end_date: str,
    limit: int,
    api_key: str,
) -> list[InsiderTrade]:
    """Fetch insider trades from Financial Datasets API."""
    headers = {"X-API-KEY": api_key}
    all_trades = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={current_end_date}"
        if start_date:
            url += f"&filing_date_gte={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            raise ValueError(
                f"Error fetching data: {ticker} - {response.status_code} - {response.text}",
            )

        data = response.json()
        response_model = InsiderTradeResponse(**data)
        insider_trades = response_model.insider_trades

        if not insider_trades:
            break

        all_trades.extend(insider_trades)

        if not start_date or len(insider_trades) < limit:
            break

        current_end_date = min(
            trade.filing_date for trade in insider_trades
        ).split("T")[0]

        if current_end_date <= start_date:
            break

    return all_trades


def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
) -> list[InsiderTrade]:
    """Fetch insider trades from cache or API."""
    config = get_config()
    data_source = config.source
    api_key = config.api_key

    cache_key = (
        f"{ticker}_{start_date or 'none'}_{end_date}_{limit}_{data_source}"
    )

    if cached_data := _cache.get_insider_trades(cache_key):
        return [InsiderTrade(**trade) for trade in cached_data]

    if data_source == "finnhub":
        all_trades = _fetch_finnhub_insider_trades(
            ticker,
            start_date,
            end_date,
            limit,
            api_key,
        )
    else:
        all_trades = _fetch_fd_insider_trades(
            ticker,
            start_date,
            end_date,
            limit,
            api_key,
        )

    if not all_trades:
        return []

    _cache.set_insider_trades(
        cache_key,
        [trade.model_dump() for trade in all_trades],
    )
    return all_trades


def _fetch_finnhub_company_news(
    ticker: str,
    start_date: str | None,
    end_date: str,
    limit: int,
    api_key: str,
) -> list[CompanyNews]:
    """Fetch company news from Finnhub API."""
    client = finnhub.Client(api_key=api_key)

    from_date = start_date or (
        datetime.datetime.strptime(end_date, "%Y-%m-%d")
        - datetime.timedelta(days=30)
    ).strftime("%Y-%m-%d")

    news_data = client.company_news(ticker, _from=from_date, to=end_date)

    if not news_data:
        return []

    all_news = []
    for news_item in news_data[:limit]:
        company_news = CompanyNews(
            ticker=ticker,
            title=news_item.get("headline", ""),
            related=news_item.get("related", ""),
            source=news_item.get("source", ""),
            date=(
                datetime.datetime.fromtimestamp(
                    news_item.get("datetime", 0),
                    datetime.timezone.utc,
                ).strftime("%Y-%m-%d")
                if news_item.get("datetime")
                else None
            ),
            url=news_item.get("url", ""),
            summary=news_item.get("summary", ""),
            category=news_item.get("category", ""),
        )
        all_news.append(company_news)
    return all_news


def _fetch_fd_company_news(
    ticker: str,
    start_date: str | None,
    end_date: str,
    limit: int,
    api_key: str,
) -> list[CompanyNews]:
    """Fetch company news from Financial Datasets API."""
    headers = {"X-API-KEY": api_key}
    all_news = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/news/?ticker={ticker}&end_date={current_end_date}"
        if start_date:
            url += f"&start_date={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            raise ValueError(
                f"Error fetching data: {ticker} - {response.status_code} - {response.text}",
            )

        data = response.json()
        response_model = CompanyNewsResponse(**data)
        company_news = response_model.news

        if not company_news:
            break

        all_news.extend(company_news)

        if not start_date or len(company_news) < limit:
            break

        current_end_date = min(
            news.date for news in company_news if news.date is not None
        ).split("T")[0]

        if current_end_date <= start_date:
            break

    return all_news


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
) -> list[CompanyNews]:
    """Fetch company news from cache or API."""
    config = get_config()
    data_source = config.source
    api_key = config.api_key

    cache_key = (
        f"{ticker}_{start_date or 'none'}_{end_date}_{limit}_{data_source}"
    )

    if cached_data := _cache.get_company_news(cache_key):
        return [CompanyNews(**news) for news in cached_data]

    if data_source == "finnhub":
        all_news = _fetch_finnhub_company_news(
            ticker,
            start_date,
            end_date,
            limit,
            api_key,
        )
    else:
        all_news = _fetch_fd_company_news(
            ticker,
            start_date,
            end_date,
            limit,
            api_key,
        )

    if not all_news:
        return []

    _cache.set_company_news(
        cache_key,
        [news.model_dump() for news in all_news],
    )
    return all_news


def _convert_finnhub_insider_trade(ticker: str, trade: dict) -> InsiderTrade:
    """Convert Finnhub insider trade format to InsiderTrade model."""
    shares_after = trade.get("share", 0)
    change = trade.get("change", 0)

    return InsiderTrade(
        ticker=ticker,
        issuer=None,
        name=trade.get("name", ""),
        title=None,
        is_board_director=None,
        transaction_date=trade.get("transactionDate", ""),
        transaction_shares=abs(change),
        transaction_price_per_share=trade.get("transactionPrice", 0.0),
        transaction_value=abs(change) * trade.get("transactionPrice", 0.0),
        shares_owned_before_transaction=(
            shares_after - change if shares_after and change else None
        ),
        shares_owned_after_transaction=float(shares_after)
        if shares_after
        else None,
        security_title=None,
        filing_date=trade.get("filingDate", ""),
    )


def get_market_cap(ticker: str, end_date: str) -> float | None:
    """Fetch market cap from the API. Finnhub values are converted from millions."""
    config = get_config()
    data_source = config.source
    api_key = config.api_key

    # For today's date, use company facts API
    if end_date == datetime.datetime.now().strftime("%Y-%m-%d"):
        headers = {"X-API-KEY": api_key}
        url = (
            f"https://api.financialdatasets.ai/company/facts/?ticker={ticker}"
        )
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            return None

        data = response.json()
        response_model = CompanyFactsResponse(**data)
        return response_model.company_facts.market_cap

    financial_metrics = get_financial_metrics(ticker, end_date)
    if not financial_metrics:
        return None

    market_cap = financial_metrics[0].market_cap
    if not market_cap:
        return None

    # Finnhub returns market cap in millions
    if data_source == "finnhub":
        market_cap = market_cap * 1_000_000

    return market_cap


def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """Convert prices to a DataFrame."""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df
