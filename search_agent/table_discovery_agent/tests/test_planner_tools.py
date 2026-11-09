# -*- coding: utf-8 -*-
"""Exercise planner tools against a small in-memory lake without a model."""

import unittest
from collections.abc import Sequence
from unittest.mock import create_autospec

import numpy as np
import pandas as pd
from agentscope.message import ToolUseBlock
from agentscope.tool import Toolkit

from agent import create_planner_toolkit, execute_round
from discovery import DiscoveryState
from indexing import (
    ColumnIndex,
    ColumnMatch,
    ColumnRepresentation,
    build_column_statistics,
    format_columns,
)
from indexing.column_matcher import ColumnNameMatcher
from tools.combiner import Match
from tools.composite_seeker import TableOperators

_TOOL_PARAMETERS = {
    "metadata_seeker": {"column_names", "column_types"},
    "join_search": {"src_node_id", "join_column_name"},
    "union_search": {"src_node_id", "union_column_names"},
    "eq_ranker": {"src_node_id", "column_name", "column_value"},
    "range_ranker": {"src_node_id", "column_name", "min_val", "max_val"},
    "correlation_search": {
        "src_node_id",
        "join_column_name",
        "src_corr_column_name",
    },
    "combine": {"node_id_1", "node_id_2", "set_op"},
    "end_search": set(),
}


class _Encoder:
    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 32), dtype=np.float32)
        for index, text in enumerate(texts):
            position = self._positions.setdefault(text, len(self._positions))
            vectors[index, position] = 1.0
        return vectors


def _call(name: str, **inputs: object) -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=name, name=name, input=inputs)


def _source(table_id: str, name: str) -> Match:
    return Match(
        table_id=table_id,
        column_name=name,
        column_type="Categorical",
        score=1.0,
    )


class PlannerToolsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.state = DiscoveryState()
        self.frames = {
            "source_a": pd.DataFrame({"area_key": ["a", "b", "c"]}),
            "source_b": pd.DataFrame({"Area Key": ["d", "e", "f"]}),
            "target_a": pd.DataFrame(
                {"Area Key": ["a", "b", "c"], "amount": [11, 12, 99]}
            ),
            "target_b": pd.DataFrame(
                {"area-key": ["d", "e", "f"], "amount": [13, 99, 99]}
            ),
        }
        self.columns = {
            (column.table_id, column.column_name): column
            for column in format_columns(self.frames)
        }
        self.index = create_autospec(ColumnIndex, instance=True)
        self.index.get_column.side_effect = self._get_column
        self.index.search.side_effect = self._search
        self.statistics = build_column_statistics(self.frames)
        self.matcher = ColumnNameMatcher(_Encoder())
        self.operators = self._operators()

    def _get_column(
        self, table_id: str, column_name: str
    ) -> ColumnRepresentation:
        return self.columns[table_id, column_name]

    def _search(
        self, query: str, channel: str = "metadata", top_k: int = 5
    ) -> tuple[ColumnMatch, ...]:
        if channel == "metadata":
            matches = (
                ColumnMatch("source_a", "area_key", "Categorical", 0.9),
                ColumnMatch("source_b", "Area Key", "Categorical", 0.8),
            )
        elif query == self.columns["source_a", "area_key"].content:
            matches = (
                ColumnMatch("source_a", "area_key", "Categorical", 1.0),
                ColumnMatch("target_a", "Area Key", "Categorical", 0.9),
            )
        elif query == self.columns["source_b", "Area Key"].content:
            matches = (
                ColumnMatch("source_b", "Area Key", "Categorical", 1.0),
                ColumnMatch("target_b", "area-key", "Categorical", 0.9),
            )
        else:
            self.fail(f"Unexpected {channel} query: {query}")
        return matches[:top_k]

    def _operators(self, result_cap: int = 256) -> TableOperators:
        return TableOperators(
            self.index,
            self.frames,
            self.statistics,
            self.matcher,
            result_cap=result_cap,
        )

    def _toolkit(self, node_id: str) -> Toolkit:
        return create_planner_toolkit(self.state, node_id, self.operators)

    async def _run(self, parent_id: str, name: str, **inputs: object) -> str:
        (node_id,) = await execute_round(
            self.state,
            self._toolkit(parent_id),
            parent_id,
            [_call(name, **inputs)],
        )
        return node_id

    def _add_source(self, parent_id: str, table_id: str, column: str) -> str:
        return self.state.add_child(
            parent_id,
            "seed",
            {"table_id": table_id},
            [_source(table_id, column)],
        )

    def _metadata_inputs(self) -> dict[str, list[str]]:
        return {
            "column_names": ["area_key"],
            "column_types": ["Categorical"],
        }

    def test_planner_schemas_expose_only_query_and_node_parameters(
        self,
    ) -> None:
        populated = self._add_source("0", "source_a", "area_key")
        for node_id in ("0", populated):
            with self.subTest(node_id=node_id):
                schemas = {
                    schema["function"]["name"]: set(
                        schema["function"]
                        .get("parameters", {})
                        .get("properties", {})
                    )
                    for schema in self._toolkit(node_id).get_json_schemas()
                }
                expected = dict(_TOOL_PARAMETERS)
                if node_id == populated:
                    del expected["metadata_seeker"]
                self.assertEqual(schemas, expected)

    async def test_metadata_join_range_and_end(self) -> None:
        seeded = await self._run(
            "0", "metadata_seeker", **self._metadata_inputs()
        )
        self.assertEqual(
            {match["table_id"] for match in self.state.get_matches(seeded)},
            {"source_a", "source_b"},
        )
        joined = await self._run(
            seeded,
            "join_search",
            src_node_id=seeded,
            join_column_name="area_key",
        )
        joined_tables = {
            match["table_id"] for match in self.state.get_matches(joined)
        }
        self.assertTrue({"target_a", "target_b"} <= joined_tables)

        ranked = await self._run(
            joined,
            "range_ranker",
            src_node_id=joined,
            column_name="amount",
            min_val=10,
            max_val=15,
        )
        matches = self.state.get_matches(ranked)
        self.assertEqual(
            [match["table_id"] for match in matches], ["target_a", "target_b"]
        )
        self.assertAlmostEqual(matches[0]["score"], 2 / 3)
        self.assertAlmostEqual(matches[1]["score"], 1 / 3)

        ended = await self._run(ranked, "end_search")
        self.assertTrue(self.state.get_node(ended)["terminated"])
        self.assertEqual(self.state.get_matches(ended), matches)

    async def test_ancestor_sources_and_cross_branch_combination(self) -> None:
        ancestor = self._add_source("0", "source_a", "area_key")
        selected = self._add_source(ancestor, "source_a", "area_key")
        sibling = self._add_source(ancestor, "source_b", "Area Key")

        accepted = await self._run(
            selected,
            "join_search",
            src_node_id=ancestor,
            join_column_name="area_key",
        )
        self.assertIn(
            "target_a",
            {match["table_id"] for match in self.state.get_matches(accepted)},
        )

        blocked = await self._run(
            selected,
            "join_search",
            src_node_id=sibling,
            join_column_name="area_key",
        )
        self.assertTrue(self.state.get_node(blocked)["error"])
        self.assertEqual(self.state.get_matches(blocked), [])

        combined = await self._run(
            selected,
            "combine",
            node_id_1=selected,
            node_id_2=sibling,
            set_op="union",
        )
        self.assertEqual(
            {match["table_id"] for match in self.state.get_matches(combined)},
            {"source_a", "source_b"},
        )

    async def test_rejects_unknown_and_failed_references(self) -> None:
        selected = self._add_source("0", "source_a", "area_key")
        failed = self.state.add_child(
            "0", "seed", {}, [], error="previous tool failure"
        )
        unknown = await self._run(
            selected,
            "join_search",
            src_node_id="999",
            join_column_name="area_key",
        )
        self.assertTrue(self.state.get_node(unknown)["error"])
        combined = await self._run(
            selected,
            "combine",
            node_id_1=selected,
            node_id_2=failed,
            set_op="union",
        )
        self.assertTrue(self.state.get_node(combined)["error"])

    async def test_metadata_result_cap(self) -> None:
        self.operators = self._operators(result_cap=1)
        seeded = await self._run(
            "0", "metadata_seeker", **self._metadata_inputs()
        )
        (match,) = self.state.get_matches(seeded)
        self.assertEqual(match["table_id"], "source_a")


if __name__ == "__main__":
    unittest.main()
