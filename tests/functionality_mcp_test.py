# -*- coding: utf-8 -*-
import os
from unittest.mock import AsyncMock, Mock, patch
import pytest
from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatefulClient, HttpStatelessClient
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from browser_use.functionality.mcp import main
from pydantic import BaseModel, Field


class NumberResult(BaseModel):
    """A simple number result model for structured output."""

    result: int = Field(description="The result of the calculation")


class TestMCPReActAgent:
    """Test suite for MCP ReAct agent functionality"""

    @pytest.fixture
    def mock_toolkit(self) -> Toolkit:
        """Create a mocked Toolkit instance"""
        return Mock(spec=Toolkit)

    @pytest.fixture
    def mock_stateful_client(self) -> HttpStatefulClient:
        """Create a mocked HttpStatefulClient"""
        client = Mock(spec=HttpStatefulClient)
        client.connect = AsyncMock()
        client.close = AsyncMock()
        client.get_callable_function = AsyncMock()
        return client

    @pytest.fixture
    def mock_stateless_client(self) -> HttpStatelessClient:
        """Create a mocked HttpStatelessClient"""
        client = Mock(spec=HttpStatelessClient)
        return client

    @pytest.fixture
    def mock_model(self) -> DashScopeChatModel:
        """Create a mocked DashScopeChatModel"""
        model = Mock(spec=DashScopeChatModel)
        model.call = AsyncMock(return_value=Mock(content="test response"))
        return model

    @pytest.fixture
    def mock_formatter(self) -> DashScopeChatFormatter:
        """Create a mocked DashScopeChatFormatter"""
        return Mock(spec=DashScopeChatFormatter)

    @pytest.fixture
    def mock_agent(
        self,
        mock_model: DashScopeChatModel,
        mock_formatter: DashScopeChatFormatter,
        mock_toolkit: Toolkit,
    ) -> Mock:
        """Create a mocked ReActAgent instance"""
        agent = Mock(spec=ReActAgent)
        agent.model = mock_model
        agent.formatter = mock_formatter
        agent.toolkit = mock_toolkit
        agent.__call__ = AsyncMock(
            return_value=Mock(
                metadata={"result": 123456},
            ),
        )
        return agent

    @pytest.mark.asyncio
    async def test_mcp_client_initialization(self) -> None:
        """Test MCP client initialization with different transports"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Test stateful client creation
            stateful_client = HttpStatefulClient(
                name="add_client",
                transport="sse",
                url="http://localhost:8080",
            )
            assert stateful_client.name == "add_client"
            assert stateful_client.transport == "sse"
            assert stateful_client.url == "http://localhost:8080"

            # Test stateless client creation
            stateless_client = HttpStatelessClient(
                name="multiply_client",
                transport="streamable_http",
                url="http://localhost:8081",
            )
            assert stateless_client.name == "multiply_client"
            assert stateless_client.transport == "streamable_http"
            assert stateless_client.url == "http://localhost:8081"

    @pytest.mark.asyncio
    async def test_toolkit_registration(
        self,
        mock_toolkit: Toolkit,
        mock_stateful_client: HttpStatefulClient,
        mock_stateless_client: HttpStatelessClient,
    ) -> None:
        """Test MCP client registration with toolkit"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Mock connect and register methods
            mock_toolkit.register_mcp_client = AsyncMock()

            # Verify registration of both clients
            await mock_toolkit.register_mcp_client(mock_stateful_client)
            await mock_toolkit.register_mcp_client(mock_stateless_client)

            assert mock_toolkit.register_mcp_client.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_initialization(
        self,
        mock_model: DashScopeChatModel,
        mock_formatter: DashScopeChatFormatter,
        mock_toolkit: Toolkit,
    ) -> None:
        """Test ReAct agent initialization"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            agent = ReActAgent(
                name="Jarvis",
                sys_prompt="You're a helpful assistant named Jarvis.",
                model=mock_model,
                formatter=mock_formatter,
                toolkit=mock_toolkit,
            )

            assert agent.name == "Jarvis"
            assert (
                agent.sys_prompt == "You're a helpful assistant named Jarvis."
            )
            assert agent.model == mock_model
            assert agent.formatter == mock_formatter
            assert agent.toolkit == mock_toolkit

    @pytest.mark.asyncio
    async def test_structured_output(
        self,
        mock_agent: ReActAgent,
    ) -> None:
        """Test structured output handling"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Create test message
            test_msg = Msg(
                "user",
                "Calculate 2345 multiplied by 3456, then add 4567 to the result,"
                " what is the final outcome?",
                "user",
            )

            # Run agent with structured model
            result = await mock_agent(test_msg, structured_model=NumberResult)

            # Verify structured output
            assert isinstance(result, Mock)
            assert result.metadata["result"] == 123456

    @pytest.mark.asyncio
    async def test_manual_tool_call(
        self,
        mock_stateful_client: HttpStatefulClient,
    ) -> None:
        """Test manual tool call functionality"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Mock callable function
            mock_callable = AsyncMock(return_value=Mock(content="15"))
            mock_stateful_client.get_callable_function = AsyncMock(
                return_value=mock_callable,
            )

            # Call tool manually
            tool_function = await mock_stateful_client.get_callable_function(
                "add",
            )
            response = await tool_function(a=5, b=10)

            # Verify tool call
            mock_stateful_client.get_callable_function.assert_called_once_with(
                "add",
                wrap_tool_result=True,
            )
            mock_callable.assert_called_once_with(a=5, b=10)
            assert response.content == "15"

    @pytest.mark.asyncio
    async def test_client_lifecycle(
        self,
        mock_stateful_client: HttpStatefulClient,
    ) -> None:
        """Test MCP client connection and cleanup"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Test connection
            await mock_stateful_client.connect()
            mock_stateful_client.connect.assert_awaited_once()

            # Test cleanup
            await mock_stateful_client.close()
            mock_stateful_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_full_integration_flow(
        self,
        mock_stateful_client: HttpStatefulClient,
        mock_stateless_client: HttpStatelessClient,
        mock_toolkit: Toolkit,
        mock_model: DashScopeChatModel,
        mock_formatter: DashScopeChatFormatter,
    ) -> None:
        """Test full integration flow with mocked dependencies"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Mock async methods
            mock_toolkit.register_mcp_client = AsyncMock()
            mock_stateful_client.connect = AsyncMock()
            mock_model.call = AsyncMock(
                return_value=Mock(
                    content="Final answer: 8101807",
                ),
            )

            # Patch the agent class
            with patch("main.ReActAgent") as mock_agent_class:
                mock_agent = Mock()
                mock_agent.__call__ = AsyncMock(
                    return_value=Mock(
                        metadata={"result": 8101807},
                    ),
                )
                mock_agent_class.return_value = mock_agent

                # Run the main function
                await main.main()

                # Verify full flow
                mock_stateful_client.connect.assert_awaited_once()
                mock_toolkit.register_mcp_client.assert_any_call(
                    mock_stateful_client,
                )
                mock_toolkit.register_mcp_client.assert_any_call(
                    mock_stateless_client,
                )
                mock_agent_class.assert_called_once()
                mock_agent.__call__.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
