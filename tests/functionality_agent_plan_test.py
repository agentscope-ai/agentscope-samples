# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from agentscope.message import Msg

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测脚本
import functionality.plan.main_agent_managed_plan as main_agent_managed_plan


@pytest.mark.asyncio
async def test_react_agent_initialization() -> None:
    """验证 ReActAgent 初始化逻辑"""
    with patch("ex.plan.ex1.ReActAgent", autospec=True) as mock_agent:
        await main_agent_managed_plan.main()
        mock_agent.assert_called_once()


@pytest.mark.asyncio
async def test_toolkit_registration() -> None:
    """验证 Toolkit 工具注册"""
    with patch("ex.plan.ex1.Toolkit", autospec=True) as mock_toolkit:
        await main_agent_managed_plan.main()
        mock_toolkit.return_value.register_tool_function.assert_called()


@pytest.mark.asyncio
async def test_message_loop() -> None:
    """验证消息循环逻辑"""
    with patch("ex.plan.ex1.UserAgent", autospec=True) as mock_user:
        mock_user.return_value.__call__.side_effect = lambda x: Msg(
            "user",
            "exit",
            "user",
        )
        await main_agent_managed_plan.main()
        mock_user.assert_called_once()


if __name__ == "__main__":
    asyncio.run(pytest.main(["-v", __file__]))
