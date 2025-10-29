# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from agentscope.message import Msg

# Import module under test
from functionality.structured_output import main


@pytest.mark.asyncio
async def test_table_model_output() -> None:
    """Verify structured output conforms to TableModel"""
    # Mock model response
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
        # Initialize Agent
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

        # Execute query
        query_msg = main.Msg(
            "user",
            "Please introduce Einstein",
            "user",
        )
        result = await agent(query_msg, structured_model=main.TableModel)

        # Verify output
        assert result.metadata == mock_model_response
        assert isinstance(result.metadata, dict)
        assert "name" in result.metadata
        assert result.metadata["name"] == "Albert Einstein"


@pytest.mark.asyncio
async def test_choice_model_output() -> None:
    """Verify structured output conforms to ChoiceModel"""
    # Mock model response
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
        # Initialize Agent
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

        # Execute query
        query_msg = main.Msg(
            "user",
            "Choose one of your favorite fruit",
            "user",
        )
        result = await agent(query_msg, structured_model=main.ChoiceModel)

        # Verify output
        assert result.metadata == mock_model_response
        assert result.metadata["choice"] in ["apple", "banana", "orange"]