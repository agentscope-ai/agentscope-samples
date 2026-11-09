# -*- coding: utf-8 -*-
"""Check query constraints and their use in discovery execution."""

import unittest
from collections.abc import Sequence

import numpy as np
import pandas as pd
from agentscope.formatter import DeepSeekChatFormatter
from agentscope.message import TextBlock, ToolUseBlock
from agentscope.model import ChatModelBase, ChatResponse

from agent import execute_round
from indexing import ColumnIndex, build_column_statistics, format_columns
from indexing.column_matcher import ColumnNameMatcher
from discovery import DiscoveryState
from discovery.constraints import (
    QueryConstraint,
    extract_constraints,
    rank_results,
    resolve_constraints,
    satisfies,
)
from tools import create_toolkit
from tools.combiner import Match


class _Encoder:
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(
            [
                [1.0, 0.0] if "population" in t.lower() else [0.0, 1.0]
                for t in texts
            ],
            dtype=np.float32,
        )


class _ScriptedModel(ChatModelBase):
    def __init__(self, *, always_invalid: bool = False) -> None:
        super().__init__(model_name="scripted", stream=False)
        self.always_invalid = always_invalid
        self.requests: list[list[dict]] = []

    async def __call__(
        self, messages: list[dict], **_kwargs: object
    ) -> ChatResponse:
        self.requests.append(messages)
        if self.always_invalid:
            text = "invalid response"
        elif len(self.requests) == 1:
            text = (
                '[{"col_name":"population","col_type":"Numerical",'
                '"values":[30000,30000]}]'
            )
        else:
            text = (
                '[{"col_name":"population","col_type":"Numerical",'
                '"values":[30000,null]},'
                '{"col_name":"income","col_type":"Numerical",'
                '"values":[null,null]}]'
            )
        return ChatResponse(content=[TextBlock(type="text", text=text)])


def _call(name: str, **inputs: object) -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=name, name=name, input=inputs)


def _match(table_id: str, score: float) -> Match:
    return Match(
        table_id=table_id,
        column_name="population",
        column_type="Numerical",
        score=score,
    )


class ConstraintsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.encoder = _Encoder()
        self.matcher = ColumnNameMatcher(self.encoder)
        self.value: QueryConstraint = {
            "col_name": "population",
            "col_type": "Numerical",
            "values": [30000, 40000],
        }
        self.presence: QueryConstraint = {
            "col_name": "population",
            "col_type": "Numerical",
            "values": [],
        }
        self.frames = {
            "half": pd.DataFrame({"population": [30000, 45000]}),
            "one_third": pd.DataFrame({"population": [40000, 45000, 50000]}),
            "outside": pd.DataFrame({"population": [45000]}),
        }

    async def test_extract_retries_and_normalizes_bounds(self) -> None:
        model = _ScriptedModel()
        constraints = await extract_constraints(
            "Find population data",
            ["population"],
            model,
            DeepSeekChatFormatter(),
        )
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(constraints[0]["values"], [30000, None])
        self.assertEqual(constraints[1]["values"], [])

    async def test_extraction_reports_failure_after_three_attempts(
        self,
    ) -> None:
        model = _ScriptedModel(always_invalid=True)
        with self.assertRaises(RuntimeError):
            await extract_constraints(
                "Find population data", [], model, DeepSeekChatFormatter()
            )
        self.assertEqual(len(model.requests), 3)

    def test_exact_value_checks(self) -> None:
        self.assertTrue(
            satisfies(self.value, self.frames["one_third"], self.matcher)
        )
        self.assertFalse(
            satisfies(
                self.value,
                self.frames["one_third"],
                self.matcher,
                numerical_threshold=0.5,
            )
        )
        self.assertTrue(
            satisfies(
                self.value,
                self.frames["half"],
                self.matcher,
                numerical_threshold=0.5,
            )
        )
        category: QueryConstraint = {
            "col_name": "region",
            "col_type": "Categorical",
            "values": ["SG", "US"],
        }
        self.assertFalse(
            satisfies(category, pd.DataFrame({"region": ["SG"]}), self.matcher)
        )
        self.assertTrue(
            satisfies(
                category, pd.DataFrame({"region": ["SG", "US"]}), self.matcher
            )
        )

    async def test_execution_updates_siblings_independently(self) -> None:
        frames = {"half": self.frames["half"]}
        index = ColumnIndex(format_columns(frames), self.encoder)
        toolkit = create_toolkit(
            index, statistics=build_column_statistics(frames)
        )
        state = DiscoveryState(initial_constraints=[self.presence, self.value])

        def resolve(constraints, name, inputs, matches):
            return resolve_constraints(
                constraints, name, inputs, matches, frames, self.matcher
            )

        (child,) = await execute_round(
            state,
            toolkit,
            "0",
            [_call("seek_columns", query="population", top_k=1)],
            resolve=resolve,
        )
        self.assertEqual(state.get_node(child)["constraints"], [self.value])
        ended, ranked = await execute_round(
            state,
            toolkit,
            child,
            [
                _call("end_search"),
                _call(
                    "rank_range",
                    candidates=state.get_matches(child),
                    lower=30000,
                    upper=40000,
                ),
            ],
            resolve=resolve,
        )
        self.assertEqual(state.get_node(ended)["constraints"], [self.value])
        self.assertEqual(state.get_node(ranked)["constraints"], [])
        self.assertEqual(state.get_node(child)["constraints"], [self.value])
        self.assertEqual(
            state.get_initial_constraints(), [self.presence, self.value]
        )
        self.assertEqual(state.get_matches(ranked)[0]["score"], 0.5)

    def test_top_three_and_final_filter(self) -> None:
        frames = {
            **self.frames,
            "outside_2": self.frames["outside"],
            "outside_3": self.frames["outside"],
        }
        matches = [
            _match("outside", 0.9),
            _match("outside_2", 0.8),
            _match("outside_3", 0.7),
            _match("half", 0.6),
        ]
        self.assertEqual(
            resolve_constraints(
                [self.value],
                "range_ranker",
                {"column_name": "population"},
                matches,
                frames,
                self.matcher,
            ),
            [self.value],
        )
        ranked = rank_results(
            [*matches, _match("one_third", 0.5)],
            [self.value],
            frames,
            self.matcher,
        )
        self.assertEqual(
            [match["table_id"] for match in ranked], ["half", "one_third"]
        )
        self.assertEqual(
            rank_results(matches[:3], [self.value], frames, self.matcher),
            matches[:3],
        )

        ranked = rank_results(
            matches, [self.presence, self.value], frames, self.matcher
        )
        self.assertEqual(ranked[0]["table_id"], "half")
