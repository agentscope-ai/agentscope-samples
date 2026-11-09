# -*- coding: utf-8 -*-
"""Build and search a graph of union and join relationships between tables."""

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from heapq import nlargest
from operator import itemgetter
from typing import Literal

import pandas as pd

from indexing import ColumnIndex, KeySketch
from indexing.column_matcher import ColumnNameMatcher
from indexing.embedding import ColumnEncoder


@dataclass(frozen=True)
class RelationshipEdge:
    """A relation to another table, with source bridge columns for joins."""

    target: str
    kind: Literal["union", "join"]
    score: float
    columns: tuple[str, ...] = ()


RelationshipGraph = dict[str, tuple[RelationshipEdge, ...]]


@dataclass(frozen=True)
class RelationshipPath:
    """A sequence of related tables scored by its weakest edge."""

    tables: tuple[str, ...]
    edges: tuple[RelationshipEdge, ...]
    reliability: float
    normalized_score: float = 0.0


def _content_hits(index: ColumnIndex, content: str) -> list[tuple[str, float]]:
    best: dict[str, float] = {}
    for hit in index.search(content, channel="content", top_k=512):
        if hit.score >= 0.5:
            best[hit.table_id] = max(best.get(hit.table_id, 0.0), hit.score)
    return sorted(best.items(), key=itemgetter(1), reverse=True)[:8]


def _top_edges(scores: Mapping[str, float]) -> list[tuple[str, float]]:
    best = sorted(scores.items(), key=itemgetter(1), reverse=True)[:10]
    total = sum(score for _, score in best)
    return [(target, score / total) for target, score in best]


def build_relationship_graph(
    index: ColumnIndex,
    frames: Mapping[str, pd.DataFrame],
    encoder: ColumnEncoder,
) -> RelationshipGraph:
    """Build the weighted outgoing edges for every table in the lake."""
    names = {
        table_id: tuple(dict.fromkeys(frame.columns))
        for table_id, frame in frames.items()
    }
    matcher = ColumnNameMatcher(
        encoder, (name for columns in names.values() for name in columns)
    )

    @cache
    def key_sketch(table_id: str, name: str) -> KeySketch:
        return KeySketch(frames[table_id], name)

    graph: RelationshipGraph = {}
    for table_id, columns in names.items():
        union_scores: dict[str, float] = defaultdict(float)
        join_columns: dict[str, dict[str, float]] = defaultdict(dict)

        for name in columns:
            column = index.get_column(table_id, name)
            hits = _content_hits(index, column.content)
            # Count the source in the per-column denominator when retrieved.
            total = sum(score for _, score in hits)
            overlaps: dict[str, float] = {}
            for target, score in hits:
                if target == table_id:
                    continue
                union_scores[target] += score / total

                if column.column_type != "Categorical":
                    continue
                key = matcher.find_match(name, names[target])
                if (
                    key is None
                    or index.get_column(target, key).column_type
                    != "Categorical"
                ):
                    continue
                overlap = key_sketch(table_id, name).overlap(
                    key_sketch(target, key)
                )
                if overlap > 0:
                    overlaps[target] = overlap

            overlap_total = sum(overlaps.values())
            for target, overlap in overlaps.items():
                join_columns[target][name] = overlap / overlap_total

        edges = [
            RelationshipEdge(target, "union", score)
            for target, score in _top_edges(union_scores)
        ]
        join_scores = {
            target: max(columns.values())
            for target, columns in join_columns.items()
        }
        for target, score in _top_edges(join_scores):
            bridges = sorted(
                join_columns[target],
                key=join_columns[target].__getitem__,
                reverse=True,
            )
            edges.append(
                RelationshipEdge(target, "join", score, tuple(bridges))
            )
        graph[table_id] = tuple(edges)
    return graph


def find_paths(
    graph: RelationshipGraph,
    seeds: Sequence[str],
    targets: Sequence[str],
    max_depth: int = 3,
    path_pool_size: int = 40,
) -> list[RelationshipPath]:
    """Retain the most reliable paths reaching targets within the hop limit."""
    if not seeds or not targets or max_depth < 1 or path_pool_size < 1:
        return []
    target_ids = set(targets)

    def walk(
        tables: tuple[str, ...],
        edges: tuple[RelationshipEdge, ...],
        reliability: float,
    ) -> Iterator[RelationshipPath]:
        current = tables[-1]
        if edges and current in target_ids:
            yield RelationshipPath(tables, edges, reliability)
            return
        if len(edges) >= max_depth:
            return
        for edge in graph.get(current, ()):
            if edge.target not in tables:
                yield from walk(
                    (*tables, edge.target),
                    (*edges, edge),
                    min(reliability, edge.score),
                )

    paths = (
        path for seed in seeds for path in walk((seed,), (), float("inf"))
    )
    # Ties keep DFS order, including the order of parallel edge types.
    return nlargest(path_pool_size, paths, key=lambda path: path.reliability)
