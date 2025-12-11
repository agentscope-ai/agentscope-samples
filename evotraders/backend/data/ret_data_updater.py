#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic Incremental Historical Data Update Module

Features:
1. Fetch stock historical data from configured API (Finnhub or Financial Datasets)
2. Incrementally update CSV files in ret_data directory
3. Automatically detect last update date, only download new data
4. Calculate returns (ret)
5. Support batch updates for multiple stocks
"""

# flake8: noqa: E501

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import exchange_calendars as xcals
import pandas as pd
import pandas_market_calendars as mcal
from dotenv import load_dotenv

from backend.config.data_config import (
    get_config,
)
from backend.tools.data_tools import get_prices, prices_to_df

# Add project root directory to path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class DataUpdater:
    """Data updater"""

    data_dir: Path

    def __init__(
        self,
        data_dir: str = None,
        start_date: str = "2022-01-01",
    ):
        """
        Initialize data updater

        Args:
            data_dir: Data storage directory, defaults to backend/data/ret_data
            start_date: Historical data start date (YYYY-MM-DD)
        """
        # Get config from centralized source
        config = get_config()
        self.data_source = config.source
        self.api_key = config.api_key

        # Set data directory
        if data_dir is None:
            self.data_dir = BASE_DIR / "backend" / "data" / "ret_data"
        else:
            self.data_dir = Path(data_dir)

        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date

        # Initialize Finnhub client if needed
        if self.data_source == "finnhub":
            import finnhub

            self.client = finnhub.Client(api_key=self.api_key)
            logger.info("Finnhub client initialized")
        else:
            self.client = None
            logger.info("Financial Datasets API configured")

    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """Get US stock market trading date sequence."""
        try:
            if mcal is not None:
                nyse = mcal.get_calendar("NYSE")
                trading_dates = nyse.valid_days(
                    start_date=start_date,
                    end_date=end_date,
                )
                return [date.strftime("%Y-%m-%d") for date in trading_dates]

            elif xcals is not None:
                nyse = xcals.get_calendar("XNYS")
                trading_dates = nyse.sessions_in_range(start_date, end_date)
                return [date.strftime("%Y-%m-%d") for date in trading_dates]

        except Exception as e:
            logger.warning(
                f"Failed to get US trading calendar, using business days: {e}",
            )

        # Fallback to simple business day method
        date_range = pd.date_range(start_date, end_date, freq="B")
        return [date.strftime("%Y-%m-%d") for date in date_range]

    def get_last_date_from_csv(self, ticker: str) -> Optional[datetime]:
        """Get last data date from CSV file."""
        csv_path = self.data_dir / f"{ticker}.csv"

        if not csv_path.exists():
            logger.info(f"{ticker}.csv does not exist, will create new file")
            return None

        try:
            df = pd.read_csv(csv_path)
            if df.empty or "time" not in df.columns:
                return None

            last_date_str = df["time"].iloc[-1]
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            logger.info(f"{ticker} last data date: {last_date_str}")
            return last_date
        except Exception as e:
            logger.warning(f"Failed to read {ticker}.csv: {e}")
            return None

    def fetch_data_from_api(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[pd.DataFrame]:
        """Fetch data from configured API."""
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        logger.info(
            f"Fetching {ticker} data from {self.data_source}: {start_date_str} to {end_date_str}",
        )

        prices = get_prices(
            ticker=ticker,
            start_date=start_date_str,
            end_date=end_date_str,
        )

        if not prices:
            logger.warning(f"{ticker} no data returned from API")
            return None

        # Convert to DataFrame
        df = prices_to_df(prices)
        df = df.reset_index()
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

        # Calculate returns (next day return)
        df["ret"] = df["close"].pct_change().shift(-1)

        # Select needed columns
        df = df[["open", "close", "high", "low", "volume", "time", "ret"]]

        logger.info(f"Successfully fetched {ticker} data: {len(df)} records")
        return df

    def merge_and_save(self, ticker: str, new_data: pd.DataFrame) -> bool:
        """Merge old and new data and save."""
        csv_path = self.data_dir / f"{ticker}.csv"

        try:
            if csv_path.exists():
                old_data = pd.read_csv(csv_path)
                logger.info(f"{ticker} existing data: {len(old_data)} records")

                # Merge and deduplicate
                combined = pd.concat([old_data, new_data], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["time"],
                    keep="last",
                )
                combined = combined.sort_values("time").reset_index(drop=True)

                # Recalculate returns
                combined["ret"] = combined["close"].pct_change().shift(-1)

                logger.info(f"{ticker} merged data: {len(combined)} records")
            else:
                combined = new_data
                logger.info(f"{ticker} new file: {len(combined)} records")

            combined.to_csv(csv_path, index=False)
            logger.info(f"{ticker} data saved to: {csv_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save {ticker} data: {e}")
            return False

    def update_ticker(
        self,
        ticker: str,
        force_full_update: bool = False,
    ) -> bool:
        """Update data for a single stock."""
        logger.info(f"{'='*60}")
        logger.info(f"Starting update for {ticker}")
        logger.info(f"{'='*60}")

        # Determine start date
        if force_full_update:
            start_date = datetime.strptime(self.start_date, "%Y-%m-%d")
            logger.info(f"Force full update, start date: {start_date.date()}")
        else:
            last_date = self.get_last_date_from_csv(ticker)
            if last_date:
                start_date = last_date + timedelta(days=1)
                logger.info(
                    f"Incremental update, start date: {start_date.date()}",
                )
            else:
                start_date = datetime.strptime(self.start_date, "%Y-%m-%d")
                logger.info(f"First update, start date: {start_date.date()}")

        end_date = datetime.now()

        if start_date.date() >= end_date.date():
            logger.info(f"{ticker} data is up to date, no update needed")
            return True

        new_data = self.fetch_data_from_api(ticker, start_date, end_date)

        if new_data is None or new_data.empty:
            days_diff = (end_date - start_date).days
            if days_diff <= 3:
                logger.info(
                    f"{ticker} has no new data (may be weekend/holiday)",
                )
                return True
            else:
                logger.warning(f"{ticker} has no new data")
                return False

        success = self.merge_and_save(ticker, new_data)

        if success:
            logger.info(f"{ticker} update completed")
        else:
            logger.error(f"{ticker} update failed")

        return success

    def update_all_tickers(
        self,
        tickers: List[str],
        force_full_update: bool = False,
    ) -> Dict[str, bool]:
        """Batch update multiple stocks."""
        results = {}

        logger.info(f"{'='*60}")
        logger.info(f"Starting batch update for {len(tickers)} stocks")
        logger.info(f"Stock list: {', '.join(tickers)}")
        logger.info(f"{'='*60}")

        for i, ticker in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] Processing {ticker}")
            results[ticker] = self.update_ticker(ticker, force_full_update)

            # API rate limiting
            if i < len(tickers):
                time.sleep(1)

        # Print summary
        logger.info(f"{'='*60}")
        logger.info("Update Summary")
        logger.info(f"{'='*60}")

        success_count = sum(results.values())
        fail_count = len(results) - success_count

        logger.info(f"Success: {success_count}")
        logger.info(f"Failed: {fail_count}")

        if fail_count > 0:
            failed_tickers = [t for t, s in results.items() if not s]
            logger.warning(f"Failed stocks: {', '.join(failed_tickers)}")

        logger.info(f"{'='*60}\n")

        return results


def main():
    """Command line entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automatically update stock historical data",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Stock ticker list (comma-separated), e.g.: AAPL,MSFT,GOOGL",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data storage directory (default: backend/data/ret_data)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2022-01-01",
        help="Historical data start date (YYYY-MM-DD, default: 2022-01-01)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full update (re-download all data)",
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Validate API key is available
    try:
        config = get_config()
        logger.info(f"Using data source: {config.source}")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Get stock list
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers_env = os.getenv("TICKERS", "")
        if tickers_env:
            tickers = [t.strip().upper() for t in tickers_env.split(",")]
        else:
            logger.error("Stock list not provided")
            logger.error(
                "Please set via --tickers parameter or TICKERS environment variable",
            )
            sys.exit(1)

    # Create updater
    updater = DataUpdater(
        data_dir=args.data_dir,
        start_date=args.start_date,
    )

    # Execute update
    try:
        results = updater.update_all_tickers(
            tickers,
            force_full_update=args.force,
        )
    except Exception:
        # API error (e.g., weekend/holiday with no data)
        sys.exit(1)

    # Return status code
    success_count = sum(results.values())
    if success_count == len(results):
        logger.info("All stocks updated successfully!")
        sys.exit(0)
    elif success_count == 0:
        logger.warning("All stocks have no new data (may be weekend/holiday)")
        sys.exit(0)
    else:
        logger.warning("Some stocks failed to update, but will continue")
        sys.exit(0)


if __name__ == "__main__":
    main()
