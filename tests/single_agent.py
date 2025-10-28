# -*- coding: utf-8 -*-
import os
import pytest
from unittest.mock import AsyncMock, patch

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测模块
from functionality.stream_printing_messages import single_agent
from agentscope.message import Msg


@pytest.mark.asyncio
async def test_toolkit_registration() -> None:
    """验证工具注册逻辑"""
    mock_toolkit = AsyncMock()
    mock_toolkit.register_tool_function = AsyncMock()

    # ✅ mock Toolkit 和 DashScopeChatModel
    with patch(
        "functionality.stream_printing_messages.single_agent.Toolkit",
        return_value=mock_toolkit,
    ), patch("agentscope.model.DashScopeChatModel") as mock_model:
        # ✅ 模拟模型响应
        mock_model.return_value.get_response = AsyncMock(
            return_value=Msg("assistant", "Test response", "assistant"),
        )

        agent = await single_agent.main()
        mock_toolkit.register_tool_function.assert_any_call(
            single_agent.execute_shell_command,
        )
        mock_toolkit.register_tool_function.assert_any_call(
            single_agent.execute_python_code,
        )


@pytest.mark.asyncio
async def test_streaming_messages() -> None:
    """验证流式消息处理"""
    mock_agent = AsyncMock()
    mock_agent.return_value = {"content": "Hello, World!"}

    with patch("agentscope.agent.ReActAgent", return_value=mock_agent):
        async for msg, last in single_agent.stream_printing_messages(
            agents=[mock_agent],
            coroutine_task=mock_agent(Msg("user", "Hi", "user")),
        ):
            assert msg == "Hello, World!"
            assert last == True
