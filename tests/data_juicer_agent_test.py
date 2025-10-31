# -*- coding: utf-8 -*-
import os

import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(Path(root_path)/"data_juicer_agent"))

import pytest
from unittest.mock import AsyncMock, Mock, patch
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.message import Msg
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import (
    view_text_file,
    write_text_file,
)

# Import the main function and related components
from data_juicer_agent.main import main
from data_juicer_agent.agent_factory import create_agent
from data_juicer_agent.tools import (
    dj_toolkit,
    dj_dev_toolkit,
    dj_tools,
    dj_dev_tools,
    mcp_tools,
    get_mcp_toolkit,
    execute_safe_command,
    query_dj_operators,
    get_basic_files,
    get_operator_example,
    configure_data_juicer_path,
)


class TestDataJuicerAgent:
    """Test suite for the data_juicer_agent functionality"""

    @pytest.fixture
    def mock_toolkit(self):
        """Create a mocked Toolkit instance"""
        return Mock(spec=Toolkit)

    @pytest.fixture
    def mock_model(self):
        """Create a mocked DashScopeChatModel"""
        model = Mock(spec=DashScopeChatModel)
        model.call = AsyncMock(
            return_value=Msg("assistant", "test response", role="assistant"),
        )
        return model

    @pytest.fixture
    def mock_formatter(self):
        """Create a mocked DashScopeChatFormatter"""
        return Mock(spec=DashScopeChatFormatter)

    @pytest.fixture
    def mock_memory(self):
        """Create a mocked InMemoryMemory"""
        return Mock(spec=InMemoryMemory)

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mocked MCP client"""
        mock_client = Mock()
        mock_client.name = "DJ_recipe_flow"
        mock_client.connect = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.get_callable_function = AsyncMock()
        mock_client.list_tools = AsyncMock()
        return mock_client

    def create_named_mock_agent(self, name, mock_agent, *args, **kwargs):
        """Create a named mock agent for testing"""
        agent_instance = Mock(spec=ReActAgent)
        agent_instance.model = mock_agent.model
        agent_instance.formatter = mock_agent.formatter
        agent_instance.toolkit = mock_agent.toolkit
        agent_instance.memory = mock_agent.memory
        agent_instance.__call__ = mock_agent.__call__
        agent_instance.name = name
        return agent_instance

    @pytest.fixture
    def mock_agent(
        self,
        mock_model,
        mock_formatter,
        mock_toolkit,
        mock_memory,
    ):
        """Create a mocked ReActAgent instance"""
        agent = Mock(spec=ReActAgent)
        agent.model = mock_model
        agent.formatter = mock_formatter
        agent.toolkit = mock_toolkit
        agent.memory = mock_memory
        agent.__call__ = AsyncMock(
            return_value=Msg("assistant", "test response", role="assistant"),
        )
        return agent

    def test_dj_toolkit_initialization(self):
        """Test DJ toolkit initialization and tool registration"""
        assert dj_toolkit.tools.get("execute_safe_command") is not None
        assert dj_toolkit.tools.get("view_text_file") is not None
        assert dj_toolkit.tools.get("write_text_file") is not None
        assert dj_toolkit.tools.get("query_dj_operators") is not None

        # Verify tool list contains expected tools
        expected_tools = [
            execute_safe_command,
            view_text_file,
            write_text_file,
            query_dj_operators,
        ]
        assert len(dj_tools) == len(expected_tools)
        for tool in expected_tools:
            assert tool in dj_tools

    def test_dj_dev_toolkit_initialization(self):
        """Test DJ development toolkit initialization and tool registration"""
        assert dj_dev_toolkit.tools.get("view_text_file") is not None
        assert dj_dev_toolkit.tools.get("write_text_file") is not None
        assert dj_dev_toolkit.tools.get("get_basic_files") is not None
        assert dj_dev_toolkit.tools.get("get_operator_example") is not None
        assert dj_dev_toolkit.tools.get("configure_data_juicer_path") is not None

        # Verify tool list contains expected tools
        expected_tools = [
            view_text_file,
            write_text_file,
            get_basic_files,
            get_operator_example,
            configure_data_juicer_path,
        ]
        assert len(dj_dev_tools) == len(expected_tools)
        for tool in expected_tools:
            assert tool in dj_dev_tools

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self, mock_mcp_client):
        """Test MCP tools list contains expected tools and MCP client binding"""
        with patch(
                "agentscope.mcp.HttpStatefulClient",
                return_value=mock_mcp_client,
            ) as mock_client_cls:
            await get_mcp_toolkit()
            assert mock_client_cls.assert_called_once
            
        expected_tools = [view_text_file, write_text_file]
        assert len(mcp_tools) == len(expected_tools)
        for tool in expected_tools:
            assert tool in mcp_tools

    @pytest.mark.asyncio
    async def test_agent_initialization(
        self,
        mock_model,
        mock_formatter,
        mock_toolkit,
        mock_memory,
    ):
        """Test ReActAgent initialization"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            agent = create_agent(
                name="DataJuicer",
                sys_prompt="You are {name}, a agent.",
                toolkit=mock_toolkit,
                model=mock_model,
                formatter=mock_formatter,
                memory=mock_memory,
            )

            assert agent.name == "DataJuicer"
            assert "DataJuicer" in agent.sys_prompt
            assert agent.model == mock_model
            assert agent.formatter == mock_formatter
            assert agent.toolkit == mock_toolkit
            assert agent.memory == mock_memory

    async def mock_user_func(self, msg=None):
        return Msg("user", "exit", role="user")

    @pytest.mark.asyncio
    async def test_main_with_multiple_agents_loading(self, mock_agent, mock_mcp_client):
        """Test main function loads multiple agents successfully"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            mock_mcp_clients = [mock_mcp_client]

            with patch(
                "data_juicer_agent.tools.mcp_helpers._create_clients",
                return_value=mock_mcp_clients,
            ):
                with patch(
                    "data_juicer_agent.main.create_agent",
                    side_effect=lambda name, *args, **kwargs: self.create_named_mock_agent(
                        name, mock_agent, *args, **kwargs
                    ),
                ) as mock_create_agent:
                    with patch(
                        "data_juicer_agent.main.user", side_effect=self.mock_user_func
                    ):

                        await main(
                            use_studio=False,
                            available_agents=["dj", "dj_dev", "dj_mcp"],
                            retrieval_mode="auto",
                        )

                        # Validate multiple agents are correctly created (dj, dj_dev, dj_mcp, and router)
                        assert mock_create_agent.call_count == 4

                        # Validate router agent is created
                        create_calls = mock_create_agent.call_args_list
                        router_agent_created = any(
                            call[0][0] == "Router"
                            for call in create_calls  # First parameter is name
                        )
                        assert router_agent_created, "Router agent should be created"

                        # Validate dj_mcp agent is created
                        mcp_agent_created = any(
                            call[0][0] == "mcp_datajuicer_agent"
                            for call in create_calls  # First parameter is name
                        )
                        assert mcp_agent_created, "MCP agent should be created"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
