# -*- coding: utf-8 -*-
# pylint: disable=W0212
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from agentscope.message import Msg


class TestAnalystAgent:
    def test_init_valid_analyst_type(self):
        from backend.agents.analyst import AnalystAgent

        mock_toolkit = MagicMock()
        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = AnalystAgent(
            analyst_type="technical_analyst",
            toolkit=mock_toolkit,
            model=mock_model,
            formatter=mock_formatter,
        )

        assert agent.analyst_type_key == "technical_analyst"
        assert agent.name == "technical_analyst_analyst"
        assert agent.analyst_persona == "Technical Analyst"

    def test_init_invalid_analyst_type(self):
        from backend.agents.analyst import AnalystAgent

        mock_toolkit = MagicMock()
        mock_model = MagicMock()
        mock_formatter = MagicMock()

        with pytest.raises(ValueError) as excinfo:
            AnalystAgent(
                analyst_type="invalid_type",
                toolkit=mock_toolkit,
                model=mock_model,
                formatter=mock_formatter,
            )

        assert "Unknown analyst type" in str(excinfo.value)

    def test_init_custom_agent_id(self):
        from backend.agents.analyst import AnalystAgent

        mock_toolkit = MagicMock()
        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = AnalystAgent(
            analyst_type="fundamentals_analyst",
            toolkit=mock_toolkit,
            model=mock_model,
            formatter=mock_formatter,
            agent_id="custom_analyst_id",
        )

        assert agent.name == "custom_analyst_id"

    def test_load_system_prompt(self):
        from backend.agents.analyst import AnalystAgent

        mock_toolkit = MagicMock()
        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = AnalystAgent(
            analyst_type="sentiment_analyst",
            toolkit=mock_toolkit,
            model=mock_model,
            formatter=mock_formatter,
        )

        prompt = agent._load_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestPMAgent:
    def test_init_default(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        assert agent.name == "portfolio_manager"
        assert agent.portfolio["cash"] == 100000.0
        assert agent.portfolio["positions"] == {}
        assert agent.portfolio["margin_requirement"] == 0.25

    def test_init_custom_cash(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
            initial_cash=50000.0,
            margin_requirement=0.5,
        )

        assert agent.portfolio["cash"] == 50000.0
        assert agent.portfolio["margin_requirement"] == 0.5

    def test_get_portfolio_state(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
            initial_cash=75000.0,
        )

        state = agent.get_portfolio_state()

        assert state["cash"] == 75000.0
        assert state is not agent.portfolio  # Should be a copy

    def test_load_portfolio_state(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        new_portfolio = {
            "cash": 50000.0,
            "positions": {
                "AAPL": {"long": 100, "short": 0, "long_cost_basis": 150.0},
            },
            "margin_used": 1000.0,
        }

        agent.load_portfolio_state(new_portfolio)

        assert agent.portfolio["cash"] == 50000.0
        assert "AAPL" in agent.portfolio["positions"]

    def test_update_portfolio(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        agent.update_portfolio({"cash": 80000.0})
        assert agent.portfolio["cash"] == 80000.0

    def _get_text_from_tool_response(self, result):
        """Helper to extract text from ToolResponse content"""
        content = result.content[0]
        if hasattr(content, "text"):
            return content.text
        elif isinstance(content, dict):
            return content.get("text", "")
        return str(content)

    def test_make_decision_long(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        result = agent._make_decision(
            ticker="AAPL",
            action="long",
            quantity=100,
            confidence=80,
            reasoning="Strong fundamentals",
        )

        text = self._get_text_from_tool_response(result)
        assert "Decision recorded" in text
        assert agent._decisions["AAPL"]["action"] == "long"
        assert agent._decisions["AAPL"]["quantity"] == 100

    def test_make_decision_hold(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        result = agent._make_decision(
            ticker="GOOGL",
            action="hold",
            quantity=0,
            confidence=50,
            reasoning="Neutral outlook",
        )

        text = self._get_text_from_tool_response(result)
        assert "Decision recorded" in text
        assert agent._decisions["GOOGL"]["action"] == "hold"
        assert agent._decisions["GOOGL"]["quantity"] == 0

    def test_make_decision_invalid_action(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        result = agent._make_decision(
            ticker="AAPL",
            action="invalid",
            quantity=10,
        )

        text = self._get_text_from_tool_response(result)
        assert "Invalid action" in text

    def test_get_decisions(self):
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        agent._make_decision("AAPL", "long", 100)
        agent._make_decision("GOOGL", "short", 50)

        decisions = agent.get_decisions()
        assert len(decisions) == 2
        assert decisions["AAPL"]["action"] == "long"
        assert decisions["GOOGL"]["action"] == "short"


class TestRiskAgent:
    def test_init_default(self):
        from backend.agents.risk_manager import RiskAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = RiskAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        assert agent.name == "risk_manager"

    def test_init_custom_name(self):
        from backend.agents.risk_manager import RiskAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = RiskAgent(
            model=mock_model,
            formatter=mock_formatter,
            name="custom_risk_manager",
        )

        assert agent.name == "custom_risk_manager"

    def test_load_system_prompt(self):
        from backend.agents.risk_manager import RiskAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        agent = RiskAgent(
            model=mock_model,
            formatter=mock_formatter,
        )

        prompt = agent._load_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestStorageService:
    def test_calculate_portfolio_value_cash_only(self):
        from backend.services.storage import StorageService

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(
                dashboard_dir=Path(tmpdir),
                initial_cash=100000.0,
            )

            portfolio = {"cash": 100000.0, "positions": {}, "margin_used": 0.0}
            prices = {}

            value = storage.calculate_portfolio_value(portfolio, prices)
            assert value == 100000.0

    def test_calculate_portfolio_value_with_positions(self):
        from backend.services.storage import StorageService

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(
                dashboard_dir=Path(tmpdir),
                initial_cash=100000.0,
            )

            portfolio = {
                "cash": 50000.0,
                "positions": {
                    "AAPL": {"long": 100, "short": 0},
                    "GOOGL": {"long": 0, "short": 10},
                },
                "margin_used": 5000.0,
            }
            prices = {"AAPL": 150.0, "GOOGL": 100.0}

            value = storage.calculate_portfolio_value(portfolio, prices)
            assert value == 69000.0

    def test_update_dashboard_after_cycle(self):
        from backend.services.storage import StorageService

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(
                dashboard_dir=Path(tmpdir),
                initial_cash=100000.0,
            )

            portfolio = {
                "cash": 90000.0,
                "positions": {"AAPL": {"long": 50, "short": 0}},
                "margin_used": 0.0,
            }
            prices = {"AAPL": 200.0}

            storage.update_dashboard_after_cycle(
                portfolio=portfolio,
                prices=prices,
                date="2024-01-15",
                executed_trades=[
                    {
                        "ticker": "AAPL",
                        "action": "long",
                        "quantity": 50,
                        "price": 200.0,
                    },
                ],
            )

            summary = storage.load_file("summary")
            assert summary is not None
            assert summary["totalAssetValue"] == 100000.0  # 90000 + 50*200

            holdings = storage.load_file("holdings")
            assert holdings is not None
            assert len(holdings) > 0

            trades = storage.load_file("trades")
            assert trades is not None
            assert len(trades) == 1
            assert trades[0]["ticker"] == "AAPL"
            assert trades[0]["qty"] == 50
            assert trades[0]["price"] == 200.0

    def test_generate_summary(self):
        from backend.services.storage import StorageService

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(
                dashboard_dir=Path(tmpdir),
                initial_cash=100000.0,
            )

            state = {
                "portfolio_state": {
                    "cash": 50000.0,
                    "positions": {"AAPL": {"long": 100, "short": 0}},
                    "margin_used": 0.0,
                },
                "equity_history": [{"t": 1000, "v": 100000}],
                "all_trades": [],
            }
            prices = {"AAPL": 500.0}

            storage._generate_summary(state, 100000.0, prices)

            summary = storage.load_file("summary")
            assert summary["totalAssetValue"] == 100000.0
            assert summary["totalReturn"] == 0.0

    def test_generate_holdings(self):
        from backend.services.storage import StorageService

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageService(
                dashboard_dir=Path(tmpdir),
                initial_cash=100000.0,
            )

            state = {
                "portfolio_state": {
                    "cash": 50000.0,
                    "positions": {"AAPL": {"long": 100, "short": 0}},
                    "margin_used": 0.0,
                },
            }
            prices = {"AAPL": 500.0}

            storage._generate_holdings(state, prices)

            holdings = storage.load_file("holdings")
            assert len(holdings) == 2  # AAPL + CASH

            aapl_holding = next(
                (h for h in holdings if h["ticker"] == "AAPL"),
                None,
            )
            assert aapl_holding is not None
            assert aapl_holding["quantity"] == 100
            assert aapl_holding["currentPrice"] == 500.0


class TestTradeExecutor:
    def test_execute_trade_long(self):
        from backend.utils.trade_executor import PortfolioTradeExecutor

        executor = PortfolioTradeExecutor(
            initial_portfolio={
                "cash": 100000.0,
                "positions": {},
                "margin_requirement": 0.25,
                "margin_used": 0.0,
            },
        )

        result = executor.execute_trade(
            ticker="AAPL",
            action="long",
            quantity=10,
            price=150.0,
        )

        assert result["status"] == "success"
        assert executor.portfolio["positions"]["AAPL"]["long"] == 10
        assert executor.portfolio["cash"] == 98500.0  # 100000 - 10*150

    def test_execute_trade_short(self):
        from backend.utils.trade_executor import PortfolioTradeExecutor

        executor = PortfolioTradeExecutor(
            initial_portfolio={
                "cash": 100000.0,
                "positions": {
                    "AAPL": {
                        "long": 50,
                        "short": 0,
                        "long_cost_basis": 100.0,
                        "short_cost_basis": 0.0,
                    },
                },
                "margin_requirement": 0.25,
                "margin_used": 0.0,
            },
        )

        result = executor.execute_trade(
            ticker="AAPL",
            action="short",
            quantity=30,
            price=150.0,
        )

        assert result["status"] == "success"
        assert executor.portfolio["positions"]["AAPL"]["long"] == 20  # 50 - 30

    def test_execute_trade_hold(self):
        from backend.utils.trade_executor import PortfolioTradeExecutor

        executor = PortfolioTradeExecutor()

        result = executor.execute_trade(
            ticker="AAPL",
            action="hold",
            quantity=0,
            price=150.0,
        )

        assert result["status"] == "success"
        assert result["message"] == "No trade needed"


class TestPipelineExecution:
    def test_execute_decisions(self):
        from backend.core.pipeline import TradingPipeline
        from backend.agents.portfolio_manager import PMAgent

        mock_model = MagicMock()
        mock_formatter = MagicMock()

        pm = PMAgent(
            model=mock_model,
            formatter=mock_formatter,
            initial_cash=100000.0,
        )

        pipeline = TradingPipeline(
            analysts=[],
            risk_manager=MagicMock(),
            portfolio_manager=pm,
            max_comm_cycles=0,
        )

        decisions = {
            "AAPL": {"action": "long", "quantity": 10},
            "GOOGL": {"action": "short", "quantity": 5},
        }
        prices = {"AAPL": 150.0, "GOOGL": 100.0}

        result = pipeline._execute_decisions(decisions, prices, "2024-01-15")

        assert len(result["executed_trades"]) == 2
        assert result["executed_trades"][0]["ticker"] == "AAPL"
        assert result["executed_trades"][0]["quantity"] == 10
        assert pm.portfolio["positions"]["AAPL"]["long"] == 10


class TestMsgContentIsString:
    def test_msg_content_string(self):
        msg = Msg(name="test", content="simple string", role="user")
        assert isinstance(msg.content, str)

    def test_msg_content_json_string(self):
        data = {"key": "value", "nested": {"a": 1}}
        msg = Msg(name="test", content=json.dumps(data), role="user")
        assert isinstance(msg.content, str)

        parsed = json.loads(msg.content)
        assert parsed["key"] == "value"

    def test_msg_content_should_not_be_dict(self):
        data = {"key": "value"}
        msg = Msg(name="test", content=json.dumps(data), role="assistant")

        assert not isinstance(msg.content, dict)
        assert isinstance(msg.content, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
