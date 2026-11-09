# -*- coding: utf-8 -*-
"""Search for related tables from columns in an existing table."""

from collections.abc import Callable, Mapping
from typing import cast

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from pandas.api.types import is_float_dtype, is_integer_dtype

from indexing import ColumnIndex, ColumnMatch

from .combiner import Match
from .ranker import CandidateColumn, CorrelationColumn, TableFrames

_CANDIDATE_LIMIT = 512


def _matches(response: ToolResponse) -> list[Match]:
    metadata = response.metadata or {}
    if "error" in metadata:
        raise ValueError(metadata["error"])
    return cast(list[Match], metadata["matches"])


def _validate_top_k(top_k: int) -> None:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")


def _validate_reference(
    reference: Mapping[str, object], *, with_key: bool = False
) -> None:
    fields: tuple[str, ...] = ("table_id", "column_name")
    missing_message = "reference must identify a table and column"
    type_message = "table ID and column name must be strings"
    if with_key:
        fields += ("key_column",)
        missing_message = "reference must identify a table, key and measure"
        type_message = "table ID, measure and key must be strings"
    if not isinstance(reference, Mapping) or any(
        field not in reference for field in fields
    ):
        raise ValueError(missing_message)
    if any(not isinstance(reference[field], str) for field in fields):
        raise ValueError(type_message)


def _retrieve(
    index: ColumnIndex, table_id: str, column_name: str
) -> list[ColumnMatch]:
    column = index.get_column(table_id, column_name)
    return [
        match
        for match in index.search(
            column.content, channel="content", top_k=_CANDIDATE_LIMIT
        )
        if match.table_id != table_id
    ]


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
        for match in _retrieve(index, table_id, name):
            if match.score > 0:
                best.setdefault(match.table_id, match)
        for match in best.values():
            by_table.setdefault(match.table_id, []).append(match)

    matches = []
    for matched in by_table.values():
        representative = max(matched, key=lambda match: match.score)
        coverage = len(matched) / len(names)
        mean_score = sum(match.score for match in matched) / len(matched)
        # Square coverage to give broader matches more weight.
        matches.append(
            Match(
                table_id=representative.table_id,
                column_name=representative.column_name,
                column_type=representative.column_type,
                score=coverage**2 * mean_score,
            ),
        )
    return matches


def _correlation_candidates(
    frames: TableFrames, keys: list[Match]
) -> list[CorrelationColumn]:
    candidates = []
    for key in keys:
        table_id = key["table_id"]
        key_column = key["column_name"]
        for name, values in frames[table_id].items():
            if name != key_column and (
                is_integer_dtype(values) or is_float_dtype(values)
            ):
                candidates.append(
                    CorrelationColumn(
                        table_id=table_id,
                        key_column=key_column,
                        column_name=str(name),
                    ),
                )
    return candidates


def _results(matches: list[Match], top_k: int) -> ToolResponse:
    best: dict[str, Match] = {}
    for match in sorted(matches, key=lambda item: item["score"], reverse=True):
        best.setdefault(match["table_id"], match)
    selected = list(best.values())[:top_k]

    lines = []
    for match in selected:
        line = (
            f"{match['table_id']}.{match['column_name']} "
            f"score={match['score']:.4f}"
        )
        if "correlation" in match:
            line += f" (correlation={match['correlation']:+.4f})"
        lines.append(line)
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text="\n".join(lines) or "No related tables found.",
            ),
        ],
        metadata={"matches": selected},
    )


def _error(message: str) -> ToolResponse:
    return ToolResponse(
        content=[TextBlock(type="text", text=message)],
        metadata={"error": message},
    )


def create_composite_seekers(
    index: ColumnIndex,
    frames: TableFrames,
    rank_overlap: Callable[..., ToolResponse],
    rank_correlation: Callable[..., ToolResponse],
) -> tuple[Callable[..., ToolResponse], ...]:
    """Compose content retrieval with the toolkit's relationship rankers."""

    def shared_keys(reference: CandidateColumn) -> list[Match]:
        candidates = [
            CandidateColumn(
                table_id=match.table_id, column_name=match.column_name
            )
            for match in _retrieve(
                index, reference["table_id"], reference["column_name"]
            )
        ]
        return [
            match
            for match in _matches(rank_overlap(reference, candidates))
            if match["score"] > 0
        ]

    def join_search(
        reference: CandidateColumn, top_k: int = 5
    ) -> ToolResponse:
        """Find new tables with values overlapping a known reference key.

        Args:
            reference: Reference key column from an existing table.
            top_k: Maximum number of related tables to return.
        """
        try:
            _validate_top_k(top_k)
            _validate_reference(reference)

            return _results(shared_keys(reference), top_k)
        except ValueError as error:
            return _error(str(error))

    def union_search(
        table_id: str, column_names: list[str], top_k: int = 5
    ) -> ToolResponse:
        """Find new tables with columns similar to a reference table's columns.

        Scores favor tables that match more of the requested columns.

        Args:
            table_id: Reference table ID.
            column_names: Columns to match against other tables.
            top_k: Maximum number of related tables to return.
        """
        try:
            _validate_top_k(top_k)

            return _results(
                _union_matches(index, table_id, column_names), top_k
            )
        except ValueError as error:
            return _error(str(error))

    def correlation_search(
        reference: CorrelationColumn, top_k: int = 5
    ) -> ToolResponse:
        """Find new tables with numeric measures correlated on shared keys.

        Use directly when correlation is the goal. This search finds shared
        keys internally and ranks measures by absolute Pearson correlation.

        Args:
            reference: Reference table ID, numeric column and key column.
            top_k: Maximum number of related tables to return.
        """
        try:
            _validate_top_k(top_k)
            _validate_reference(reference, with_key=True)
            table_id = reference["table_id"]
            name = reference["column_name"]
            key_column = reference["key_column"]
            if index.get_column(table_id, name).column_type != "Numerical":
                raise ValueError("reference measure must be numerical")
            if name == key_column:
                raise ValueError("reference measure and key must differ")

            reference_key = CandidateColumn(
                table_id=table_id, column_name=key_column
            )
            candidates = _correlation_candidates(
                frames, shared_keys(reference_key)
            )

            return _results(
                _matches(rank_correlation(reference, candidates)), top_k
            )
        except ValueError as error:
            return _error(str(error))

    return join_search, union_search, correlation_search
