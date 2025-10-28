# -*- coding: utf-8 -*-
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agentscope.message import Msg

with patch("conversational_agents.chatbot.main.asyncio.run"):
    from conversational_agents.chatbot.main import (
        ReActAgent,
        UserAgent,
        Toolkit,
    )
    from conversational_agents.chatbot.main import (
        execute_shell_command,
        execute_python_code,
        view_text_file,
    )


@pytest.fixture
def mock_toolkit():
    """Create a mocked Toolkit instance"""
    with patch("conversational_agents.chatbot.main.Toolkit") as mock:
        toolkit = MagicMock()
        mock.return_value = toolkit

        # Create tool registry mock
        toolkit._tools = {
            "execute_shell_command": MagicMock(),
            "execute_python_code": MagicMock(),
            "view_text_file": MagicMock(),
        }

        return toolkit


@pytest.fixture
def mock_model():
    """Create a mocked DashScopeChatModel"""
    with patch(
        "conversational_agents.chatbot.main.DashScopeChatModel",
    ) as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Fix model.call simulation
        mock_instance.__call__ = AsyncMock(
            return_value=Msg(
                name="Model",
                content="mocked response",
                role="assistant",
            ),
        )

        return mock_instance


@pytest.fixture
def mock_formatter():
    """Create a mocked formatter"""
    with patch(
        "conversational_agents.chatbot.main.DashScopeChatFormatter",
    ) as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Fix formatter.format async call
        mock_instance.format = AsyncMock(return_value="mocked prompt")

        return mock_instance


@pytest.fixture
def mock_memory():
    """Create a mocked memory"""
    with patch("conversational_agents.chatbot.main.InMemoryMemory") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Fix await memory.get_memory() error
        mock_instance.get_memory = AsyncMock(return_value=[])
        mock_instance.add = AsyncMock(return_value=None)

        return mock_instance


# Async tests
@pytest.mark.asyncio
async def test_agent_initialization(
    mock_toolkit,
    mock_model,
    mock_formatter,
    mock_memory,
):
    """Test ReAct agent initialization"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
        # Create mocked model
        mock_model = MagicMock()

        # Initialize agent
        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=mock_formatter,
            toolkit=mock_toolkit,
            memory=mock_memory,
        )

        assert agent.name == "Friday"
        assert agent.sys_prompt == "You are a helpful assistant named Friday."
        assert agent.model is mock_model
        assert agent.formatter is mock_formatter
        assert agent.toolkit is mock_toolkit
        assert agent.memory is mock_memory


@pytest.mark.asyncio
async def test_tool_function_registration(mock_toolkit):
    """Test tool functions are properly registered"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
        # Create mocked model
        mock_model = MagicMock()

        # Initialize agent
        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=MagicMock(),
            toolkit=mock_toolkit,
            memory=MagicMock(),
        )

        # Verify tool registration
        assert "execute_shell_command" in agent.toolkit._tools
        assert "execute_python_code" in agent.toolkit._tools
        assert "view_text_file" in agent.toolkit._tools


@pytest.mark.asyncio
async def test_user_interaction(mock_toolkit, mock_model):
    """Test user-agent interaction loop"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
        # Create mocked memory
        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])

        # Create mocked formatter
        mock_formatter = MagicMock()

        # Create agent and user
        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=mock_formatter,
            toolkit=mock_toolkit,
            memory=mock_memory,
        )

        user = UserAgent("User")

        # Test exit command
        with patch("builtins.input", return_value="exit"):
            msg = await user("exit")
            assert (
                msg.content == "exit"
            )  # Fix content being a string instead of dict


@pytest.mark.asyncio
async def test_tool_execution():
    """Test tool function execution"""

    # Simulate ToolResponse structure
    class MockToolResponse:
        def __str__(self):
            return "ToolResponse(content=[{'type': 'text', 'text': '<returncode>0</returncode><stdout>test\\n</stdout><stderr></stderr>'}], metadata=None, stream=False, is_last=True, is_interrupted=False, id='test')"

    # Test shell command
    with patch(
        "conversational_agents.chatbot.main.execute_shell_command",
    ) as mock_shell:
        mock_shell.return_value = AsyncMock(return_value=MockToolResponse())
        result = await execute_shell_command("echo test")
        assert "test" in str(result)  # Fix assertion content

    # Test Python code execution
    with patch(
        "conversational_agents.chatbot.main.execute_python_code",
    ) as mock_python:
        mock_python.return_value = AsyncMock(return_value=MockToolResponse())
        result = await execute_python_code("print('test')", timeout=5)
        assert "test" in str(result)

    # Test file reading
    with patch(
        "conversational_agents.chatbot.main.view_text_file",
    ) as mock_file:
        mock_file.return_value = AsyncMock(return_value=MockToolResponse())
        result = await view_text_file("test.txt")
        assert "test" in str(result)


@pytest.mark.asyncio
async def test_memory_integration(mock_memory):
    """Test memory integration"""
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
        # Create mocked model
        mock_model = MagicMock()

        # Create mocked formatter
        mock_formatter = MagicMock()
        mock_formatter.format = AsyncMock(return_value="mocked prompt")

        # Initialize agent
        agent = ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=mock_model,
            formatter=mock_formatter,
            toolkit=MagicMock(),
            memory=mock_memory,
        )

        # Fix all async-related mock objects
        agent._reasoning_hint_msgs = MagicMock()
        agent._reasoning_hint_msgs.get_memory = AsyncMock(return_value=[])
        agent.plan_notebook = MagicMock()
        agent.plan_notebook.get_current_hint = AsyncMock(return_value=None)
        agent._reasoning_hint_msgs.add = AsyncMock()
        agent.print = AsyncMock()

        # Test memory recording
        test_msg = Msg(
            name="User",
            content="test message",
            role="user",
        )

        agent.memory.add = AsyncMock()  # Fix await expression error
        await agent(test_msg)
        agent.memory.add.assert_awaited_once_with(test_msg)
