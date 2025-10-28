# -*- coding: utf-8 -*-
# tests/chatbot_fullstack_runtime/test_agent_server.py
import os

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from agentscope.message import Msg

# 避免实际启动服务
with patch("agentscope_runtime.engine.LocalDeployManager"):
    from conversational_agents.chatbot_fullstack_runtime.backend.agent_server import (
        _local_deploy,
    )


@pytest.mark.asyncio
async def test_local_deploy():
    """Test agent server initialization"""
    with patch.dict(
        os.environ,
        {
            "SERVER_PORT": "8090",
            "SERVER_ENDPOINT": "agent",
            "DASHSCOPE_API_KEY": "test_key",
        },
    ):
        # Mock 依赖
        with patch(
            "conversational_agents.chatbot_fullstack_runtime.agent_server.LLMAgent",
        ) as mock_agent:
            mock_agent_instance = MagicMock()
            mock_agent.return_value = mock_agent_instance

            with patch(
                "conversational_agents.chatbot_fullstack_runtime.agent_server.Runner",
            ) as mock_runner:
                mock_runner_instance = MagicMock()
                mock_runner.return_value = mock_runner_instance

                with patch(
                    "conversational_agents.chatbot_fullstack_runtime.agent_server.LocalDeployManager",
                ) as mock_deploy:
                    mock_deploy_instance = MagicMock()
                    mock_deploy.return_value = mock_deploy_instance

                    # 模拟部署成功
                    mock_runner.return_value.deploy = AsyncMock(
                        return_value={
                            "url": "http://localhost:8090",
                        },
                    )

                    # 限制无限循环
                    with patch(
                        "asyncio.sleep",
                        new=AsyncMock(side_effect=asyncio.TimeoutError()),
                    ):
                        try:
                            await _local_deploy()
                        except asyncio.TimeoutError:
                            pass  # 期望的异常

                        # 验证初始化
                        mock_agent.assert_called_once()
                        mock_runner.assert_called_once()
                        mock_deploy.assert_called_once_with(
                            host="localhost",
                            port=8090,
                        )
