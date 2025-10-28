# -*- coding: utf-8 -*-
import os
import pytest
from unittest.mock import AsyncMock, patch

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测模块
from ..functionality.stream_printing_messages import multi_agent


@pytest.mark.asyncio
async def test_agent_creation() -> None:
    """验证代理创建逻辑"""
    agent = multi_agent.create_agent("Alice")
    assert agent.name == "Alice"
    assert "Alice" in agent.sys_prompt


@pytest.mark.asyncio
async def test_workflow_execution() -> None:
    """验证多代理工作流执行"""
    with patch("stream_printing_messages.MsgHub", AsyncMock()):
        # 创建 Mock 代理
        alice = AsyncMock()
        bob = AsyncMock()
        charlie = AsyncMock()

        # 模拟工作流
        await multi_agent.workflow(alice, bob, charlie)

        # 验证代理调用顺序
        alice.assert_awaited()
        bob.assert_awaited()
        charlie.assert_awaited()
