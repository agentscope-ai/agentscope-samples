# -*- coding: utf-8 -*-
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio

from browser_use.browser_use_fullstack_runtime.backend.agentscope_browseruse_agent import (
    AgentscopeBrowseruseAgent,
)
from browser_use.browser_use_fullstack_runtime.backend.async_quart_service import (
    app,
)
from quart.testing import QuartClient


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
        "browser_use.browser_use_fullstack_runtime.backend.agentscope_browseruse_agent.SandboxService",
    ) as MockSandboxService, patch(
        "browser_use.browser_use_fullstack_runtime.backend.agentscope_browseruse_agent.InMemoryMemoryService",
    ) as MockMemoryService, patch(
        "browser_use.browser_use_fullstack_runtime.backend.agentscope_browseruse_agent.InMemorySessionHistoryService",
    ) as MockHistoryService, patch(
        "agentscope_runtime.sandbox.manager.container_clients.docker_client.docker"
    ) as mock_docker, patch(
        "agentscope_runtime.sandbox.manager.sandbox_manager.SandboxManager"
    ) as MockSandboxManager:
        # ✅ Completely mock Docker dependencies
        mock_api = MagicMock()
        mock_api.version.return_value = {
            "ApiVersion": "1.0"
        }  # Avoid real API calls

        mock_client = MagicMock()
        mock_client.api = mock_api
        mock_client.from_env.return_value = mock_client
        mock_client.__enter__.return_value = mock_client

        # ✅ Completely mock APIClient
        mock_docker.APIClient = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # ✅ Completely mock SandboxManager
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
    """Create test client for Quart app"""
    async with QuartClient(app) as client:
        yield client


# -----------------------------
# ✅ AgentscopeBrowseruseAgent Singleton Tests
# -----------------------------
@pytest.mark.asyncio
async def test_agent_singleton_initialization(agent_singleton):
    """Test agent singleton initialization"""
    agent = agent_singleton  # ✅ Remove await (fixture returns actual instance)
    assert isinstance(agent, AgentscopeBrowseruseAgent)
    assert hasattr(agent, "agent")
    assert hasattr(agent, "runner")


# @pytest.mark.asyncio
# async def test_connect_method(agent_singleton):
#     """Test connect method sets up services correctly"""
#     # ✅ Skip test due to Docker dependency
#     pytest.skip("Skipping due to Docker dependency")
#     await agent_singleton.connect()
#     assert agent_singleton.ws == ""


@pytest.mark.asyncio
async def test_chat_method(agent_singleton):
    """Test chat method handles messages correctly"""
    mock_request = {
        "messages": [
            {"role": "user", "content": "Hello"},
        ],
    }

    with patch.object(agent_singleton.runner, "stream_query") as mock_stream:

        async def mock_stream_query(*args, **kwargs):
            yield {
                "choices": [
                    {
                        "delta": {
                            "content": "Test response",
                            "cards": [
                                {"type": "text", "text": "Test response"}
                            ],
                        },
                    }
                ],
            }

        mock_stream.side_effect = mock_stream_query

        responses = []
        async for response in agent_singleton.chat(mock_request["messages"]):
            responses.append(response)

        assert len(responses) == 1
        assert responses[0][0].text == "Test response"


# -----------------------------
# ✅ Utility Function Tests
# -----------------------------
def test_simple_yield():
    """Test simple_yield function produces correct format"""
    from browser_use.browser_use_fullstack_runtime.backend.async_quart_service import (
        simple_yield,
    )

    result = simple_yield("test content")
    assert "data: " in result
    assert "test content" in result


def test_wrap_as_openai_response():
    """Test wrap_as_openai_response formats correctly"""
    from browser_use.browser_use_fullstack_runtime.backend.async_quart_service import (
        wrap_as_openai_response,
    )

    result = wrap_as_openai_response("text", "card", "content")

    assert result["choices"][0]["delta"]["content"] == "text"
    assert result["choices"][0]["delta"]["cards"] == "card"
