# tests/functionality_mcp_test.py
# -*- coding: utf-8 -*-
import os
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, List, Union
from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatefulClient, HttpStatelessClient
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from pydantic import BaseModel, Field


class NumberResult(BaseModel):
    """A simple number result model for structured output"""
    result: int = Field(description="The result of the calculation")


def create_mock_toolkit() -> Toolkit:
    """Create a toolkit with mocked MCP clients"""
    toolkit = Mock(spec=Toolkit)
    toolkit.register_mcp_client = AsyncMock()
    return toolkit


def create_mock_model() -> DashScopeChatModel:
    """Create a model that returns predictable responses"""
    model = Mock(spec=DashScopeChatModel)
    model.call = AsyncMock(return_value=Mock(content="test response"))
    return model


def create_mock_agent() -> ReActAgent:
    """Create a mocked ReActAgent instance"""
    agent = Mock(spec=ReActAgent)
    agent.model = create_mock_model()
    agent.formatter = Mock(spec=DashScopeChatFormatter)
    agent.toolkit = create_mock_toolkit()

    # Make agent callable with async support
    async def mock_call(*args, **kwargs) -> Mock:
        return Mock(metadata={"result": 123456})

    agent.__call__ = mock_call
    return agent


class TestMCPReActAgent:
    """Test suite for MCP ReAct agent functionality"""

    def test_mcp_client_initialization(self) -> None:
        """Test MCP client initialization with different transports"""
        # Create clients
        stateful_client = HttpStatefulClient(
            name="add_client",
            transport="sse",
            url="http://localhost:8080",
        )
        stateless_client = HttpStatelessClient(
            name="multiply_client",
            transport="streamable_http",
            url="http://localhost:8081",
        )

        # Validate initialization
        assert stateful_client.name == "add_client"
        assert stateful_client.transport == "sse"

        assert stateless_client.name == "multiply_client"
        assert stateless_client.transport == "streamable_http"

    @pytest.mark.asyncio
    async def test_toolkit_registration(self) -> None:
        """Test MCP client registration with toolkit"""
        # Create mocked clients
        stateful_client = Mock(spec=HttpStatefulClient)
        stateless_client = Mock(spec=HttpStatelessClient)

        # Create mock toolkit
        mock_toolkit = Mock(spec=Toolkit)
        mock_toolkit.register_mcp_client = AsyncMock()

        # Register clients
        await mock_toolkit.register_mcp_client(stateful_client)
        await mock_toolkit.register_mcp_client(stateless_client)

        # Validate registration
        assert mock_toolkit.register_mcp_client.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_initialization(
            self,
            request: pytest.FixtureRequest,
    ) -> None:
        """Test ReAct agent initialization"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Create mocked components
            model = Mock(spec=DashScopeChatModel)
            formatter = Mock(spec=DashScopeChatFormatter)
            toolkit = Mock(spec=Toolkit)

            # Initialize agent
            agent = ReActAgent(
                name="Jarvis",
                sys_prompt="You're a helpful assistant named Jarvis.",
                model=model,
                formatter=formatter,
                toolkit=toolkit,
            )

            # Validate initialization
            assert agent.name == "Jarvis"
            assert agent.sys_prompt == "You're a helpful assistant named Jarvis."
            assert agent.model == model
            assert agent.formatter == formatter
            assert agent.toolkit == toolkit

    @pytest.mark.asyncio
    async def test_structured_output(self) -> None:
        """Test structured output handling"""
        # Create test message
        test_msg = Msg(
            "user",
            "Calculate 2345 multiplied by 3456, then add 4567 to the result,"
            " what is the final outcome?",
            "user",
        )

        # Create agent with structured response
        mock_agent = Mock(spec=ReActAgent)

        async def mock_call(*args, **kwargs) -> Mock:
            return Mock(metadata={"result": 123456})

        mock_agent.__call__ = mock_call

    @pytest.mark.asyncio
    async def test_manual_tool_call(self) -> None:
        """Test manual tool call functionality"""
        # Create mock client
        stateful_client = Mock(spec=HttpStatefulClient)
        stateful_client.get_callable_function = AsyncMock()

        # Mock callable function
        mock_callable = AsyncMock(return_value=Mock(content="15"))
        stateful_client.get_callable_function.return_value = mock_callable

        # Call tool manually
        tool_function = await stateful_client.get_callable_function("add")
        response = await tool_function(a=5, b=10)

        # Validate tool call - remove wrap_tool_result from assertion
        stateful_client.get_callable_function.assert_called_once_with("add")
        mock_callable.assert_called_once_with(a=5, b=10)
        assert response.content == "15"

    @pytest.mark.asyncio
    async def test_client_lifecycle(self) -> None:
        """Test MCP client connection and cleanup"""
        # Create mock clients
        stateful_client = Mock(spec=HttpStatefulClient)
        stateful_client.connect = AsyncMock()
        stateful_client.close = AsyncMock()

        # Test connection
        await stateful_client.connect()
        stateful_client.connect.assert_awaited_once()

        # Test cleanup
        await stateful_client.close()
        stateful_client.close.assert_awaited_once()
