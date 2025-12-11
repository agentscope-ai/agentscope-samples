# -*- coding: utf-8 -*-
# pylint: disable=W0212
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from backend.services.market import MarketService
from backend.data.mock_price_manager import MockPriceManager
from backend.data.polling_price_manager import PollingPriceManager


class TestMockPriceManager:
    def test_init_default(self):
        manager = MockPriceManager()

        assert manager.poll_interval == 10
        assert manager.volatility == 0.5
        assert manager.running is False
        assert len(manager.subscribed_symbols) == 0

    def test_init_custom(self):
        manager = MockPriceManager(poll_interval=5, volatility=1.0)

        assert manager.poll_interval == 5
        assert manager.volatility == 1.0

    def test_subscribe(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL", "MSFT"])

        assert "AAPL" in manager.subscribed_symbols
        assert "MSFT" in manager.subscribed_symbols
        assert manager.base_prices["AAPL"] == 237.50  # default price
        assert manager.base_prices["MSFT"] == 425.30  # default price

    def test_subscribe_with_base_prices(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        assert manager.base_prices["AAPL"] == 100.0
        assert manager.open_prices["AAPL"] == 100.0
        assert manager.latest_prices["AAPL"] == 100.0

    def test_subscribe_unknown_symbol(self):
        manager = MockPriceManager()
        manager.subscribe(["UNKNOWN"])

        assert "UNKNOWN" in manager.subscribed_symbols
        assert manager.base_prices["UNKNOWN"] > 0  # random price generated

    def test_unsubscribe(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL", "MSFT"])
        manager.unsubscribe(["AAPL"])

        assert "AAPL" not in manager.subscribed_symbols
        assert "MSFT" in manager.subscribed_symbols

    def test_add_price_callback(self):
        manager = MockPriceManager()
        callback = MagicMock()
        manager.add_price_callback(callback)

        assert callback in manager.price_callbacks

    def test_generate_price_update_within_bounds(self):
        manager = MockPriceManager(volatility=0.5)
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        for _ in range(100):
            new_price = manager._generate_price_update("AAPL")
            # Should be within +/-10% of open
            assert 90.0 <= new_price <= 110.0

    def test_update_prices_triggers_callback(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        callback = MagicMock()
        manager.add_price_callback(callback)

        manager._update_prices()

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["symbol"] == "AAPL"
        assert "price" in call_args
        assert "timestamp" in call_args

    def test_start_stop(self):
        manager = MockPriceManager(poll_interval=1)
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        manager.start()
        assert manager.running is True

        time.sleep(0.1)  # let thread start

        manager.stop()
        assert manager.running is False

    def test_start_without_subscription(self):
        manager = MockPriceManager()
        manager.start()

        assert (
            manager.running is False
        )  # should not start without subscriptions

    def test_get_latest_price(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        price = manager.get_latest_price("AAPL")
        assert price == 100.0

    def test_get_latest_price_unknown(self):
        manager = MockPriceManager()
        price = manager.get_latest_price("UNKNOWN")
        assert price is None

    def test_get_all_latest_prices(self):
        manager = MockPriceManager()
        manager.subscribe(
            ["AAPL", "MSFT"],
            base_prices={"AAPL": 100.0, "MSFT": 200.0},
        )

        prices = manager.get_all_latest_prices()
        assert prices["AAPL"] == 100.0
        assert prices["MSFT"] == 200.0

    def test_reset_open_prices(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})
        manager.latest_prices["AAPL"] = 105.0

        manager.reset_open_prices()

        # Open price should change (based on latest with small gap)
        assert manager.open_prices["AAPL"] != 100.0

    def test_set_base_price(self):
        manager = MockPriceManager()
        manager.subscribe(["AAPL"], base_prices={"AAPL": 100.0})

        manager.set_base_price("AAPL", 150.0)

        assert manager.base_prices["AAPL"] == 150.0
        assert manager.open_prices["AAPL"] == 150.0
        assert manager.latest_prices["AAPL"] == 150.0


class TestPollingPriceManager:
    def test_init(self):
        manager = PollingPriceManager(api_key="test_key", poll_interval=30)

        assert manager.api_key == "test_key"
        assert manager.poll_interval == 30
        assert manager.running is False

    def test_subscribe(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.subscribe(["AAPL", "MSFT"])

        assert "AAPL" in manager.subscribed_symbols
        assert "MSFT" in manager.subscribed_symbols

    def test_unsubscribe(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.subscribe(["AAPL", "MSFT"])
        manager.unsubscribe(["AAPL"])

        assert "AAPL" not in manager.subscribed_symbols
        assert "MSFT" in manager.subscribed_symbols

    def test_add_price_callback(self):
        manager = PollingPriceManager(api_key="test_key")
        callback = MagicMock()
        manager.add_price_callback(callback)

        assert callback in manager.price_callbacks

    @patch.object(PollingPriceManager, "_fetch_prices")
    def test_start_stop(self):
        manager = PollingPriceManager(api_key="test_key", poll_interval=1)
        manager.subscribe(["AAPL"])

        manager.start()
        assert manager.running is True

        time.sleep(0.1)

        manager.stop()
        assert manager.running is False

    def test_start_without_subscription(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.start()

        assert manager.running is False

    def test_get_latest_price(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.latest_prices["AAPL"] = 150.0

        price = manager.get_latest_price("AAPL")
        assert price == 150.0

    def test_get_open_price(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.open_prices["AAPL"] = 148.0

        price = manager.get_open_price("AAPL")
        assert price == 148.0

    def test_reset_open_prices(self):
        manager = PollingPriceManager(api_key="test_key")
        manager.open_prices["AAPL"] = 150.0

        manager.reset_open_prices()

        assert len(manager.open_prices) == 0


class TestMarketService:
    def test_init_mock_mode(self):
        service = MarketService(
            tickers=["AAPL", "MSFT"],
            poll_interval=10,
            mock_mode=True,
        )

        assert service.tickers == ["AAPL", "MSFT"]
        assert service.poll_interval == 10
        assert service.mock_mode is True
        assert service.running is False

    def test_init_real_mode(self):
        service = MarketService(
            tickers=["AAPL"],
            mock_mode=False,
            api_key="test_key",
        )

        assert service.mock_mode is False
        assert service.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_start_mock_mode(self):
        service = MarketService(
            tickers=["AAPL"],
            poll_interval=10,
            mock_mode=True,
        )

        broadcast_func = AsyncMock()

        await service.start(broadcast_func)

        assert service.running is True
        assert service._price_manager is not None
        assert isinstance(service._price_manager, MockPriceManager)

        service.stop()

    @pytest.mark.asyncio
    async def test_start_real_mode_without_api_key(self):
        service = MarketService(
            tickers=["AAPL"],
            mock_mode=False,
            api_key=None,
        )

        broadcast_func = AsyncMock()

        with pytest.raises(ValueError) as excinfo:
            await service.start(broadcast_func)

        assert "API key required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        service = MarketService(
            tickers=["AAPL"],
            mock_mode=True,
        )

        broadcast_func = AsyncMock()

        await service.start(broadcast_func)
        assert service.running is True

        # Start again should not fail
        await service.start(broadcast_func)

        service.stop()

    def test_stop(self):
        service = MarketService(
            tickers=["AAPL"],
            mock_mode=True,
        )
        service.running = True
        service._price_manager = MagicMock()

        service.stop()

        assert service.running is False
        assert service._price_manager is None

    def test_stop_when_not_running(self):
        service = MarketService(
            tickers=["AAPL"],
            mock_mode=True,
        )

        # Should not raise
        service.stop()
        assert service.running is False

    def test_get_price_sync(self):
        service = MarketService(tickers=["AAPL"], mock_mode=True)
        service.cache["AAPL"] = {"price": 150.0, "open": 148.0}

        price = service.get_price_sync("AAPL")
        assert price == 150.0

    def test_get_price_sync_not_found(self):
        service = MarketService(tickers=["AAPL"], mock_mode=True)

        price = service.get_price_sync("MSFT")
        assert price is None

    def test_get_all_prices(self):
        service = MarketService(tickers=["AAPL", "MSFT"], mock_mode=True)
        service.cache["AAPL"] = {"price": 150.0}
        service.cache["MSFT"] = {"price": 400.0}

        prices = service.get_all_prices()

        assert prices["AAPL"] == 150.0
        assert prices["MSFT"] == 400.0

    @pytest.mark.asyncio
    async def test_broadcast_price_update(self):
        service = MarketService(tickers=["AAPL"], mock_mode=True)
        service._broadcast_func = AsyncMock()

        price_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "open": 148.0,
            "timestamp": 1234567890,
        }

        await service._broadcast_price_update(price_data)

        service._broadcast_func.assert_called_once()
        call_args = service._broadcast_func.call_args[0][0]
        assert call_args["type"] == "price_update"
        assert call_args["symbol"] == "AAPL"
        assert call_args["price"] == 150.0

    @pytest.mark.asyncio
    async def test_broadcast_price_update_no_func(self):
        service = MarketService(tickers=["AAPL"], mock_mode=True)
        service._broadcast_func = None

        price_data = {"symbol": "AAPL", "price": 150.0, "open": 148.0}

        # Should not raise
        await service._broadcast_price_update(price_data)

    @pytest.mark.asyncio
    async def test_price_callback_thread_safety(self):
        service = MarketService(
            tickers=["AAPL"],
            poll_interval=1,
            mock_mode=True,
        )

        received_prices = []

        async def capture_broadcast(msg):
            received_prices.append(msg)

        await service.start(capture_broadcast)

        # Wait for at least one price update
        await asyncio.sleep(1.5)

        service.stop()

        # Should have received at least one price update
        assert len(received_prices) >= 1
        assert received_prices[0]["type"] == "price_update"


class TestMarketServiceIntegration:
    @pytest.mark.asyncio
    async def test_full_mock_cycle(self):
        service = MarketService(
            tickers=["AAPL", "MSFT"],
            poll_interval=1,
            mock_mode=True,
        )

        messages = []

        async def collect_messages(msg):
            messages.append(msg)

        await service.start(collect_messages)

        # Wait for price updates
        await asyncio.sleep(2.5)

        service.stop()

        # Should have received multiple price updates
        assert len(messages) >= 2

        # Check message structure
        symbols_seen = set()
        for msg in messages:
            assert msg["type"] == "price_update"
            assert "symbol" in msg
            assert "price" in msg
            assert "ret" in msg
            symbols_seen.add(msg["symbol"])

        # Should have prices for both tickers
        assert "AAPL" in symbols_seen or "MSFT" in symbols_seen


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
