# -*- coding: utf-8 -*-
"""Test relationship graph construction and observation offline."""

import unittest
from collections.abc import Sequence

import numpy as np
import pandas as pd

from agent import observe, select_paths
from indexing.column_formatter import ColumnRepresentation
from indexing.column_index import ColumnMatch
from discovery.relationship_graph import (
    RelationshipEdge,
    RelationshipPath,
    build_relationship_graph,
    find_paths,
)
from discovery.state import DiscoveryState
from tools.combiner import Match


class _Index:
    def __init__(
        self,
        frames: dict[str, pd.DataFrame],
        results: dict[str, tuple[ColumnMatch, ...]],
    ) -> None:
        self.columns = {
            (table, name): ColumnRepresentation(
                table,
                name,
                (
                    "Numerical"
                    if pd.api.types.is_numeric_dtype(column)
                    else "Categorical"
                ),
                f"{table}.{name} metadata",
                f"{table}.{name} content",
            )
            for table, frame in frames.items()
            for name, column in frame.items()
        }
        self.results = results

    def get_column(
        self, table_id: str, column_name: str
    ) -> ColumnRepresentation:
        return self.columns[table_id, column_name]

    def search(
        self, query: str, channel: str, top_k: int
    ) -> tuple[ColumnMatch, ...]:
        if channel != "content":
            raise AssertionError(
                "The relationship graph should search by content"
            )
        return self.results.get(query, ())[:top_k]


class _NameEncoder:
    def encode(self, names: Sequence[str]) -> np.ndarray:
        vectors = {
            "region key": [1.0, 0.0],
            "territory": [0.85, np.sqrt(1 - 0.85**2)],
        }
        return np.array(
            [vectors.get(name, [0.0, 1.0]) for name in names], dtype=np.float32
        )


def _match(table_id: str) -> Match:
    return Match(
        table_id=table_id,
        column_name="value",
        column_type="Numerical",
        score=1.0,
    )


class RelationshipGraphTest(unittest.TestCase):
    def test_union_weights_and_compatible_join_bridges(self) -> None:
        frames = {
            "seed": pd.DataFrame(
                {
                    "Region Key": ["us", "fr"],
                    "Sales": [1, 2],
                    "Segment": ["a", "b"],
                }
            ),
            "exact": pd.DataFrame(
                {
                    "region_key": ["us", "fr"],
                    "Price": [3, 4],
                    "segment": ["c", "d"],
                }
            ),
            "semantic": pd.DataFrame(
                {"territory": ["us", "gb"], "segment": ["a", "c"]}
            ),
            "unrelated": pd.DataFrame({"district": ["us", "fr"]}),
            "weak": pd.DataFrame({"region_key": ["us", "fr"]}),
        }
        index = _Index(
            frames,
            {
                "seed.Region Key content": (
                    ColumnMatch("seed", "Region Key", "Categorical", 1.0),
                    ColumnMatch("exact", "region_key", "Categorical", 0.9),
                    ColumnMatch("semantic", "territory", "Categorical", 0.8),
                    ColumnMatch("unrelated", "district", "Categorical", 0.5),
                    ColumnMatch("weak", "region_key", "Categorical", 0.49),
                ),
                "seed.Sales content": (
                    ColumnMatch("seed", "Sales", "Numerical", 1.0),
                    ColumnMatch("exact", "Price", "Numerical", 0.6),
                ),
                "seed.Segment content": (
                    ColumnMatch("seed", "Segment", "Categorical", 1.0),
                    ColumnMatch("semantic", "segment", "Categorical", 0.85),
                    ColumnMatch("exact", "segment", "Categorical", 0.75),
                ),
            },
        )

        graph = build_relationship_graph(index, frames, _NameEncoder())
        union = {
            edge.target: edge for edge in graph["seed"] if edge.kind == "union"
        }
        join = {
            edge.target: edge for edge in graph["seed"] if edge.kind == "join"
        }

        self.assertEqual(set(graph), set(frames))
        self.assertEqual(set(union), {"exact", "semantic", "unrelated"})
        # Per-column weights include the self hit in their denominator.
        union_weights = {
            "exact": 0.9 / 3.2 + 0.6 / 1.6 + 0.75 / 2.6,
            "semantic": 0.8 / 3.2 + 0.85 / 2.6,
            "unrelated": 0.5 / 3.2,
        }
        total = sum(union_weights.values())
        for target, weight in union_weights.items():
            self.assertAlmostEqual(union[target].score, weight / total)

        self.assertEqual(set(join), {"exact", "semantic"})
        # Region overlap shares are 3/4 and 1/4. Only semantic has any
        # Segment overlap, giving that bridge a share of 1.
        self.assertAlmostEqual(join["exact"].score, 3 / 7)
        self.assertAlmostEqual(join["semantic"].score, 4 / 7)
        self.assertEqual(join["exact"].columns, ("Region Key",))
        self.assertEqual(join["semantic"].columns, ("Segment", "Region Key"))

    def test_content_candidate_cap_counts_tables_before_removing_self(
        self,
    ) -> None:
        neighbors = [f"neighbor_{i}" for i in range(9)]
        frames = {
            table: pd.DataFrame({"value": [1], "other": [2]})
            for table in ["seed", *neighbors]
        }
        index = _Index(
            frames,
            {
                "seed.value content": (
                    ColumnMatch("seed", "value", "Numerical", 1.0),
                    ColumnMatch(neighbors[0], "value", "Numerical", 0.99),
                    ColumnMatch(neighbors[0], "other", "Numerical", 0.98),
                    *(
                        ColumnMatch(
                            table, "value", "Numerical", 0.95 - i * 0.01
                        )
                        for i, table in enumerate(neighbors[1:])
                    ),
                ),
            },
        )

        graph = build_relationship_graph(index, frames, _NameEncoder())

        self.assertEqual(
            [edge.target for edge in graph["seed"] if edge.kind == "union"],
            neighbors[:7],
        )


class ObservationTest(unittest.TestCase):
    def test_path_search_uses_weakest_edge_and_stops_at_first_target(
        self,
    ) -> None:
        graph = {
            "seed": (
                RelationshipEdge("left", "union", 0.95),
                RelationshipEdge("right", "join", 0.65),
                RelationshipEdge("chain1", "union", 0.95),
            ),
            "left": (
                RelationshipEdge("seed", "union", 0.99),
                RelationshipEdge("target", "join", 0.4),
            ),
            "right": (RelationshipEdge("target", "union", 0.6),),
            "target": (RelationshipEdge("beyond", "union", 0.99),),
            "chain1": (RelationshipEdge("chain2", "union", 0.95),),
            "chain2": (RelationshipEdge("chain3", "union", 0.95),),
            "chain3": (RelationshipEdge("beyond", "union", 0.95),),
        }
        targets = ("target", "beyond")

        self.assertEqual(find_paths(graph, ["seed"], targets, max_depth=1), [])
        paths: list[RelationshipPath] = find_paths(graph, ["seed"], targets)
        self.assertEqual(
            [path.tables for path in paths],
            [("seed", "right", "target"), ("seed", "left", "target")],
        )
        self.assertEqual([path.reliability for path in paths], [0.6, 0.4])
        self.assertEqual(
            find_paths(
                graph, ["seed"], targets, max_depth=4, path_pool_size=1
            )[0].tables,
            ("seed", "chain1", "chain2", "chain3", "beyond"),
        )

    def test_selection_recomputes_novelty_and_uses_reliability_for_ties(
        self,
    ) -> None:
        graph = {
            "seed": (
                RelationshipEdge("shared", "union", 1.0),
                RelationshipEdge("fresh", "union", 0.6),
                RelationshipEdge("last", "join", 0.5),
            ),
            "shared": (
                RelationshipEdge("target_a", "union", 0.9),
                RelationshipEdge("target_b", "union", 0.8),
            ),
            "fresh": (RelationshipEdge("target_c", "join", 0.8),),
        }
        paths = find_paths(
            graph, ["seed"], ("target_a", "target_b", "target_c", "last")
        )

        selected = select_paths(paths, {"seed"}, path_budget=3)

        self.assertEqual(
            [path.tables[-1] for path in selected],
            ["target_a", "target_c", "target_b"],
        )
        for path, score in zip(selected, (0.9, 0.6, 0.8)):
            self.assertAlmostEqual(path.normalized_score, score / 2.3)

    def test_default_pool_and_selection_limits(self) -> None:
        targets = [f"target_{i:02d}" for i in range(42)]
        graph = {
            "seed": tuple(
                RelationshipEdge(table, "union", 0.5) for table in targets
            )
        }

        pool = find_paths(graph, ["seed"], targets)
        selected = select_paths(pool, {"seed"})

        self.assertEqual([path.tables[-1] for path in pool], targets[:40])
        self.assertEqual([path.tables[-1] for path in selected], targets[:6])

    def test_observe_uses_sibling_footprint_and_preserves_evidence(
        self,
    ) -> None:
        state = DiscoveryState(seed_matches=[_match("seed")])
        current = state.add_child(
            "0", "search", {"q": "current"}, [_match("seed")]
        )
        sibling = state.add_child(
            "0", "search", {"q": "sibling"}, [_match("seen")]
        )
        state.add_child(sibling, "search", {"q": "deeper"}, [_match("known")])
        state.add_child(
            current,
            "search",
            {"q": "own child"},
            [_match("fresh"), _match("target")],
        )
        bridge = RelationshipEdge("fresh", "join", 0.6, ("key",))
        graph = {
            "seed": (RelationshipEdge("seen", "union", 0.9), bridge),
            "seen": (RelationshipEdge("known", "union", 0.9),),
            "fresh": (RelationshipEdge("target", "join", 0.6),),
        }
        schemas = {
            table: ("key",)
            for table in ("seed", "seen", "known", "fresh", "target", "unused")
        }

        evidence = observe(
            graph,
            state,
            current,
            ["seed"],
            ("known", "target"),
            schemas,
            path_budget=2,
        )

        self.assertEqual(
            [path.tables for path in evidence.paths],
            [("seed", "fresh", "target"), ("seed", "seen", "known")],
        )
        self.assertEqual(evidence.paths[0].edges[0], bridge)
        self.assertEqual(
            evidence.reachable_tables, ("fresh", "target", "seen", "known")
        )
        self.assertEqual(
            evidence.schemas,
            {
                table: schemas[table]
                for table in ("seed", "fresh", "target", "seen", "known")
            },
        )


if __name__ == "__main__":
    unittest.main()
