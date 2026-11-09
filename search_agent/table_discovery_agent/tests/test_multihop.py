# -*- coding: utf-8 -*-
"""Exercise a multi-hop discovery query through the CLI offline."""

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

_QUERY = (
    "Start with revenue, follow store_id and then region_id, "
    "and find population between 30000 and 40000."
)
_CONSTRAINTS = [
    {"col_name": "revenue", "col_type": "Numerical", "values": []},
    {"col_name": "store_id", "col_type": "Categorical", "values": []},
    {"col_name": "region_id", "col_type": "Categorical", "values": []},
    {
        "col_name": "population",
        "col_type": "Numerical",
        "values": [30000, 40000],
    },
]
_ACTIONS = (
    (
        "metadata_seeker",
        {"column_names": ["revenue"], "column_types": ["Numerical"]},
    ),
    ("join_search", {"src_node_id": "1", "join_column_name": "store_id"}),
    ("join_search", {"src_node_id": "2", "join_column_name": "region_id"}),
    (
        "range_ranker",
        {
            "src_node_id": "3",
            "column_name": "population",
            "min_val": 30000,
            "max_val": 40000,
        },
    ),
    ("end_search", {}),
)


class _ColumnNameEncoder:
    """Give each distinct name its own embedding dimension."""

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 64), dtype=np.float32)
        for row, text in enumerate(texts):
            name = text.partition("|")[0].removeprefix("Column:")
            name = " ".join(name.casefold().replace("_", " ").split())
            position = self._positions.setdefault(name, len(self._positions))
            vectors[row, position] = 1.0
        return vectors


class _ScriptedModel(ChatModelBase):
    """Supply the five planned actions and record each planner's context."""

    def __init__(self) -> None:
        super().__init__(model_name="scripted", stream=False)
        self.choices: list[str | None] = []
        self.plans: list[tuple[str, set[str]]] = []

    async def __call__(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
    ) -> ChatResponse:
        self.choices.append(tool_choice)
        if tool_choice == "auto":
            step = len(self.plans)
            self.plans.append(
                (
                    messages[-1]["content"],
                    {tool["function"]["name"] for tool in tools or ()},
                )
            )
            if step >= len(_ACTIONS):
                raise AssertionError("Unexpected extra planning round")
            name, inputs = _ACTIONS[step]
            return ChatResponse(
                content=[
                    ToolUseBlock(
                        type="tool_use",
                        id=f"action-{step}",
                        name=name,
                        input=inputs,
                    )
                ]
            )

        value = (
            _CONSTRAINTS
            if tool_choice is None
            else {"directions": [], "stuck": []}
        )
        return ChatResponse(
            content=[TextBlock(type="text", text=json.dumps(value))]
        )


def _section(prompt: str, title: str) -> str:
    return prompt.split(f"## {title}\n", 1)[1].split("\n\n", 1)[0]


class MultihopDiscoveryTest(unittest.TestCase):
    def test_cli_follows_two_joins_and_ranks_the_endpoint(self) -> None:
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
                return_value=_ColumnNameEncoder(),
            ),
            redirect_stdout(output),
        ):
            main()

        self.assertEqual(model.choices, [None] + ["none", "auto"] * 5)
        expected_tables = (
            None,
            "store_sales",
            "store_directory",
            "region_demographics",
            "region_demographics",
        )
        for step, ((prompt, tools), table) in enumerate(
            zip(model.plans, expected_tables, strict=True)
        ):
            with self.subTest(round=step + 1):
                self.assertEqual(_section(prompt, "Current Node"), str(step))
                self.assertIn(_ACTIONS[step][0], tools)
                held = json.loads(_section(prompt, "Held Candidate Tables"))
                if table is None:
                    self.assertEqual(held, [])
                else:
                    self.assertIn(table, {match["table_id"] for match in held})
                trajectory = json.loads(_section(prompt, "Current Trajectory"))
                self.assertEqual(
                    [
                        (action["tool"], action["input"])
                        for action in trajectory
                    ],
                    list(_ACTIONS[:step]),
                )
                for action in trajectory:
                    self.assertNotIn("error", action)
                    self.assertGreater(action["matches"], 0)

        self.assertEqual(
            json.loads(_section(model.plans[-1][0], "Unresolved Constraints")),
            [],
        )
        self.assertEqual(
            output.getvalue().strip(), "region_demographics.population"
        )


if __name__ == "__main__":
    unittest.main()
