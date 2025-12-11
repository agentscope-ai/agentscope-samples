# -*- coding: utf-8 -*-
"""
Scheduler - Market-aware trigger system for trading cycles
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

logger = logging.getLogger(__name__)

# NYSE timezone for US stock trading
NYSE_TZ = ZoneInfo("America/New_York")
NYSE_CALENDAR = mcal.get_calendar("NYSE")


class Scheduler:
    """
    Market-aware scheduler for live trading.
    Uses NYSE timezone and trading calendar.
    """

    def __init__(
        self,
        mode: str = "daily",
        trigger_time: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        config: Optional[dict] = None,
    ):
        self.mode = mode
        self.trigger_time = trigger_time or "09:30"  # NYSE timezone
        self.trigger_now = self.trigger_time == "now"
        self.interval_minutes = interval_minutes or 60
        self.config = config or {}

        self.running = False
        self._task: Optional[asyncio.Task] = None

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

    def _next_trading_day(self, from_date: datetime) -> datetime:
        """Find the next trading day from given date"""
        check_date = from_date
        for _ in range(10):  # Max 10 days ahead (handles holidays)
            if self._is_trading_day(check_date):
                return check_date
            check_date += timedelta(days=1)
        return check_date

    async def start(self, callback: Callable):
        """Start scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True

        if self.mode == "daily":
            self._task = asyncio.create_task(self._run_daily(callback))
        elif self.mode == "intraday":
            self._task = asyncio.create_task(self._run_intraday(callback))
        else:
            raise ValueError(f"Unknown scheduler mode: {self.mode}")

        logger.info(
            f"Scheduler started: mode={self.mode}, timezone=America/New_York",
        )

    async def _run_daily(self, callback: Callable):
        """Run once per trading day at specified time (NYSE timezone)"""
        first_run = True

        while self.running:
            now = self._now_nyse()

            # Handle "now" trigger - run immediately on first iteration
            if self.trigger_now and first_run:
                first_run = False
                current_date = now.strftime("%Y-%m-%d")
                logger.info(f"Triggering immediately for {current_date}")
                await callback(date=current_date)
                # After immediate run, stop (one-shot mode)
                self.running = False
                break

            target_time = datetime.strptime(self.trigger_time, "%H:%M").time()

            # Calculate next trigger datetime
            if now.time() < target_time:
                next_run = now.replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0,
                )
            else:
                next_run = (now + timedelta(days=1)).replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0,
                )

            # Skip to next trading day
            next_run = self._next_trading_day(next_run)
            next_run = next_run.replace(
                hour=target_time.hour,
                minute=target_time.minute,
                second=0,
                microsecond=0,
            )

            wait_seconds = (next_run - now).total_seconds()
            logger.info(
                f"Next trigger: {next_run.strftime('%Y-%m-%d %H:%M %Z')} "
                f"(in {wait_seconds/3600:.1f} hours)",
            )

            await asyncio.sleep(wait_seconds)

            current_date = self._now_nyse().strftime("%Y-%m-%d")
            logger.info(f"Triggering daily cycle for {current_date}")
            await callback(date=current_date)

    async def _run_intraday(self, callback: Callable):
        """Run every N minutes (for future use)"""
        while self.running:
            now = self._now_nyse()
            current_date = now.strftime("%Y-%m-%d")

            if self._is_trading_day(now):
                logger.info(f"Triggering intraday cycle for {current_date}")
                await callback(date=current_date)

            await asyncio.sleep(self.interval_minutes * 60)

    def stop(self):
        """Stop scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Scheduler stopped")


class BacktestScheduler:
    """Backtest Scheduler - Runs through historical trading dates"""

    def __init__(
        self,
        start_date: str,
        end_date: str,
        trading_calendar: Optional[Any] = None,
        delay_between_days: float = 0.1,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.trading_calendar = trading_calendar
        self.delay_between_days = delay_between_days

        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._dates: list = []

    def get_trading_dates(self) -> list:
        """Get list of trading dates in the backtest period"""
        import pandas as pd

        start = pd.to_datetime(self.start_date)
        end = pd.to_datetime(self.end_date)

        if self.trading_calendar:
            calendar = mcal.get_calendar(self.trading_calendar)
            trading_dates = calendar.valid_days(
                start_date=self.start_date,
                end_date=self.end_date,
            )
            dates = [d.strftime("%Y-%m-%d") for d in trading_dates]
        else:
            all_dates = pd.date_range(start=start, end=end, freq="D")
            dates = [
                d.strftime("%Y-%m-%d") for d in all_dates if d.weekday() < 5
            ]

        self._dates = dates
        return dates

    async def start(self, callback: Callable):
        """Start async backtest scheduler"""
        if self.running:
            logger.warning("Backtest scheduler already running")
            return

        self.running = True
        dates = self.get_trading_dates()

        logger.info(
            f"Starting backtest: {self.start_date} to {self.end_date} "
            f"({len(dates)} trading days)",
        )

        self._task = asyncio.create_task(self._run_async(callback, dates))

    async def _run_async(self, callback: Callable, dates: list):
        """Run backtest asynchronously"""
        for i, date in enumerate(dates, 1):
            if not self.running:
                break

            logger.info(f"[{i}/{len(dates)}] Processing {date}")
            await callback(date=date)

            if self.delay_between_days > 0:
                await asyncio.sleep(self.delay_between_days)

        logger.info("Backtest complete")
        self.running = False

    def run(self, callback: Callable, **kwargs):
        """Run backtest synchronously through all trading dates"""
        dates = self.get_trading_dates()
        results = []

        logger.info(
            f"Starting backtest: {self.start_date} to {self.end_date} "
            f"({len(dates)} trading days)",
        )

        for i, date in enumerate(dates, 1):
            logger.info(f"[{i}/{len(dates)}] Processing {date}")
            result = callback(date=date, **kwargs)
            results.append({"date": date, "result": result})

        logger.info("Backtest complete")
        return results

    def stop(self):
        """Stop backtest scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Backtest scheduler stopped")

    def get_total_days(self) -> int:
        """Get total number of trading days"""
        if not self._dates:
            self.get_trading_dates()
        return len(self._dates)
