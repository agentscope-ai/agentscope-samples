# -*- coding: utf-8 -*-
"""
Historical Price Manager for backtest mode
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Path to local CSV data directory
_DATA_DIR = Path(__file__).parent / "ret_data"


class HistoricalPriceManager:
    """Provides historical prices for backtest mode"""

    def __init__(self):
        self.subscribed_symbols = []
        self.price_callbacks = []
        self._price_cache = {}
        self._current_date = None
        self.latest_prices = {}
        self.open_prices = {}
        self.close_prices = {}
        self.running = False

    def subscribe(
        self,
        symbols: List[str],
    ):
        """Subscribe to symbols"""
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                self.subscribed_symbols.append(symbol)

    def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
                self._price_cache.pop(symbol, None)

    def add_price_callback(self, callback: Callable):
        """Add price update callback"""
        self.price_callbacks.append(callback)

    def _load_from_csv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load price data from local CSV file."""
        csv_path = _DATA_DIR / f"{symbol}.csv"
        if not csv_path.exists():
            return None

        try:
            df = pd.read_csv(csv_path)
            if df.empty or "time" not in df.columns:
                return None

            df["Date"] = pd.to_datetime(df["time"])
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception as e:
            logger.warning(f"Failed to load CSV for {symbol}: {e}")
            return None

    def preload_data(self, start_date: str, end_date: str):
        """Preload historical data from local CSV files."""
        logger.info(f"Preloading data: {start_date} to {end_date}")

        for symbol in self.subscribed_symbols:
            if symbol in self._price_cache:
                continue

            # Load from local CSV file directly
            df = self._load_from_csv(symbol)
            if df is not None and not df.empty:
                self._price_cache[symbol] = df
                logger.info(f"Loaded {symbol} from CSV: {len(df)} records")
            else:
                logger.warning(f"No CSV data for {symbol}")

    def set_date(self, date: str):
        """Set current trading date and update prices"""
        self._current_date = date
        date_dt = pd.Timestamp(date)

        for symbol in self.subscribed_symbols:
            df = self._price_cache.get(symbol)
            if df is None or df.empty:
                # Keep previous prices if no data available
                logger.warning(f"No cached data for {symbol} on {date}")
                continue

            # Find exact date or closest earlier date
            if date_dt in df.index:
                row = df.loc[date_dt]
            else:
                valid_dates = df.index[df.index <= date_dt]
                if len(valid_dates) == 0:
                    logger.warning(f"No data for {symbol} on or before {date}")
                    continue
                row = df.loc[valid_dates[-1]]

            open_price = float(row["open"])
            close_price = float(row["close"])

            self.open_prices[symbol] = open_price
            self.close_prices[symbol] = close_price
            self.latest_prices[symbol] = open_price

            logger.debug(
                f"{symbol} @ {date}: open={open_price:.2f}, close={close_price:.2f}",  # noqa: E501
            )

    def emit_open_prices(self):
        """Emit open prices to callbacks"""
        if not self._current_date:
            return

        timestamp = int(
            datetime.strptime(self._current_date, "%Y-%m-%d").timestamp()
            * 1000,
        )

        for symbol in self.subscribed_symbols:
            price = self.open_prices.get(symbol)
            if price is None or price <= 0:
                logger.warning(f"Invalid open price for {symbol}: {price}")
                continue

            self.latest_prices[symbol] = price
            self._emit_price(symbol, price, timestamp)

    def emit_close_prices(self):
        """Emit close prices to callbacks"""
        if not self._current_date:
            return

        timestamp = int(
            datetime.strptime(self._current_date, "%Y-%m-%d").timestamp()
            * 1000,
        )
        timestamp += 23400000  # Add 6.5 hours

        for symbol in self.subscribed_symbols:
            price = self.close_prices.get(symbol)
            if price is None or price <= 0:
                logger.warning(f"Invalid close price for {symbol}: {price}")
                continue

            self.latest_prices[symbol] = price
            self._emit_price(symbol, price, timestamp)

    def _emit_price(self, symbol: str, price: float, timestamp: int):
        """Emit single price to callbacks"""
        open_price = self.open_prices.get(symbol, price)
        close_price = self.close_prices.get(symbol, price)
        ret = (
            ((price - open_price) / open_price) * 100 if open_price > 0 else 0
        )

        price_data = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp,
            "open": open_price,
            "close": close_price,
            "high": max(open_price, close_price),
            "low": min(open_price, close_price),
            "ret": ret,
        }

        for callback in self.price_callbacks:
            try:
                callback(price_data)
            except Exception as e:
                logger.error(f"Callback error for {symbol}: {e}")

    def get_price_for_date(
        self,
        symbol: str,
        date: str,
        price_type: str = "close",
    ) -> Optional[float]:
        """Get price for a specific date"""
        df = self._price_cache.get(symbol)
        if df is None or df.empty:
            return self.latest_prices.get(symbol)

        date_dt = pd.Timestamp(date)
        if date_dt in df.index:
            return float(df.loc[date_dt, price_type])

        valid_dates = df.index[df.index <= date_dt]
        if len(valid_dates) == 0:
            return self.latest_prices.get(symbol)
        return float(df.loc[valid_dates[-1], price_type])

    def start(self):
        """Start manager"""
        self.running = True

    def stop(self):
        """Stop manager"""
        self.running = False

    def get_latest_price(self, symbol: str) -> Optional[float]:
        return self.latest_prices.get(symbol)

    def get_all_latest_prices(self) -> Dict[str, float]:
        return self.latest_prices.copy()

    def get_open_price(self, symbol: str) -> Optional[float]:
        # Return open price, fallback to latest if not set
        price = self.open_prices.get(symbol)
        if price is None or price <= 0:
            return self.latest_prices.get(symbol)
        return price

    def get_close_price(self, symbol: str) -> Optional[float]:
        # Return close price, fallback to latest if not set
        price = self.close_prices.get(symbol)
        if price is None or price <= 0:
            return self.latest_prices.get(symbol)
        return price

    def reset_open_prices(self):
        # Don't clear prices - keep them for continuity
        pass
