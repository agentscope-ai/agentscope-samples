import os
import asyncio
import pytest
from typing import List, Dict
from agentscope.message import Msg
from functionality.long_term_memory_mem0.memory_example import Mem0LongTermMemory, ReActAgent

# 跳过测试如果未配置 API 密钥
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    pytest.skip("Missing DASHSCOPE_API_KEY", allow_module_level=True)


@pytest.mark.asyncio
async def test_record_conversation() -> None:
    """Test recording a conversation to long-term memory."""
    memory = Mem0LongTermMemory(
        agent_name="Friday",
        user_name="test_user",
        model=ReActAgent.model_class(
            model_name="qwen-max-latest",
            api_key=DASHSCOPE_API_KEY,
        ),
        embedding_model=ReActAgent.embedding_class(
            model_name="text-embedding-v2",
            api_key=DASHSCOPE_API_KEY,
        ),
        on_disk=False,
    )

    msg = Msg(
        role="user",
        content="Please help me book a hotel, preferably homestay",
        name="user",
    )
    result = await memory.record(msgs=[msg])

    # 验证记录结果包含必要字段
    assert "memory_id" in result[0]
    assert "content" in result[0]
    assert result[0]["content"] == msg.content


@pytest.mark.asyncio
async def test_retrieve_memories() -> None:
    """Test retrieving memories based on query."""
    memory = Mem0LongTermMemory(
        agent_name="Friday",
        user_name="test_user",
        model=ReActAgent.model_class(
            model_name="qwen-max-latest",
            api_key=DASHSCOPE_API_KEY,
        ),
        embedding_model=ReActAgent.embedding_class(
            model_name="text-embedding-v2",
            api_key=DASHSCOPE_API_KEY,
        ),
        on_disk=False,
    )

    # 预先记录一条记忆
    await memory.record(
        msgs=[
            Msg(
                role="user",
                content="I prefer temperatures in Celsius",
                name="user",
            )
        ],
    )

    # 检索相关记忆
    query_msg = Msg(
        role="user",
        content="What's the temperature unit?",
        name="user",
    )
    results = await memory.retrieve(msg=[query_msg])

    # 验证检索结果
    assert len(results) >= 1
    assert any("Celsius" in item["content"] for item in results)


@pytest.mark.asyncio
async def test_react_agent_with_long_term_memory() -> None:
    """Test ReActAgent integration with long-term memory."""
    agent = ReActAgent(
        name="Friday",
        sys_prompt="You are a helpful assistant.",
        model=ReActAgent.model_class(
            model_name="qwen-max-latest",
            api_key=DASHSCOPE_API_KEY,
        ),
        toolkit=ReActAgent.toolkit_class(),  # 假设 Toolkit 有默认实现
        memory=ReActAgent.memory_class(),  # 假设 InMemoryMemory 有默认实现
        long_term_memory=Mem0LongTermMemory(
            agent_name="Friday",
            user_name="test_user",
            model=ReActAgent.model_class(
                model_name="qwen-max-latest",
                api_key=DASHSCOPE_API_KEY,
            ),
            embedding_model=ReActAgent.embedding_class(
                model_name="text-embedding-v2",
                api_key=DASHSCOPE_API_KEY,
            ),
            on_disk=False,
        ),
        long_term_memory_mode="both",
    )

    # 记录用户偏好
    preference_msg = Msg(
        role="user",
        content="I prefer temperatures in Celsius and wind speed in km/h",
        name="user",
    )
    response = await agent(preference_msg)

    # 验证响应包含确认信息
    assert "recorded" in response.get_text_content().lower() or "saved" in response.get_text_content().lower()

    # 查询用户偏好
    query_msg = Msg(
        role="user",
        content="What preference do I have?",
        name="user",
    )
    response = await agent(query_msg)

    # 验证响应包含用户偏好
    assert "Celsius" in response.get_text_content()
    assert "km/h" in response.get_text_content()