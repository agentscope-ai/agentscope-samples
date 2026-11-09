# -*- coding: utf-8 -*-
"""Search for related tables from columns in an existing table."""

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from pandas.api.types import is_float_dtype, is_integer_dtype

from indexing import ColumnIndex, ColumnRepresentation
from indexing.column_matcher import ColumnNameMatcher
from indexing.sketches import CountMinSketch, QuantileHistogram

from .combiner import Match
from .ranker import (
    CandidateColumn,
    ColumnStatistics,
    CorrelationColumn,
    TableFrames,
    _Bound,
    _TableRanker,
    _match,
    _normalize_scores,
    _range_bounds,
    _top_matches,
)
from .seeker import (
    _TableSeeker,
    _metadata_queries,
    _retrieve_content,
    _union_matches,
)

_JOIN_CANDIDATE_LIMIT = 512


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
            for match in _retrieve_content(
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


def _positive_result_cap(result_cap: int) -> int:
    if (
        isinstance(result_cap, bool)
        or not isinstance(result_cap, int)
        or result_cap < 1
    ):
        raise ValueError("result_cap must be a positive integer")
    return result_cap


class TableOperators:
    """Retrieve or rank tables for one discovery tool call at a time."""

    def __init__(
        self,
        index: ColumnIndex,
        frames: TableFrames,
        statistics: ColumnStatistics,
        matcher: ColumnNameMatcher,
        *,
        result_cap: int = 256,
    ) -> None:
        self._result_cap = _positive_result_cap(result_cap)
        self._seeker = _TableSeeker(index, frames, matcher)
        self._ranker = _TableRanker(index, frames, statistics)

    @property
    def result_cap(self) -> int:
        """Return the maximum number of tables emitted by each operator."""
        return self._result_cap

    def _resolve_result_cap(self, override: int | None) -> int:
        return (
            self._result_cap
            if override is None
            else _positive_result_cap(override)
        )

    def metadata_seeker(
        self,
        column_names: Sequence[str],
        column_types: Sequence[str],
        *,
        result_cap: int | None = None,
    ) -> list[Match]:
        """Find tables covering the requested names and column types."""
        queries = _metadata_queries(column_names, column_types)
        return self._seeker.seek(
            queries, "metadata", self._resolve_result_cap(result_cap)
        )

    def eq_ranker(
        self,
        sources: list[Match],
        column_name: str,
        column_value: object,
        *,
        result_cap: int | None = None,
    ) -> list[Match]:
        """Rank source tables by the frequency of a categorical value."""
        cap = self._resolve_result_cap(result_cap)
        return self._ranker.rank_by_statistic(
            self._seeker.source_columns(sources, column_name),
            CountMinSketch,
            lambda sketch: sketch.frequency(column_value),
            cap,
        )

    def range_ranker(
        self,
        sources: list[Match],
        column_name: str,
        min_val: _Bound = None,
        max_val: _Bound = None,
        *,
        result_cap: int | None = None,
        allow_equal_bounds: bool = False,
    ) -> list[Match]:
        """Rank source tables by the fraction inside an inclusive range."""
        lower, upper = _range_bounds(min_val, max_val, allow_equal_bounds)
        cap = self._resolve_result_cap(result_cap)
        return self._ranker.rank_by_statistic(
            self._seeker.source_columns(sources, column_name),
            QuantileHistogram,
            lambda sketch: sketch.range_fraction(lower, upper),
            cap,
        )

    def join_search(
        self, sources: list[Match], join_column_name: str
    ) -> list[Match]:
        """Find tables with positive categorical key overlap."""
        _, overlaps = self._overlapping_keys(sources, join_column_name)
        matches = [_match(column, score) for column, score in overlaps]
        return _top_matches(_normalize_scores(matches), self._result_cap)

    def union_search(
        self, sources: list[Match], union_column_names: list[str]
    ) -> list[Match]:
        """Find tables covering the requested source column contents."""
        if not union_column_names:
            raise ValueError("provide at least one source column name")
        queries = [
            (
                name,
                [
                    column.content
                    for column in self._seeker.source_columns(sources, name)
                ],
            )
            for name in union_column_names
        ]
        return self._seeker.seek(queries, "content", self._result_cap)

    def correlation_search(
        self,
        sources: list[Match],
        join_column_name: str,
        src_corr_column_name: str,
    ) -> list[Match]:
        """Find measures correlated with source measures on shared keys."""
        keys, overlaps = self._overlapping_keys(sources, join_column_name)
        source_measures = []
        for key in keys:
            measure = self._seeker.find_column(
                key.table_id, src_corr_column_name
            )
            if measure is not None and measure.column_type == "Numerical":
                source_measures.append(
                    (self._ranker.key_sketch(key), measure.column_name)
                )
        if not source_measures:
            return []

        matches = []
        for key, _ in overlaps:
            match = self._ranker.best_correlation(key, source_measures)
            if match is not None:
                matches.append(match)
        return _top_matches(_normalize_scores(matches), self._result_cap)

    def _overlapping_keys(
        self, sources: list[Match], name: str
    ) -> tuple[
        list[ColumnRepresentation], list[tuple[ColumnRepresentation, float]]
    ]:
        source_columns = self._seeker.source_columns(sources, name)
        keys = [
            column
            for column in source_columns
            if column.column_type == "Categorical"
        ]
        if not keys:
            return [], []
        candidates = self._seeker.seek(
            [(name, [column.content for column in source_columns])],
            "content",
            _JOIN_CANDIDATE_LIMIT,
        )
        source_sketches = [self._ranker.key_sketch(key) for key in keys]
        overlaps = []
        for candidate in candidates:
            key = self._seeker.find_column(candidate["table_id"], name)
            if key is None or key.column_type != "Categorical":
                continue
            score = self._ranker.overlap(key, source_sketches)
            if score > 0:
                overlaps.append((key, score))
        return keys, overlaps
