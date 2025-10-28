# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from agentscope.message import Msg

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测模块
from functionality.structured_output import main


@pytest.mark.asyncio
async def test_table_model_output() -> None:
    """验证结构化输出符合 TableModel"""
    # Mock 模型响应
    mock_model_response = {
        "name": "Albert Einstein",
        "age": 143,
        "intro": "Theoretical physicist known for the theory of relativity.",
        "honors": ["Nobel Prize in Physics", "Time Person of the Century"],
    }

    # Patch DashScopeChatModel.get_response
    with patch(
        "structured_output.main.DashScopeChatModel.get_response",
        AsyncMock(
            return_value=Msg(
                "assistant",
                "",
                "Friday",
                metadata=mock_model_response,
            ),
        ),
    ):
        # 初始化 Agent
        toolkit = main.Toolkit()
        agent = main.ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=main.DashScopeChatModel(
                api_key=os.environ["DASHSCOPE_API_KEY"],
                model_name="qwen-max",
                stream=True,
            ),
            formatter=main.DashScopeChatFormatter(),
            toolkit=toolkit,
            memory=main.InMemoryMemory(),
        )

        # 执行查询
        query_msg = main.Msg(
            "user",
            "Please introduce Einstein",
            "user",
        )
        result = await agent(query_msg, structured_model=main.TableModel)

        # 验证输出
        assert result.metadata == mock_model_response
        assert isinstance(result.metadata, dict)
        assert "name" in result.metadata
        assert result.metadata["name"] == "Albert Einstein"


@pytest.mark.asyncio
async def test_choice_model_output() -> None:
    """验证结构化输出符合 ChoiceModel"""
    # Mock 模型响应
    mock_model_response = {"choice": "apple"}

    # Patch DashScopeChatModel.get_response
    with patch(
        "structured_output.main.DashScopeChatModel.get_response",
        AsyncMock(
            return_value=Msg(
                "assistant",
                "",
                "Friday",
                metadata=mock_model_response,
            ),
        ),
    ):
        # 初始化 Agent
        toolkit = main.Toolkit()
        agent = main.ReActAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=main.DashScopeChatModel(
                api_key=os.environ["DASHSCOPE_API_KEY"],
                model_name="qwen-max",
                stream=True,
            ),
            formatter=main.DashScopeChatFormatter(),
            toolkit=toolkit,
            memory=main.InMemoryMemory(),
        )

        # 执行查询
        query_msg = main.Msg(
            "user",
            "Choose one of your favorite fruit",
            "user",
        )
        result = await agent(query_msg, structured_model=main.ChoiceModel)

        # 验证输出
        assert result.metadata == mock_model_response
        assert result.metadata["choice"] in ["apple", "banana", "orange"]
