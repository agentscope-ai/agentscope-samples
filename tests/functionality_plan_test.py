# tests/functionality_plan_test.py
# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentscope.message import Msg
from typing import AsyncGenerator, Any

# Set environment variable
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# Import the script to be tested
import functionality.plan.main_manual_plan as main_manual_plan


# Async generator for streaming responses
async def mock_stream_response():
    """Create an async generator for model responses"""
    yield Msg("assistant", "I", "assistant")
    yield Msg("assistant", "will", "assistant")
    yield Msg("assistant", "help", "assistant")
    yield Msg("assistant", "you", "assistant")
    yield Msg("assistant", "create", "assistant")
    yield Msg("assistant", "a", "assistant")
    yield Msg("assistant", "plan", "assistant")


# Test fixtures
@pytest.fixture
def mock_chat_model():
    """Mock DashScopeChatModel with proper async stream support"""
    with patch("functionality.plan.main_manual_plan.DashScopeChatModel") as mock:
        # Create a mock model that supports streaming
        mock_model = AsyncMock()

        # Configure model to support both call and async iteration
        mock_model.return_value = mock_stream_response()
        mock_model.stream = True

        mock.return_value = mock_model
        yield mock


@pytest.fixture
def mock_user_agent():
    """Mock UserAgent with proper async support"""
    with patch("functionality.plan.main_manual_plan.UserAgent") as mock:
        # Create an async agent that can be awaited
        mock_agent = AsyncMock()

        # Set up a sequence of responses
        mock_agent.side_effect = [
            Msg("user", "Create a plan", "user"),
            Msg("user", "exit", "user")
        ]

        mock.return_value = mock_agent
        yield mock


@pytest.fixture
def mock_plan_notebook():
    """Mock PlanNotebook to prevent real plan creation"""
    with patch("functionality.plan.main_manual_plan.PlanNotebook") as mock:
        # Create a mock notebook with empty plan
        mock_notebook = MagicMock()
        mock_notebook.create_plan = AsyncMock()

        # Make notebook.get_current_hint() return a predictable value
        mock_notebook.get_current_hint = AsyncMock(return_value=Msg(
            "system",
            "This is a test hint",
            "system"
        ))

        mock.return_value = mock_notebook
        yield mock


@pytest.mark.asyncio
async def test_manual_plan_execution(
        mock_chat_model,
        mock_user_agent,
        mock_plan_notebook,
) -> None:
    """Verify manual plan execution"""
    await main_manual_plan.main()
    mock_user_agent.assert_called_once()


if __name__ == "__main__":
    asyncio.run(pytest.main(["-v", __file__]))