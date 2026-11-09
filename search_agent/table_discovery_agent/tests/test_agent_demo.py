# -*- coding: utf-8 -*-
"""Exercise the agent's column search without calling a model service."""

import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from agentscope.formatter import DeepSeekChatFormatter
from agentscope.message import Msg, TextBlock, ToolUseBlock
from agentscope.model import ChatModelBase, ChatResponse

from agent import create_agent
from data_lake import load_data_lake, read_table
from indexing import ColumnIndex, format_columns

_TOOL_CALL_ID = "seek-population"
_EXPECTED_COLUMN = "region_demographics.population"
_FINAL_TEXT = f"The population column is {_EXPECTED_COLUMN}."


class _PopulationEncoder:
    """Place texts that mention population on the same unit vector."""

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return two-dimensional unit embeddings."""
        return np.array(
            [
                (1.0, 0.0) if "population" in text.casefold() else (0.0, 1.0)
                for text in texts
            ],
            dtype=np.float32,
        )


class _ScriptedModel(ChatModelBase):
    """Request a column search, then record the context for the answer."""

    def __init__(self) -> None:
        super().__init__(model_name="scripted", stream=False)
        self.requests: list[list[dict[str, Any]]] = []

    async def __call__(
        self,
        messages: list[dict[str, Any]],
        **_kwargs: Any,
    ) -> ChatResponse:
        """Emit a tool call on the first turn and text on the next."""
        self.requests.append(messages)
        if len(self.requests) == 1:
            return ChatResponse(
                content=[
                    ToolUseBlock(
                        type="tool_use",
                        id=_TOOL_CALL_ID,
                        name="seek_columns",
                        input={
                            "query": "population",
                            "channel": "metadata",
                            "top_k": 1,
                        },
                    ),
                ],
            )
        result = next(
            (
                message["content"]
                for message in messages
                if message["role"] == "tool"
                and message.get("tool_call_id") == _TOOL_CALL_ID
            ),
            "",
        )
        if _EXPECTED_COLUMN not in str(result):
            raise AssertionError(f"Expected {_EXPECTED_COLUMN} in {result!r}")
        return ChatResponse(
            content=[TextBlock(type="text", text=_FINAL_TEXT)],
        )


class AgentDemoTest(unittest.IsolatedAsyncioTestCase):
    """Verify that the agent gives the seeker result to its model."""

    async def test_seeker_result_reaches_model(self) -> None:
        """Run a real index search over the bundled demo CSVs."""
        lake = Path(__file__).resolve().parents[1] / "data" / "demo_lake"
        frames = {
            table.id: read_table(table) for table in load_data_lake(lake)
        }
        index = ColumnIndex(format_columns(frames), _PopulationEncoder())
        model = _ScriptedModel()
        agent = create_agent(index, model, DeepSeekChatFormatter())

        reply = await agent(
            Msg(
                name="user",
                role="user",
                content="Find the column that contains regional population.",
            ),
        )

        self.assertEqual(len(model.requests), 2)
        self.assertFalse(
            any(message["role"] == "tool" for message in model.requests[0]),
        )
        tool_messages = [
            message
            for message in model.requests[1]
            if message["role"] == "tool"
            and message.get("tool_call_id") == _TOOL_CALL_ID
        ]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn(
            _EXPECTED_COLUMN,
            str(tool_messages[0]["content"]),
        )
        self.assertEqual(reply.get_text_content(), _FINAL_TEXT)
