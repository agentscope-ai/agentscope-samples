# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
import sqlite3
from unittest.mock import AsyncMock, patch
from agentscope.message import Msg
from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.model import DashScopeChatModel

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测模块
import session_with_sqlite.sqlite_session as sqlite_session
from session_with_sqlite import main

# 使用内存数据库替代文件数据库
SQLITE_PATH = ":memory:"  # 使用内存数据库


class MockSqliteSession(sqlite_session.SqliteSession):
    """使用内存数据库的 SqliteSession 子类"""

    def __init__(self) -> None:
        super().__init__(SQLITE_PATH)


@pytest.mark.asyncio
async def test_session_initialization() -> None:
    """验证会话初始化逻辑"""
    session = MockSqliteSession()
    assert session.db_path == SQLITE_PATH
    await session.close()


@pytest.mark.asyncio
async def test_save_and_load_session() -> None:
    """验证会话保存和加载功能"""
    # 创建 Mock Agent
    mock_model = AsyncMock(spec=DashScopeChatModel)
    mock_model.get_response.return_value = Msg(
        "assistant",
        "Washington D.C.",
        "friday",
    )

    agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=mock_model,
        formatter=DashScopeChatFormatter(),
    )

    # 初始化会话
    session = MockSqliteSession()
    await session.save_session_state(session_id="alice", friday_of_user=agent)

    # 创建新 Agent 实例并加载会话
    new_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=mock_model,
        formatter=DashScopeChatFormatter(),
    )
    await session.load_session_state(
        session_id="alice",
        friday_of_user=new_agent,
    )

    # 验证历史消息
    assert len(new_agent.memory) == 1
    assert new_agent.memory[0].content == "Washington D.C."
    await session.close()


@pytest.mark.asyncio
async def test_user_isolation() -> None:
    """验证不同用户的数据隔离"""
    session = MockSqliteSession()

    # Alice 的会话
    alice_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.save_session_state(
        session_id="alice",
        friday_of_user=alice_agent,
    )

    # Bob 的会话
    bob_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.save_session_state(
        session_id="bob",
        friday_of_user=bob_agent,
    )

    # 验证 Alice 的会话
    alice_new_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.load_session_state(
        session_id="alice",
        friday_of_user=alice_new_agent,
    )
    assert len(alice_new_agent.memory) == 1

    # 验证 Bob 的会话
    bob_new_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.load_session_state(
        session_id="bob",
        friday_of_user=bob_new_agent,
    )
    assert len(bob_new_agent.memory) == 1

    await session.close()


@pytest.mark.asyncio
async def test_consecutive_interactions() -> None:
    """验证多次交互后状态恢复"""
    session = MockSqliteSession()

    # 第一次交互
    agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.save_session_state(session_id="alice", friday_of_user=agent)

    # 第二次交互
    new_agent = ReActAgent(
        name="friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=AsyncMock(spec=DashScopeChatModel),
        formatter=DashScopeChatFormatter(),
    )
    await session.load_session_state(
        session_id="alice",
        friday_of_user=new_agent,
    )
    assert len(new_agent.memory) == 1

    await session.close()
