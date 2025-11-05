# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock
import pytest
from agentscope.message import Msg
from agentscope.agent import ReActAgent
from agentscope.tool import Toolkit


@pytest.mark.asyncio
class TestReActAgent:
    """Test suite for the ReAct agent implementation"""

    @pytest.fixture
    def test_agent(self):
        """Fixture to create a test ReAct
        agent with fully mocked dependencies"""

        async def model_response():
            yield Msg(
                name="Friday",
                content="Mocked model response",
                role="assistant",
            )

        mock_model = AsyncMock()
        mock_model.side_effect = model_response

        mock_formatter = AsyncMock()
        mock_formatter.format = AsyncMock(return_value="Mocked prompt")

        mock_memory = AsyncMock()
        mock_memory.get_memory = AsyncMock(return_value=[])

        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=mock_formatter,
            toolkit=Toolkit(),
            memory=mock_memory,
        )

        # pylint: disable=protected-access
        agent._reasoning_hint_msgs = AsyncMock()
        # pylint: disable=protected-access
        agent._reasoning_hint_msgs.get_memory = AsyncMock(return_value=[])

        return agent

    async def test_exit_command(self, test_agent, monkeypatch):
        """Test exit command handling"""

        async def exit_model_response(*_args, **_kwargs):
            yield Msg(
                name="Friday",
                content="exit",
                role="assistant",
            )

        test_agent.model.side_effect = exit_model_response

        monkeypatch.setattr("builtins.input", lambda _: "exit")

        msg = Msg(name="User", content="exit", role="user")
        response = await test_agent(msg)

        assert response.content == "exit"

    async def test_conversation_flow(self, monkeypatch):
        """Test full conversation flow"""

        async def model_response(*_args, **_kwargs):
            yield Msg(
                name="Friday",
                content="Thought: I need to use a tool\n"
                "Action: execute_shell_command\n"
                "Action Input: echo 'Hello World'",
                role="assistant",
            )

        mock_model = AsyncMock()
        mock_model.side_effect = model_response

        mock_formatter = AsyncMock()
        mock_formatter.format = AsyncMock(return_value="Mocked prompt")

        mock_memory = AsyncMock()
        mock_memory.get_memory = AsyncMock(return_value=[])

        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=mock_formatter,
            toolkit=Toolkit(),
            memory=mock_memory,
        )

        monkeypatch.setattr("builtins.input", lambda _: "Test command")

        msg = Msg(name="User", content="Test command", role="user")
        response = await agent(msg)
        assert "Thought:" in response.content
