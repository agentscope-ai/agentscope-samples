# -*- coding: utf-8 -*-
"""
Polling-based Price Manager - Uses Finnhub REST API
Supports real-time price fetching via polling
"""
import logging
import threading
import time
from typing import Callable, Dict, List, Optional

import finnhub

logger = logging.getLogger(__name__)


class PollingPriceManager:
    """Polling-based price manager using Finnhub Quote API"""

    def __init__(self, api_key: str, poll_interval: int = 30):
        """
        Args:
            api_key: Finnhub API Key
            poll_interval: Polling interval in seconds (default 30s)
        """
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.finnhub_client = finnhub.Client(api_key=api_key)

        self.subscribed_symbols: List[str] = []
        self.latest_prices: Dict[str, float] = {}
        self.open_prices: Dict[str, float] = {}
        self.price_callbacks: List[Callable] = []

        self.running = False
        self._thread: Optional[threading.Thread] = None

        logger.info(
            f"PollingPriceManager initialized (interval: {poll_interval}s)",
        )

    def subscribe(self, symbols: List[str]):
        """Subscribe to stock symbols"""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                self.subscribed_symbols.append(symbol)
                logger.info(f"Subscribed to: {symbol}")

    def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
                logger.info(f"Unsubscribed: {symbol}")

    def add_price_callback(self, callback: Callable):
        """Add price update callback"""
        self.price_callbacks.append(callback)

    def _fetch_prices(self):
        """Fetch latest prices for all subscribed stocks"""
        for symbol in self.subscribed_symbols:
            try:
                quote_data = self.finnhub_client.quote(symbol)

                current_price = quote_data.get("c")
                open_price = quote_data.get("o")
                timestamp = quote_data.get("t", int(time.time()))

                if not current_price or current_price <= 0:
                    logger.warning(f"{symbol}: Invalid price data")
                    continue

                # Store open price on first fetch
                if (
                    symbol not in self.open_prices
                    and open_price
                    and open_price > 0
                ):
                    self.open_prices[symbol] = open_price
                    logger.info(f"{symbol} open price: ${open_price:.2f}")

                stored_open = self.open_prices.get(symbol, open_price)
                ret = (
                    ((current_price - stored_open) / stored_open) * 100
                    if stored_open > 0
                    else 0
                )

                self.latest_prices[symbol] = current_price

                price_data = {
                    "symbol": symbol,
                    "price": current_price,
                    "timestamp": timestamp * 1000,
                    "open": stored_open,
                    "high": quote_data.get("h"),
                    "low": quote_data.get("l"),
                    "previous_close": quote_data.get("pc"),
                    "ret": ret,
                    "change": quote_data.get("d"),
                    "change_percent": quote_data.get("dp"),
                }

                for callback in self.price_callbacks:
                    try:
                        callback(price_data)
                    except Exception as e:
                        logger.error(f"Price callback error ({symbol}): {e}")

                logger.debug(
                    f"{symbol}: ${current_price:.2f} [ret: {ret:+.2f}%]",
                )

            except Exception as e:
                logger.error(f"Failed to fetch {symbol} price: {e}")

    def _polling_loop(self):
        """Main polling loop"""
        logger.info(f"Price polling started (interval: {self.poll_interval}s)")

        while self.running:
            try:
                start_time = time.time()
                self._fetch_prices()

                elapsed = time.time() - start_time
                sleep_time = max(0, self.poll_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                time.sleep(5)

    def start(self):
        """Start price polling"""
        if self.running:
            logger.warning("Price polling already running")
            return

        if not self.subscribed_symbols:
            logger.warning("No stocks subscribed")
            return

        self.running = True
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()

        logger.info(
            f"Price polling started: {', '.join(self.subscribed_symbols)}",
        )

    def stop(self):
        """Stop price polling"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Price polling stopped")

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol"""
        return self.latest_prices.get(symbol)

    def get_all_latest_prices(self) -> Dict[str, float]:
        """Get all latest prices"""
        return self.latest_prices.copy()

    def get_open_price(self, symbol: str) -> Optional[float]:
        """Get open price for symbol"""
        return self.open_prices.get(symbol)

    def reset_open_prices(self):
        """Reset open prices for new trading day"""
        self.open_prices.clear()
        logger.info("Open prices reset")
