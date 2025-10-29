# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)

from agentscope.message import Msg



# Use correct module path (replace with your actual module path)
@patch("functionality.plan.main_agent_managed_plan.ReActAgent")  # ✅ Mock from actual usage location
@patch("functionality.plan.main_agent_managed_plan.Toolkit")
@patch("functionality.plan.main_agent_managed_plan.UserAgent")
@pytest.mark.asyncio
async def test_main_flow(mock_user, mock_toolkit, mock_agent) -> None:
    """验证完整流程逻辑"""
    # Configure async mock for agent
    mock_agent_instance = AsyncMock()
    mock_agent.return_value = mock_agent_instance

    # Mock agent reply with async response
    mock_agent_instance.reply.return_value = Msg(
        "assistant",
        "Test response",
        "assistant"
    )

    # Configure async mock for user
    mock_user_instance = AsyncMock()
    mock_user.return_value = mock_user_instance

    # Mock user response
    mock_user_instance.return_value = Msg("user", "exit", "user")

    # Import target module after path setup
    import functionality.plan.main_agent_managed_plan as main_module

    # Explicitly call main function in test context
    await main_module.main()

    # Verify interactions
    mock_agent.assert_called_once()
    mock_toolkit.assert_called_once()
    mock_user.assert_called_once()