# -*- coding: utf-8 -*-
"""Retrieve indexed columns and aggregate table matches."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict
from operator import attrgetter
from typing import Literal

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from indexing import ColumnIndex, ColumnMatch, ColumnRepresentation
from indexing.column_formatter import _normalize_name
from indexing.column_matcher import ColumnNameMatcher

from .combiner import Match
from .ranker import (
    TableFrames,
    _match,
    _normalize_scores,
    _top_matches,
)

_ANN_LIMIT = 512
_SIMILARITY_THRESHOLD = 0.5
_Channel = Literal["metadata", "content"]


def create_seeker(index: ColumnIndex) -> Callable[..., ToolResponse]:
    """Bind the seeker tool to a prebuilt column index."""

    def seek_columns(
        query: str,
        channel: Literal["metadata", "content"] = "metadata",
        top_k: int = 5,
    ) -> ToolResponse:
        """Find table columns relevant to a text query.

        Args:
            query: Text describing the desired columns or their values.
            channel: Use metadata for column names and types, or content
                for representative values and statistics.
            top_k: Maximum number of columns to return.
        """
        try:
            matches = index.search(query, channel=channel, top_k=top_k)
        except ValueError as error:
            return ToolResponse(
                content=[TextBlock(type="text", text=str(error))],
                metadata={"error": str(error)},
            )

        lines = [
            f"{match.table_id}.{match.column_name} "
            f"({match.column_type}) score={match.score:.4f}"
            for match in matches
        ]
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="\n".join(lines) or "No matching columns.",
                ),
            ],
            metadata={"matches": [asdict(match) for match in matches]},
        )

    return seek_columns


def _metadata_queries(
    column_names: Sequence[str], column_types: Sequence[str]
) -> list[tuple[str, list[str]]]:
    if not column_names or len(column_names) != len(column_types):
        raise ValueError("provide a type for each requested column")
    queries = []
    for name, column_type in zip(column_names, column_types):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("column names must be nonempty strings")
        if column_type not in ("Categorical", "Numerical"):
            raise ValueError("column types must be Categorical or Numerical")
        query = (
            f"Column: {_normalize_name(name)} | Type: {column_type}"
            " | Description: None"
        )
        queries.append((name, [query]))
    return queries


def _retrieve_content(
    index: ColumnIndex, table_id: str, column_name: str
) -> list[ColumnMatch]:
    column = index.get_column(table_id, column_name)
    return [
        match
        for match in index.search(
            column.content, channel="content", top_k=_ANN_LIMIT
        )
        if match.table_id != table_id
    ]


def _coverage_matches(
    by_table: Iterable[list[ColumnMatch]], descriptor_count: int
) -> list[Match]:
    matches = []
    for hits in by_table:
        coverage = len(hits) / descriptor_count
        mean_score = sum(hit.score for hit in hits) / len(hits)
        column = max(hits, key=attrgetter("score"))
        # Square coverage to give broader matches more weight.
        matches.append(_match(column, coverage**2 * mean_score))
    return matches


def _union_matches(
    index: ColumnIndex, table_id: str, column_names: list[str]
) -> list[Match]:
    if (
        not isinstance(column_names, list)
        or not column_names
        or any(not isinstance(name, str) for name in column_names)
    ):
        raise ValueError("column_names must be a nonempty list of names")
    if not isinstance(table_id, str):
        raise ValueError("table ID and column name must be strings")

    names = list(dict.fromkeys(column_names))
    by_table: dict[str, list[ColumnMatch]] = {}
    # Keep one positive match per source column in each candidate table.
    for name in names:
        best: dict[str, ColumnMatch] = {}
        for match in _retrieve_content(index, table_id, name):
            if match.score > 0:
                best.setdefault(match.table_id, match)
        for match in best.values():
            by_table.setdefault(match.table_id, []).append(match)

    return _coverage_matches(by_table.values(), len(names))


class _TableSeeker:
    """Resolve and search indexed columns for table discovery."""

    def __init__(
        self,
        index: ColumnIndex,
        frames: TableFrames,
        matcher: ColumnNameMatcher,
        *,
        schemas: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._index = index
        self._frames = frames
        self._matcher = matcher
        self._schemas = schemas

    def find_column(
        self, table_id: str, name: str
    ) -> ColumnRepresentation | None:
        if self._schemas is None:
            frame = self._frames.get(table_id)
            columns = None if frame is None else frame.columns
        else:
            columns = self._schemas.get(table_id)
        if columns is None:
            return None
        column_name = self._matcher.find_match(name, columns)
        if column_name is None:
            return None
        return self._index.get_column(table_id, column_name)

    def source_columns(
        self, sources: list[Match], name: str
    ) -> list[ColumnRepresentation]:
        columns = []
        for table_id in dict.fromkeys(
            source["table_id"] for source in sources
        ):
            column = self.find_column(table_id, name)
            if column is not None:
                columns.append(column)
        return columns

    def seek(
        self,
        descriptors: Sequence[tuple[str, Iterable[str]]],
        channel: _Channel,
        cap: int,
    ) -> list[Match]:
        queries_by_name: dict[str, list[str]] = {}
        for name, queries in descriptors:
            queries_by_name.setdefault(name, []).extend(queries)

        by_table: dict[str, list[ColumnMatch]] = {}
        for queries in queries_by_name.values():
            for hit in self._descriptor_hits(queries, channel).values():
                by_table.setdefault(hit.table_id, []).append(hit)

        matches = _coverage_matches(by_table.values(), len(descriptors))
        return _normalize_scores(_top_matches(matches, cap))

    def _descriptor_hits(
        self, queries: Iterable[str], channel: _Channel
    ) -> dict[str, ColumnMatch]:
        best: dict[str, ColumnMatch] = {}
        for query in dict.fromkeys(queries):
            for hit in self._index.search(query, channel, top_k=_ANN_LIMIT):
                previous = best.get(hit.table_id)
                if hit.score >= _SIMILARITY_THRESHOLD and (
                    previous is None or hit.score > previous.score
                ):
                    best[hit.table_id] = hit
        return best
