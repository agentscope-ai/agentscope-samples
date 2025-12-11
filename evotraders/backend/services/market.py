# -*- coding: utf-8 -*-
"""
Market Data Service
Supports live, mock, and backtest modes
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

logger = logging.getLogger(__name__)

# NYSE timezone and calendar
NYSE_TZ = ZoneInfo("America/New_York")
NYSE_CALENDAR = mcal.get_calendar("NYSE")


class MarketStatus:
    """Market status enum-like class"""

    OPEN = "open"
    CLOSED = "closed"
    PREMARKET = "premarket"
    AFTERHOURS = "afterhours"


class MarketService:
    """Market data service for price management"""

    def __init__(
        self,
        tickers: List[str],
        poll_interval: int = 10,
        mock_mode: bool = False,
        backtest_mode: bool = False,
        api_key: Optional[str] = None,
        backtest_start_date: Optional[str] = None,
        backtest_end_date: Optional[str] = None,
    ):
        self.tickers = tickers
        self.poll_interval = poll_interval
        self.mock_mode = mock_mode
        self.backtest_mode = backtest_mode
        self.api_key = api_key
        self.backtest_start_date = backtest_start_date
        self.backtest_end_date = backtest_end_date

        self.cache: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._broadcast_func: Optional[Callable] = None
        self._price_manager: Optional[Any] = None
        self._current_date: Optional[str] = None

        # Market status tracking
        self._last_market_status: Optional[str] = None

        # Session tracking for live returns
        self._session_start_values: Optional[Dict[str, float]] = None
        self._session_start_timestamp: Optional[int] = None

    @property
    def mode_name(self) -> str:
        if self.backtest_mode:
            return "BACKTEST"
        elif self.mock_mode:
            return "MOCK"
        return "LIVE"

    async def start(self, broadcast_func: Callable):
        """Start market data service"""
        if self.running:
            return

        self.running = True
        self._loop = asyncio.get_running_loop()
        self._broadcast_func = broadcast_func

        if self.backtest_mode:
            self._start_backtest_mode()
        elif self.mock_mode:
            self._start_mock_mode()
        else:
            self._start_real_mode()

        logger.info(
            f"Market service started: {self.mode_name}, tickers={self.tickers}",  # noqa: E501
        )

    def _make_price_callback(self) -> Callable:
        """Create thread-safe price callback"""

        def callback(price_data: Dict[str, Any]):
            symbol = price_data["symbol"]
            self.cache[symbol] = price_data

            loop = self._loop
            if loop and loop.is_running() and self._broadcast_func:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_price_update(price_data),
                    loop,
                )

        return callback

    def _start_mock_mode(self):
        from backend.data.mock_price_manager import MockPriceManager

        self._price_manager = MockPriceManager(
            poll_interval=self.poll_interval,
            volatility=0.5,
        )
        self._price_manager.add_price_callback(self._make_price_callback())
        self._price_manager.subscribe(
            self.tickers,
            base_prices={t: 100.0 for t in self.tickers},
        )
        self._price_manager.start()

    def _start_real_mode(self):
        from backend.data.polling_price_manager import PollingPriceManager

        if not self.api_key:
            raise ValueError("API key required for live mode")
        self._price_manager = PollingPriceManager(
            api_key=self.api_key,
            poll_interval=self.poll_interval,
        )
        self._price_manager.add_price_callback(self._make_price_callback())
        self._price_manager.subscribe(self.tickers)
        self._price_manager.start()

    def _start_backtest_mode(self):
        from backend.data.historical_price_manager import (
            HistoricalPriceManager,
        )

        self._price_manager = HistoricalPriceManager()
        self._price_manager.add_price_callback(self._make_price_callback())
        self._price_manager.subscribe(self.tickers)

        if self.backtest_start_date and self.backtest_end_date:
            self._price_manager.preload_data(
                self.backtest_start_date,
                self.backtest_end_date,
            )

        self._price_manager.start()

    async def _broadcast_price_update(self, price_data: Dict[str, Any]):
        """Broadcast price update to frontend"""
        if not self._broadcast_func:
            return

        symbol = price_data["symbol"]
        price = price_data["price"]
        open_price = price_data.get("open", price)
        ret = (
            ((price - open_price) / open_price) * 100 if open_price > 0 else 0
        )

        await self._broadcast_func(
            {
                "type": "price_update",
                "symbol": symbol,
                "price": price,
                "open": open_price,
                "ret": ret,
                "timestamp": price_data.get("timestamp"),
                "realtime_prices": {
                    t: self._get_cached_price(t) for t in self.tickers
                },
            },
        )

    def _get_cached_price(self, ticker: str) -> Dict[str, Any]:
        """Get cached price data for a ticker"""
        if ticker in self.cache:
            return self.cache[ticker]
        # Return from price manager if not in cache
        if self._price_manager:
            price = self._price_manager.get_latest_price(ticker)
            if price:
                return {"price": price, "symbol": ticker}
        return {"price": 0, "symbol": ticker}

    def stop(self):
        """Stop market service"""
        if not self.running:
            return
        self.running = False
        if self._price_manager:
            self._price_manager.stop()
            self._price_manager = None
        self._loop = None
        self._broadcast_func = None

    # Backtest methods
    def set_backtest_date(self, date: str):
        """Set current backtest date"""
        if not self.backtest_mode or not self._price_manager:
            return
        self._current_date = date
        self._price_manager.set_date(date)
        logger.info(f"Backtest date: {date}")

    async def emit_market_open(self):
        """Emit market open prices"""
        if self.backtest_mode and self._price_manager:
            self._price_manager.emit_open_prices()
            # Log prices for debugging
            prices = self.get_open_prices()
            logger.info(f"Open prices: {prices}")

    async def emit_market_close(self):
        """Emit market close prices"""
        if self.backtest_mode and self._price_manager:
            self._price_manager.emit_close_prices()
            # Log prices for debugging
            prices = self.get_close_prices()
            logger.info(f"Close prices: {prices}")

    def get_open_prices(self) -> Dict[str, float]:
        """Get open prices for all tickers"""
        prices = {}
        for ticker in self.tickers:
            price = None
            # Try price manager first
            if self.backtest_mode and self._price_manager:
                price = self._price_manager.get_open_price(ticker)
            # Fallback to cache
            if price is None or price <= 0:
                cached = self.cache.get(ticker, {})
                price = cached.get("open") or cached.get("price")
            prices[ticker] = price if price and price > 0 else 0.0
        return prices

    def get_close_prices(self) -> Dict[str, float]:
        """Get close prices for all tickers"""
        prices = {}
        for ticker in self.tickers:
            price = None
            # Try price manager first
            if self.backtest_mode and self._price_manager:
                price = self._price_manager.get_close_price(ticker)
            # Fallback to cache
            if price is None or price <= 0:
                cached = self.cache.get(ticker, {})
                price = cached.get("close") or cached.get("price")
            prices[ticker] = price if price and price > 0 else 0.0
        return prices

    def get_price_for_date(
        self,
        ticker: str,
        date: str,
        price_type: str = "close",
    ) -> Optional[float]:
        """Get price for a specific date"""
        if self.backtest_mode and self._price_manager:
            return self._price_manager.get_price_for_date(
                ticker,
                date,
                price_type,
            )
        return self.get_price_sync(ticker)

    # Common methods
    def get_price_sync(self, ticker: str) -> Optional[float]:
        """Get latest price synchronously"""
        # Try cache first
        data = self.cache.get(ticker)
        if data and data.get("price"):
            return data["price"]
        # Try price manager
        if self._price_manager:
            return self._price_manager.get_latest_price(ticker)
        return None

    def get_all_prices(self) -> Dict[str, float]:
        """Get all latest prices"""
        prices = {}
        for ticker in self.tickers:
            price = self.get_price_sync(ticker)
            prices[ticker] = price if price and price > 0 else 0.0
        return prices

    # Live mode async waiting methods

    def _now_nyse(self) -> datetime:
        """Get current time in NYSE timezone"""
        return datetime.now(NYSE_TZ)

    def _is_trading_day(self, date: datetime) -> bool:
        """Check if date is a NYSE trading day"""
        date_str = date.strftime("%Y-%m-%d")
        valid_days = NYSE_CALENDAR.valid_days(
            start_date=date_str,
            end_date=date_str,
        )
        return len(valid_days) > 0

    def _get_market_hours(self, date: datetime) -> tuple:
        """Get market open and close times for a given date"""
        date_str = date.strftime("%Y-%m-%d")
        schedule = NYSE_CALENDAR.schedule(
            start_date=date_str,
            end_date=date_str,
        )
        if schedule.empty:
            return None, None
        market_open = schedule.iloc[0]["market_open"].to_pydatetime()
        market_close = schedule.iloc[0]["market_close"].to_pydatetime()
        return market_open, market_close

    def _next_trading_day(self, from_date: datetime) -> datetime:
        """Find the next trading day from given date"""
        check_date = from_date + timedelta(days=1)
        for _ in range(10):  # Max 10 days ahead (handles holidays)
            if self._is_trading_day(check_date):
                return check_date
            check_date += timedelta(days=1)
        return check_date

    def _get_trading_date_for_execution(self) -> tuple:
        """
        Determine the trading date for execution.

        Returns:
            (trading_date, market_open_time, market_close_time)

        Logic:
        - If today is a trading day and market has opened: use today
        - If today is a trading day but market hasn't opened: wait for open
        - If today is not a trading day: use next trading day
        """
        now = self._now_nyse()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self._is_trading_day(today):
            market_open, market_close = self._get_market_hours(today)
            return today, market_open, market_close
        else:
            # Weekend or holiday - find next trading day
            next_day = self._next_trading_day(today)
            market_open, market_close = self._get_market_hours(next_day)
            return next_day, market_open, market_close

    async def wait_for_open_prices(self) -> Dict[str, float]:
        """
        Wait for market open and return open prices.

        Behavior:
        - If market is already open today: return current prices immediately
        - If market hasn't opened yet today: wait until open
        - If not a trading day: wait until next trading day opens
        """
        now = self._now_nyse()
        trading_date, market_open, _ = self._get_trading_date_for_execution()

        if market_open is None:
            logger.warning("Could not determine market hours")
            return self.get_all_prices()

        trading_date_str = trading_date.strftime("%Y-%m-%d")

        # Check if we need to wait
        if now < market_open:
            wait_seconds = (market_open - now).total_seconds()
            logger.info(
                f"Waiting {wait_seconds/60:.1f} min for market open "
                f"({trading_date_str} {market_open.strftime('%H:%M')} ET)",
            )
            await asyncio.sleep(wait_seconds)
            # Small delay to ensure prices are available
            await asyncio.sleep(5)
        else:
            logger.info(
                f"Market already open for {trading_date_str}, "
                f"getting current prices",
            )

        # Poll until we have valid prices
        prices = await self._poll_for_prices()
        logger.info(f"Got open prices for {trading_date_str}: {prices}")
        return prices

    async def wait_for_close_prices(self) -> Dict[str, float]:
        """
        Wait for market close and return close prices.

        Behavior:
        - If market is already closed today: return current prices immediately
        - If market hasn't closed yet: wait until close
        """
        now = self._now_nyse()
        trading_date, _, market_close = self._get_trading_date_for_execution()

        if market_close is None:
            logger.warning("Could not determine market hours")
            return self.get_all_prices()

        trading_date_str = trading_date.strftime("%Y-%m-%d")

        # Check if we need to wait
        if now < market_close:
            wait_seconds = (market_close - now).total_seconds()
            logger.info(
                f"Waiting {wait_seconds/60:.1f} min for market close "
                f"({trading_date_str} {market_close.strftime('%H:%M')} ET)",
            )
            await asyncio.sleep(wait_seconds)
            # Small delay to ensure final prices settle
            await asyncio.sleep(10)
        else:
            logger.info(
                f"Market already closed for {trading_date_str}, "
                f"getting close prices",
            )

        # Get final prices
        prices = await self._poll_for_prices()
        logger.info(f"Got close prices for {trading_date_str}: {prices}")
        return prices

    def get_live_trading_date(self) -> str:
        """Get the trading date that will be used for live execution"""
        trading_date, _, _ = self._get_trading_date_for_execution()
        return trading_date.strftime("%Y-%m-%d")

    async def _poll_for_prices(
        self,
        max_retries: int = 12,
    ) -> Dict[str, float]:
        """Poll until all prices are available"""
        for _ in range(max_retries):
            prices = self.get_all_prices()
            if all(p > 0 for p in prices.values()):
                return prices
            logger.debug("Waiting for prices to be available...")
            await asyncio.sleep(5)
        # Return whatever we have
        return self.get_all_prices()

    # ========== Market Status Methods ==========

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status

        Returns:
            Dict with status info:
            - status: 'open' | 'closed' | 'premarket' | 'afterhours'
            - status_text: Human readable status
            - is_trading_day: Whether today is a trading day
            - market_open: Market open time (if trading day)
            - market_close: Market close time (if trading day)
        """
        if self.backtest_mode:
            # In backtest mode, always return open
            return {
                "status": MarketStatus.OPEN,
                "status_text": "Backtest Mode",
                "is_trading_day": True,
            }

        now = self._now_nyse()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        is_trading = self._is_trading_day(today)

        if not is_trading:
            return {
                "status": MarketStatus.CLOSED,
                "status_text": "Market Closed (Non-trading Day)",
                "is_trading_day": False,
            }

        market_open, market_close = self._get_market_hours(today)

        if market_open is None or market_close is None:
            return {
                "status": MarketStatus.CLOSED,
                "status_text": "Market Closed",
                "is_trading_day": is_trading,
            }

        # Determine status based on current time
        if now < market_open:
            return {
                "status": MarketStatus.PREMARKET,
                "status_text": "Pre-Market",
                "is_trading_day": True,
                "market_open": market_open.isoformat(),
                "market_close": market_close.isoformat(),
            }
        elif now > market_close:
            return {
                "status": MarketStatus.CLOSED,
                "status_text": "Market Closed",
                "is_trading_day": True,
                "market_open": market_open.isoformat(),
                "market_close": market_close.isoformat(),
            }
        else:
            return {
                "status": MarketStatus.OPEN,
                "status_text": "Market Open",
                "is_trading_day": True,
                "market_open": market_open.isoformat(),
                "market_close": market_close.isoformat(),
            }

    async def check_and_broadcast_market_status(self):
        """Check market status and broadcast if changed"""
        status = self.get_market_status()
        current_status = status["status"]

        if current_status != self._last_market_status:
            self._last_market_status = current_status
            await self._broadcast_market_status(status)

            # Handle session transitions
            if current_status == MarketStatus.OPEN:
                await self._on_session_start()
            elif (
                current_status == MarketStatus.CLOSED
                and self._session_start_values is not None
            ):
                self._on_session_end()

    async def _broadcast_market_status(self, status: Dict[str, Any]):
        """Broadcast market status update to frontend"""
        if not self._broadcast_func:
            return

        await self._broadcast_func(
            {
                "type": "market_status_update",
                "market_status": status,
                "timestamp": datetime.now(NYSE_TZ).isoformat(),
            },
        )
        logger.info(f"Market status: {status['status_text']}")

    async def _on_session_start(self):
        """Called when market session starts - capture baseline values"""
        # Wait briefly for prices to be available
        await asyncio.sleep(2)

        prices = self.get_all_prices()
        if prices and any(p > 0 for p in prices.values()):
            self._session_start_values = prices.copy()
            self._session_start_timestamp = int(
                datetime.now().timestamp() * 1000,
            )
            logger.info(f"Session started with prices: {prices}")

    def _on_session_end(self):
        """Called when market session ends - clear session data"""
        self._session_start_values = None
        self._session_start_timestamp = None
        logger.info("Session ended, cleared session data")

    def get_session_returns(
        self,
        current_prices: Dict[str, float],
        portfolio_value: Optional[float] = None,
        session_start_portfolio_value: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate session returns (from session start to now)

        Args:
            current_prices: Current prices for tickers
            portfolio_value: Current portfolio value (optional)
            session_start_portfolio_value:

        Returns:
            Dict with return data or None if session not started
        """
        if self._session_start_values is None:
            return None

        timestamp = int(datetime.now().timestamp() * 1000)
        returns = {}

        # Calculate individual ticker returns
        for ticker, start_price in self._session_start_values.items():
            current = current_prices.get(ticker)
            if current and start_price and start_price > 0:
                ret = ((current - start_price) / start_price) * 100
                returns[ticker] = round(ret, 4)

        result = {
            "timestamp": timestamp,
            "ticker_returns": returns,
        }

        # Calculate portfolio return if values provided
        if (
            portfolio_value is not None
            and session_start_portfolio_value is not None
        ):
            if session_start_portfolio_value > 0:
                portfolio_ret = (
                    (portfolio_value - session_start_portfolio_value)
                    / session_start_portfolio_value
                ) * 100
                result["portfolio_return"] = round(portfolio_ret, 4)

        return result

    @property
    def session_start_values(self) -> Optional[Dict[str, float]]:
        """Get session start values for external use"""
        return self._session_start_values

    @property
    def session_start_timestamp(self) -> Optional[int]:
        """Get session start timestamp"""
        return self._session_start_timestamp
