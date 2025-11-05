# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import StdIOStatefulClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel

from deep_research.agent_deep_research.deep_research_agent import (
    DeepResearchAgent,
)
from deep_research.agent_deep_research.main import main


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set required environment variables"""
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test_dashscope_key")
    return {
        "TAVILY_API_KEY": "test_tavily_key",
        "DASHSCOPE_API_KEY": "test_dashscope_key",
    }


@pytest.fixture
def temp_working_dir():
    """Create a temporary working directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_tavily_client():
    """Create a mocked Tavily client"""
    client = AsyncMock(spec=StdIOStatefulClient)
    client.name = "tavily_mcp"
    client.connect = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_formatter():
    """Create a mocked formatter"""
    return Mock(spec=DashScopeChatFormatter)


@pytest.fixture
def mock_memory():
    """Create a mocked memory instance"""
    return Mock(spec=InMemoryMemory)


@pytest.fixture
def mock_model():
    """Create a mocked model instance"""
    model = Mock(spec=DashScopeChatModel)
    model.call = AsyncMock(return_value=Mock(content="test response"))
    return model


class TestDeepResearchAgent:
    """Test suite for Deep Research Agent functionality"""

    def test_agent_initialization(
        self,
        mock_model,  # pylint: disable=redefined-outer-name
        mock_tavily_client,  # pylint: disable=redefined-outer-name
        temp_working_dir,  # pylint: disable=redefined-outer-name
    ):
        """Test agent initialization with valid parameters"""
        mock_loop = MagicMock()
        mock_task = AsyncMock()
        mock_loop.create_task = MagicMock(return_value=mock_task)
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            agent = DeepResearchAgent(
                name="Friday",
                sys_prompt="You are a helpful assistant named Friday.",
                model=mock_model,
                formatter=DashScopeChatFormatter(),
                memory=InMemoryMemory(),
                search_mcp_client=mock_tavily_client,
                tmp_file_storage_dir=temp_working_dir,
            )

        assert agent.name == "Friday"
        assert agent.sys_prompt.startswith(
            "You are a helpful assistant named Friday.",
        )
        assert agent.tmp_file_storage_dir == temp_working_dir
        assert os.path.exists(temp_working_dir)

    @pytest.mark.asyncio
    async def test_main_function_success(
        self,
        mock_tavily_client,  # pylint: disable=redefined-outer-name
        temp_working_dir,  # pylint: disable=redefined-outer-name
    ):
        """Test main function with successful execution"""
        with patch(
            "deep_research.agent_deep_research.main.StdIOStatefulClient",
            return_value=mock_tavily_client,
        ):
            with patch(
                "deep_research.agent_deep_research.main.DeepResearchAgent",
                autospec=True,
            ) as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent.return_value = Msg(
                    "Friday",
                    "Test response",
                    "assistant",
                )
                mock_agent_class.return_value = mock_agent

                with patch("os.makedirs") as mock_makedirs:
                    with patch.dict(
                        os.environ,
                        {"AGENT_OPERATION_DIR": temp_working_dir},
                    ):
                        test_query = "Test research question"

                        await main(test_query)

                        mock_makedirs.assert_called_once_with(
                            temp_working_dir,
                            exist_ok=True,
                        )
                        mock_agent_class.assert_called_once()

                        # ✅ Use assert_called_once() + manual argument check
                        mock_agent.assert_called_once()
                        call_arg = mock_agent.call_args[0][0]
                        assert call_arg.name == "Bob"
                        assert call_arg.content == "Test research question"

    @pytest.mark.asyncio
    async def test_main_function_with_missing_env_vars(self):
        """Test main function handles missing environment variables"""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(Exception):
                await main("Test query")

    @pytest.mark.asyncio
    async def test_agent_cleanup(
        self,
        mock_tavily_client,  # pylint: disable=redefined-outer-name
    ):
        """Test proper cleanup of resources"""
        with patch(
            "deep_research.agent_deep_research.main.StdIOStatefulClient",
            return_value=mock_tavily_client,
        ):
            with patch.dict(os.environ, {"AGENT_OPERATION_DIR": "/tmp"}):
                await main("Test query")

            mock_tavily_client.close.assert_called_once()

    def test_working_directory_creation(
        self,
        temp_working_dir,  # pylint: disable=redefined-outer-name
    ):
        """Test working directory is created correctly"""
        test_dir = os.path.join(temp_working_dir, "test_subdir")
        os.makedirs(test_dir, exist_ok=True)
        assert os.path.exists(test_dir)
        os.makedirs(test_dir, exist_ok=True)  # Should not raise error


class TestErrorHandling:
    """Test suite for error handling scenarios"""

    @pytest.mark.asyncio
    async def test_filesystem_errors(
        self,
        mock_tavily_client,  # pylint: disable=redefined-outer-name
    ):
        """Test handling of filesystem errors"""
        with patch(
            "deep_research.agent_deep_research.main.StdIOStatefulClient",
            return_value=mock_tavily_client,
        ):
            with patch.dict(
                os.environ,
                {"AGENT_OPERATION_DIR": "/invalid/path"},
            ):
                with patch(
                    "os.makedirs",
                    side_effect=PermissionError("Permission denied"),
                ):
                    with pytest.raises(PermissionError):
                        await main("Test query")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
