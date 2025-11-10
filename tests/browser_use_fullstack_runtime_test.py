# -*- coding: utf-8 -*-
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio

from quart.testing import QuartClient

from browser_use.browser_use_fullstack_runtime.backend import (
    agentscope_browseruse_agent as agent_module,
)
from browser_use.browser_use_fullstack_runtime.backend import (
    async_quart_service as service,
)

AgentscopeBrowseruseAgent = agent_module.AgentscopeBrowseruseAgent
RunStatus = agent_module.RunStatus
app = service.app


# -----------------------------
# 🧪 Singleton Test Configuration
# -----------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for session scope."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def agent_singleton():
    """Session-scoped single instance of AgentscopeBrowseruseAgent"""
    with patch(
        "browser_use.browser_use_fullstack_runtime."
        "backend.agentscope_browseruse_agent.SandboxService",
    ) as MockSandboxService, patch(
        "browser_use.browser_use_fullstack_runtime."
        "backend.agentscope_browseruse_agent.InMemoryMemoryService",
    ) as MockMemoryService, patch(
        "browser_use.browser_use_fullstack_runtime."
        "backend.agentscope_browseruse_agent.InMemorySessionHistoryService",
    ) as MockHistoryService, patch(
        "agentscope_runtime.common.container_clients.docker_client.docker",
    ) as mock_docker, patch(
        "agentscope_runtime.sandbox.manager.sandbox_manager.SandboxManager",
    ) as MockSandboxManager:
        # ✅ Fully mock Docker dependencies
        mock_api = MagicMock()
        mock_api.version.return_value = {"ApiVersion": "1.0"}

        mock_client = MagicMock()
        mock_client.api = mock_api
        mock_client.from_env.return_value = mock_client
        mock_client.__enter__.return_value = mock_client

        # ✅ Fully mock APIClient
        mock_docker.APIClient = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # ✅ Fully mock SandboxManager
        MockSandboxManager.return_value = MagicMock()

        # Configure InMemorySessionHistoryService
        mock_session = MagicMock()
        mock_session.create_session = AsyncMock()
        MockHistoryService.return_value = mock_session

        # Configure InMemoryMemoryService
        mock_memory = MagicMock()
        mock_memory.start = AsyncMock()
        MockMemoryService.return_value = mock_memory

        # Configure SandboxService
        mock_sandbox = MagicMock()
        mock_sandbox.start = AsyncMock()
        MockSandboxService.return_value = mock_sandbox

        agent = AgentscopeBrowseruseAgent()
        await agent.connect()
        return agent


@pytest.fixture(scope="session")
async def test_app():
    """Create Quart application test client"""
    async with QuartClient(app) as client:
        yield client


# -----------------------------
# ✅ AgentscopeBrowseruseAgent Singleton Tests
# -----------------------------
@pytest.mark.asyncio
async def agent_singleton_singleton_initialization(
    agent_singleton,  # pylint: disable=redefined-outer-name
):
    """Test agent singleton initialization"""
    agent = agent_singleton  # pylint: disable=redefined-outer-name
    assert isinstance(agent, AgentscopeBrowseruseAgent)
    assert hasattr(agent, "agent")
    assert hasattr(agent, "runner")


@pytest.mark.asyncio
async def test_chat_method(
    agent_singleton,
):  # pylint: disable=redefined-outer-name
    """Test chat method handles messages"""
    mock_request = {
        "messages": [
            {"role": "user", "content": "Hello"},
        ],
    }

    # ✅ Create mock object with object/status properties
    mock_event = SimpleNamespace(
        object="message",
        status=agent_module.RunStatus.Completed,
        content=[{"type": "text", "text": "Test response"}],
    )

    with patch.object(
        agent_singleton.runner,  # pylint: disable=redefined-outer-name
        "stream_query",
    ) as mock_stream:
        # ✅ Return object with properties
        async def mock_stream_query(*_args, **_kwargs):
            yield mock_event

        mock_stream.side_effect = mock_stream_query

        responses = []
        async for response in agent_singleton.chat(
            # pylint: disable=redefined-outer-name
            mock_request["messages"],
        ):
            responses.append(response)

        assert len(responses) == 1
        assert (
            responses[0][0]["text"] == "Test response"
        )  # ✅ Fix property access
