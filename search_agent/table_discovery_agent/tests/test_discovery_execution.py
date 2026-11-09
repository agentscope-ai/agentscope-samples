# -*- coding: utf-8 -*-
"""Test discovery tool execution and tree collection without a model."""

import json
import unittest

from agentscope.message import TextBlock, ToolUseBlock
from agentscope.tool import Toolkit, ToolResponse

from agent import execute_round
from discovery import DiscoveryState
from tools.combiner import Match
from tools.termination import end_search


def _call(call_id: str, name: str, **inputs: object) -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=call_id, name=name, input=inputs)


def _match(table: str, score: float, column: str = "value") -> Match:
    return Match(
        table_id=table,
        column_name=column,
        column_type="numeric",
        score=score,
    )


class DiscoveryExecutionTest(unittest.IsolatedAsyncioTestCase):
    """Exercise branch behavior using a real AgentScope toolkit."""

    def setUp(self) -> None:
        """Register discovery tools with scripted responses."""
        self.toolkit = Toolkit()
        self.toolkit.register_tool_function(end_search)
        self.results: dict[str, list[Match]] = {}
        self.queries: list[str] = []

        def search(query: str, top_k: int = 5) -> ToolResponse:
            """Return the scripted matches for a query.

            Args:
                query: Name of the scripted result.
                top_k: Maximum number of matches.
            """
            self.queries.append(query)
            return ToolResponse(
                content=[],
                metadata={"matches": self.results[query][:top_k]},
            )

        self.toolkit.register_tool_function(search)

    async def test_end_search_only_terminates_its_child(self) -> None:
        """A sibling can keep searching after the other sibling ends."""
        seed = [_match("seed", 1)]
        self.results.update(first=[_match("first", 1)], next=seed)
        state = DiscoveryState(seed_matches=seed)

        ended, opened = await execute_round(
            state,
            self.toolkit,
            "0",
            [_call("end", "end_search"), _call("a", "search", query="first")],
        )

        self.assertFalse(state.get_node("0")["ended"])
        self.assertEqual(state.get_node(ended)["parent_id"], "0")
        self.assertTrue(state.get_node(ended)["ended"])
        self.assertTrue(state.get_node(ended)["terminated"])
        self.assertEqual(state.get_matches(ended), seed)
        self.assertEqual(state.get_node(opened)["parent_id"], "0")
        self.assertFalse(state.get_node(opened)["ended"])
        self.assertFalse(state.get_node(opened)["terminated"])
        self.assertEqual(state.get_matches(opened), self.results["first"])

        self.assertEqual(
            await execute_round(
                state, self.toolkit, ended, [_call("end-again", "end_search")]
            ),
            [],
        )
        self.assertEqual(
            await execute_round(
                state,
                self.toolkit,
                opened,
                [_call("seed-again", "seek_columns", query="first")],
            ),
            [],
        )

        (child,) = await execute_round(
            state, self.toolkit, opened, [_call("b", "search", query="next")]
        )
        self.assertEqual(state.get_node(child)["parent_id"], opened)
        self.assertEqual(state.get_matches(child), seed)

    async def test_skips_repeated_successes_across_branches(self) -> None:
        """Deduplicate successful tool inputs globally, except end_search."""
        self.results.update(
            left=[_match("left", 1)], right=[_match("right", 1)]
        )
        self.results["shared"] = [_match("shared", 1)]
        state = DiscoveryState()
        left, right = await execute_round(
            state,
            self.toolkit,
            "0",
            [
                _call("l", "search", query="left"),
                _call("r", "search", query="right"),
            ],
        )

        shared, left_end = await execute_round(
            state,
            self.toolkit,
            left,
            [
                _call("a", "search", query="shared", top_k=1),
                _call("b", "search", top_k=1, query="shared"),
                _call("end-l", "end_search"),
            ],
        )
        (right_end,) = await execute_round(
            state,
            self.toolkit,
            right,
            [
                _call("c", "search", top_k=1, query="shared"),
                _call("end-r", "end_search"),
            ],
        )
        self.assertEqual(self.queries, ["left", "right", "shared"])
        self.assertEqual(state.get_matches(shared), self.results["shared"])
        self.assertTrue(state.get_node(left_end)["terminated"])
        self.assertTrue(state.get_node(right_end)["terminated"])
        self.assertEqual(state.get_matches(left_end), self.results["left"])
        self.assertEqual(state.get_matches(right_end), self.results["right"])

    async def test_tool_errors_are_recorded_and_retryable(self) -> None:
        """Handle explicit tool errors and exceptions wrapped by Toolkit."""
        responses: list[ToolResponse | Exception] = []

        def recover() -> ToolResponse:
            """Return or raise the next scripted outcome."""
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        toolkit = Toolkit()
        toolkit.register_tool_function(recover)
        explicit_error = ToolResponse(
            content=[TextBlock(type="text", text="failed")],
            metadata={"error": "scripted failure"},
        )
        recovered = ToolResponse(
            content=[], metadata={"matches": [_match("fixed", 1)]}
        )
        for failure in (explicit_error, ValueError("scripted failure")):
            with self.subTest(failure=type(failure).__name__):
                state = DiscoveryState()
                responses[:] = [failure, recovered]
                failed, fixed = await execute_round(
                    state,
                    toolkit,
                    "0",
                    [
                        _call("try", "recover"),
                        _call("retry", "recover"),
                        _call("skip", "recover"),
                    ],
                )
                self.assertEqual(responses, [])
                self.assertTrue(state.get_node(failed)["ended"])
                self.assertFalse(state.get_node(failed)["terminated"])
                self.assertIn(
                    "scripted failure", state.get_node(failed)["error"] or ""
                )
                self.assertEqual(state.get_matches(failed), [])
                self.assertIsNone(state.get_node(fixed)["error"])
                self.assertEqual(
                    state.collect_candidates(), [_match("fixed", 1)]
                )

    async def test_empty_leaf_falls_back_without_using_root_seed(self) -> None:
        """Use the nearest candidate result from each valid non-root path."""
        self.results.update(
            empty=[],
            no_improvement=[],
            found=[_match("found", 0.5)],
            failed_branch=[_match("ignored", 1)],
        )
        state = DiscoveryState(seed_matches=[_match("seed", 1)])
        (empty,) = await execute_round(
            state, self.toolkit, "0", [_call("a", "search", query="empty")]
        )
        self.assertTrue(state.get_node(empty)["ended"])
        self.assertIsNone(state.get_node(empty)["error"])
        self.assertEqual(state.collect_candidates(), [])

        found, failed = await execute_round(
            state,
            self.toolkit,
            "0",
            [
                _call("b", "search", query="found"),
                _call("c", "search", query="failed_branch"),
            ],
        )
        await execute_round(
            state,
            self.toolkit,
            found,
            [_call("d", "search", query="no_improvement")],
        )
        await execute_round(
            state, self.toolkit, failed, [_call("e", "missing_tool")]
        )
        self.assertEqual(state.collect_candidates(), [_match("found", 1)])

    async def test_collects_open_and_terminated_leaves(self) -> None:
        """Keep the first column and max score after per-leaf normalization."""
        self.results["left"] = [
            _match("shared", 0.25, column="first"),
            _match("left", 0.5),
        ]
        self.results["right"] = [
            _match("shared", 0.375, column="second"),
            _match("right", 0.5),
        ]
        state = DiscoveryState()
        left, right = await execute_round(
            state,
            self.toolkit,
            "0",
            [
                _call("a", "search", query="left"),
                _call("b", "search", query="right"),
            ],
        )
        # Record the left termination before creating the other leaf so its
        # column is encountered first during collection.
        (ended,) = await execute_round(
            state, self.toolkit, left, [_call("end", "end_search")]
        )
        self.results["open"] = self.results["right"]
        (opened,) = await execute_round(
            state, self.toolkit, right, [_call("c", "search", query="open")]
        )
        self.assertTrue(state.get_node(ended)["terminated"])
        self.assertFalse(state.get_node(opened)["ended"])
        self.assertEqual(
            state.collect_candidates(),
            [
                _match("shared", 0.75, column="first"),
                _match("left", 1),
                _match("right", 1),
            ],
        )
        self.assertEqual(state.get_matches(ended), self.results["left"])
        self.assertEqual(state.get_matches(opened), self.results["right"])

    async def test_state_survives_a_json_round_trip(self) -> None:
        """Restore the tree and continue with the existing call history."""
        self.results["first"] = [_match("first", 1)]
        state = DiscoveryState(seed_matches=[_match("seed", 1)])
        (found,) = await execute_round(
            state, self.toolkit, "0", [_call("a", "search", query="first")]
        )
        snapshot = json.loads(json.dumps(state.state_dict()))
        restored = DiscoveryState()
        restored.load_state_dict(snapshot)

        self.assertEqual(restored.state_dict(), snapshot)
        self.assertEqual(
            restored.collect_candidates(), state.collect_candidates()
        )
        (ended,) = await execute_round(
            restored,
            self.toolkit,
            found,
            [
                _call("repeat", "search", query="first"),
                _call("end", "end_search"),
            ],
        )
        self.assertEqual(self.queries, ["first"])
        self.assertNotIn(ended, ("0", found))
        self.assertEqual(restored.get_node(ended)["parent_id"], found)
        self.assertTrue(restored.get_node(ended)["terminated"])


if __name__ == "__main__":
    unittest.main()
