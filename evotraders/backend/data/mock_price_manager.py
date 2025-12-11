# -*- coding: utf-8 -*-
"""
Mock Price Manager - For testing during non-trading hours
Generates virtual real-time price data
"""
import logging
import os
import random
import threading
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockPriceManager:
    """Mock Price Manager - Generates virtual prices for testing"""

    def __init__(self, poll_interval: int = 10, volatility: float = 0.5):
        """
        Args:
            poll_interval: Price update interval in seconds
            volatility: Price volatility percentage
        """
        if poll_interval is None:
            poll_interval = int(os.getenv("MOCK_POLL_INTERVAL", "5"))
        if volatility is None:
            volatility = float(os.getenv("MOCK_VOLATILITY", "0.5"))

        self.poll_interval = poll_interval
        self.volatility = volatility

        self.subscribed_symbols: List[str] = []
        self.base_prices: Dict[str, float] = {}
        self.open_prices: Dict[str, float] = {}
        self.latest_prices: Dict[str, float] = {}
        self.price_callbacks: List[Callable] = []

        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.default_base_prices = {
            "AAPL": 237.50,
            "MSFT": 425.30,
            "GOOGL": 161.50,
            "AMZN": 218.45,
            "NVDA": 950.00,
            "META": 573.22,
            "TSLA": 342.15,
            "AMD": 168.90,
            "NFLX": 688.25,
            "INTC": 42.18,
            "COIN": 285.50,
            "PLTR": 45.80,
            "BABA": 88.30,
            "DIS": 112.50,
            "BKNG": 4850.00,
        }

        logger.info(
            f"MockPriceManager initialized (interval: {self.poll_interval}s, "
            f"volatility: {self.volatility}%)",
        )

    def subscribe(
        self,
        symbols: List[str],
        base_prices: Dict[str, float] = None,
    ):
        """Subscribe to stock symbols"""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                self.subscribed_symbols.append(symbol)

                if base_prices and symbol in base_prices:
                    base_price = base_prices[symbol]
                elif symbol in self.default_base_prices:
                    base_price = self.default_base_prices[symbol]
                else:
                    base_price = random.uniform(50, 500)

                self.base_prices[symbol] = base_price
                self.open_prices[symbol] = base_price
                self.latest_prices[symbol] = base_price

                logger.info(
                    f"Subscribed to mock price: {symbol} (base: ${base_price:.2f})",  # noqa: E501
                )

    def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
                self.base_prices.pop(symbol, None)
                self.open_prices.pop(symbol, None)
                self.latest_prices.pop(symbol, None)
                logger.info(f"Unsubscribed: {symbol}")

    def add_price_callback(self, callback: Callable):
        """Add price update callback"""
        self.price_callbacks.append(callback)

    def _generate_price_update(self, symbol: str) -> float:
        """Generate price update based on random walk"""
        current_price = self.latest_prices.get(
            symbol,
            self.base_prices[symbol],
        )

        change_percent = random.uniform(-self.volatility, self.volatility)
        new_price = current_price * (1 + change_percent / 100)

        # 10% chance of larger movement
        if random.random() < 0.1:
            trend_factor = random.uniform(-2, 2)
            new_price = new_price * (1 + trend_factor / 100)

        # Limit intraday movement to +/-10%
        open_price = self.open_prices[symbol]
        max_price = open_price * 1.10
        min_price = open_price * 0.90
        new_price = max(min_price, min(max_price, new_price))

        return new_price

    def _update_prices(self):
        """Update prices for all subscribed stocks"""
        timestamp = int(time.time() * 1000)

        for symbol in self.subscribed_symbols:
            try:
                new_price = self._generate_price_update(symbol)
                self.latest_prices[symbol] = new_price

                open_price = self.open_prices[symbol]
                ret = ((new_price - open_price) / open_price) * 100

                price_data = {
                    "symbol": symbol,
                    "price": new_price,
                    "timestamp": timestamp,
                    "volume": random.randint(1000000, 10000000),
                    "open": open_price,
                    "high": max(new_price, open_price),
                    "low": min(new_price, open_price),
                    "previous_close": open_price,
                    "ret": ret,
                }

                for callback in self.price_callbacks:
                    try:
                        callback(price_data)
                    except Exception as e:
                        logger.error(
                            f"Mock price callback error ({symbol}): {e}",
                        )

                logger.debug(
                    f"Mock {symbol}: ${new_price:.2f} [ret: {ret:+.2f}%]",
                )

            except Exception as e:
                logger.error(f"Failed to generate mock price ({symbol}): {e}")

    def _polling_loop(self):
        """Main polling loop"""
        logger.info(
            f"Mock price generation started (interval: {self.poll_interval}s)",
        )

        while self.running:
            try:
                start_time = time.time()
                self._update_prices()

                elapsed = time.time() - start_time
                sleep_time = max(0, self.poll_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Mock polling loop error: {e}")
                time.sleep(5)

    def start(self):
        """Start mock price generation"""
        if self.running:
            logger.warning("Mock price manager already running")
            return

        if not self.subscribed_symbols:
            logger.warning("No stocks subscribed")
            return

        self.running = True
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()

        logger.info(
            f"Mock price manager started: {', '.join(self.subscribed_symbols)}",  # noqa: E501
        )

    def stop(self):
        """Stop mock price generation"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Mock price manager stopped")

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
        for symbol in self.subscribed_symbols:
            last_close = self.latest_prices[symbol]
            gap_percent = random.uniform(-1, 1)
            new_open = last_close * (1 + gap_percent / 100)
            self.open_prices[symbol] = new_open
            self.latest_prices[symbol] = new_open
        logger.info("Open prices reset")

    def set_base_price(self, symbol: str, price: float):
        """Manually set base price for testing"""
        if symbol in self.subscribed_symbols:
            self.base_prices[symbol] = price
            self.open_prices[symbol] = price
            self.latest_prices[symbol] = price
            logger.info(f"{symbol} base price set to: ${price:.2f}")
        else:
            logger.warning(f"{symbol} not subscribed")
