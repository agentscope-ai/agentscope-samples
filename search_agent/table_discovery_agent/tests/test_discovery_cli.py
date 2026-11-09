# -*- coding: utf-8 -*-
"""Exercise the discovery CLI with a scripted model and real tools."""

import json
import unittest
from collections.abc import Sequence
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
from agentscope.message import TextBlock, ToolUseBlock
from agentscope.model import ChatModelBase, ChatResponse

from main import main

_QUERY = "Find tables with population data"
_TABLE = "region_demographics"
_CONSTRAINT = {
    "col_name": "population",
    "col_type": "Numerical",
    "values": [],
}


class _PopulationEncoder:
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.array(
            [
                (1.0, 0.0) if "population" in text.casefold() else (0.0, 1.0)
                for text in texts
            ],
            dtype=np.float32,
        )


def _text_response(value: object) -> ChatResponse:
    return ChatResponse(
        content=[TextBlock(type="text", text=json.dumps(value))]
    )


def _tool_response(name: str, **inputs: object) -> ChatResponse:
    return ChatResponse(
        content=[
            ToolUseBlock(type="tool_use", id=name, name=name, input=inputs)
        ]
    )


class _ScriptedModel(ChatModelBase):
    """Record the model inputs while driving two discovery rounds."""

    def __init__(self) -> None:
        super().__init__(model_name="scripted", stream=False)
        self.requests: list[tuple[str, set[str], str | None]] = []

    async def __call__(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
    ) -> ChatResponse:
        names = {tool["function"]["name"] for tool in tools or ()}
        self.requests.append((messages[-1]["content"], names, tool_choice))
        turn = len(self.requests)
        if turn == 1:
            return _text_response([_CONSTRAINT])
        if turn in (2, 4):
            return _text_response(
                {
                    "directions": [{"id": f"observation-{turn}"}],
                    "stuck": [],
                }
            )
        if turn == 3:
            return _tool_response(
                "metadata_seeker",
                column_names=["population"],
                column_types=["Numerical"],
            )
        if turn == 5:
            return _tool_response("end_search")
        raise AssertionError(f"Unexpected model turn {turn}")


class DiscoveryCliTest(unittest.TestCase):
    def test_ask_runs_observation_and_planning_until_search_ends(self) -> None:
        lake = Path(__file__).resolve().parents[1] / "data" / "demo_lake"
        model = _ScriptedModel()
        output = StringIO()
        argv = [
            "main.py",
            "--lake",
            str(lake),
            "--embedding-model",
            "unused",
            "--ask",
            _QUERY,
        ]
        with (
            patch("sys.argv", argv),
            patch.dict("os.environ", {"DEEPSEEK_API_KEY": "unused"}),
            patch("agent.OpenAIChatModel", return_value=model),
            patch(
                "indexing.embedding.create_encoder",
                return_value=_PopulationEncoder(),
            ),
            redirect_stdout(output),
        ):
            main()

        self.assertEqual(len(model.requests), 5)
        (
            constraints,
            first_observation,
            first_plan,
            next_observation,
            next_plan,
        ) = model.requests
        self.assertIn(_QUERY, constraints[0])
        self.assertEqual(
            [choice for _, _, choice in model.requests],
            [None, "none", "auto", "none", "auto"],
        )
        self.assertEqual(first_observation[1], set())
        self.assertIn("## Held Candidate Tables\n[]", first_observation[0])
        self.assertIn("metadata_seeker", first_plan[1])
        self.assertIn("observation-2", first_plan[0])
        self.assertEqual(next_observation[1], set())
        self.assertIn(
            f'## Held Candidate Tables\n["{_TABLE}"]', next_observation[0]
        )
        self.assertIn("observation-4", next_plan[0])
        self.assertIn(f'"table_id": "{_TABLE}"', next_plan[0])
        self.assertIn('"tool": "metadata_seeker"', next_plan[0])
        self.assertIn("end_search", next_plan[1])
        self.assertNotIn("metadata_seeker", next_plan[1])
        self.assertEqual(output.getvalue().strip(), f"{_TABLE}.population")


if __name__ == "__main__":
    unittest.main()
