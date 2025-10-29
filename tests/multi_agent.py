# -*- coding: utf-8 -*-
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Add root dir to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from functionality.stream_printing_messages import multi_agent


@pytest.mark.asyncio
async def test_agent_creation() -> None:
    """Verify agent creation logic"""
    agent = multi_agent.create_agent("Alice")
    assert agent.name == "Alice"
    assert "Alice" in agent.sys_prompt


@pytest.mark.asyncio
async def test_workflow_execution() -> None:
    """Verify multi-agent workflow execution"""
    # ✅ Create proper async context manager mock
    mock_hub = AsyncMock()
    mock_hub.__aenter__.return_value = mock_hub
    mock_hub.__aexit__.return_value = AsyncMock()

    # Patch the MsgHub to use our mock
    with patch(
        "functionality.stream_printing_messages.multi_agent.MsgHub",
        return_value=mock_hub,
    ):
        # Create mock agents
        alice = AsyncMock()
        bob = AsyncMock()
        charlie = AsyncMock()

        # Run the workflow
        await multi_agent.workflow(alice, bob, charlie)

        # Verify agents were called
        alice.assert_awaited()
        bob.assert_awaited()
        charlie.assert_awaited()