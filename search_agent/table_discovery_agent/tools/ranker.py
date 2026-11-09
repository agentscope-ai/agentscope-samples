# -*- coding: utf-8 -*-
"""Score candidate columns using value and relationship sketches."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from functools import cache
from math import isfinite
from operator import itemgetter
from typing import TypeVar

import pandas as pd
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from pandas.api.types import is_float_dtype, is_integer_dtype
from typing_extensions import TypedDict

from indexing import ColumnIndex, ColumnMatch, ColumnRepresentation, KeySketch
from indexing.sketches import CountMinSketch, QuantileHistogram

from .combiner import Match

ColumnStatistics = Mapping[tuple[str, str], CountMinSketch | QuantileHistogram]
TableFrames = Mapping[str, pd.DataFrame]
_Sketch = TypeVar("_Sketch", CountMinSketch, QuantileHistogram)
_Bound = float | str | None
_CORRELATION_THRESHOLD = 0.5


class CandidateColumn(TypedDict):
    """Identify a column in the current data lake."""

    table_id: str
    column_name: str


def _error(message: str) -> ToolResponse:
    return ToolResponse(
        content=[TextBlock(type="text", text=message)],
        metadata={"error": message},
    )


class CorrelationColumn(CandidateColumn):
    """Identify a numeric column and the key used to align its values."""

    key_column: str


@dataclass(frozen=True)
class _CorrelationMatch(ColumnMatch):
    key_column: str
    correlation: float


def _column_id(candidate: CandidateColumn) -> tuple[str, str]:
    if isinstance(candidate, dict):
        table_id = candidate.get("table_id")
        column_name = candidate.get("column_name")
        if isinstance(table_id, str) and isinstance(column_name, str):
            return table_id, column_name
    raise ValueError("each candidate must provide table_id and column_name")


def _ranked_response(
    matches: list[ColumnMatch],
    skipped: int = 0,
    skip_reason: str = "of another type",
) -> ToolResponse:
    matches.sort(key=lambda match: match.score, reverse=True)
    lines = []
    for match in matches:
        line = f"{match.table_id}.{match.column_name} score={match.score:.4f}"
        if isinstance(match, _CorrelationMatch):
            line += f" (correlation={match.correlation:+.4f})"
        lines.append(line)
    if not lines:
        lines.append("No candidate columns scored.")
    if skipped:
        lines.append(f"Skipped {skipped} candidate columns {skip_reason}.")
    return ToolResponse(
        content=[TextBlock(type="text", text="\n".join(lines))],
        metadata={
            "matches": [asdict(match) for match in matches],
            "skipped": skipped,
        },
    )


def _rank(
    statistics: ColumnStatistics,
    candidates: list[CandidateColumn],
    sketch_type: type[_Sketch],
    score: Callable[[_Sketch], float],
    column_type: str,
) -> ToolResponse:
    matches = []
    skipped = 0
    if not isinstance(candidates, list):
        return _error("candidates must be a list of column references")

    for candidate in candidates:
        try:
            table_id, column_name = _column_id(candidate)
        except ValueError as error:
            return _error(str(error))
        sketch = statistics.get((table_id, column_name))
        if sketch is None:
            return _error(f"Unknown column: {table_id}.{column_name}")
        if not isinstance(sketch, sketch_type):
            skipped += 1
            continue

        matches.append(
            ColumnMatch(table_id, column_name, column_type, score(sketch)),
        )

    return _ranked_response(matches, skipped)


def create_rankers(
    statistics: ColumnStatistics,
) -> tuple[Callable[..., ToolResponse], ...]:
    """Bind equality and range rankers to the supplied column statistics."""

    def rank_equality(
        candidates: list[CandidateColumn],
        value: str,
    ) -> ToolResponse:
        """Rank retrieved categorical columns for an exact cell value.

        Scores estimate the fraction of non-null cells with that value.
        Zero scores are retained.

        Args:
            candidates: Candidate columns identified by table ID and name.
            value: Cell value to match, expressed as text.
        """
        if not isinstance(value, str):
            return _error("value must be a string")

        return _rank(
            statistics,
            candidates,
            CountMinSketch,
            lambda sketch: sketch.frequency(value),
            "Categorical",
        )

    def rank_range(
        candidates: list[CandidateColumn],
        lower: float | None = None,
        upper: float | None = None,
    ) -> ToolResponse:
        """Rank retrieved numeric columns for an inclusive value range.

        Scores estimate the fraction of finite values within the range.
        Provide at least one bound. Zero scores are retained.

        Args:
            candidates: Candidate columns identified by table ID and name.
            lower: Inclusive lower bound. Omit for an unbounded lower end.
            upper: Inclusive upper bound. Omit for an unbounded upper end.
        """
        if lower is None and upper is None:
            return _error("provide at least one range bound")
        try:
            valid = all(
                bound is None
                or (not isinstance(bound, bool) and isfinite(bound))
                for bound in (lower, upper)
            )
        except (TypeError, OverflowError):
            valid = False
        if not valid:
            return _error("range bounds must be finite numbers")
        if lower is not None and upper is not None and lower > upper:
            return _error("lower bound must not exceed upper bound")

        return _rank(
            statistics,
            candidates,
            QuantileHistogram,
            lambda sketch: sketch.range_fraction(lower, upper),
            "Numerical",
        )

    return rank_equality, rank_range


def create_relationship_rankers(
    frames: TableFrames,
) -> tuple[Callable[..., ToolResponse], ...]:
    """Bind relationship rankers to the loaded tables."""

    def resolve_column(table_id: str, column_name: str) -> pd.Series:
        frame = frames.get(table_id)
        if frame is None or column_name not in frame.columns:
            raise ValueError(f"Unknown column: {table_id}.{column_name}")
        return frame[column_name]

    # Share key sketches across the overlap and correlation rankers.
    @cache
    def key_sketch(table_id: str, key_column: str) -> KeySketch:
        return KeySketch(frames[table_id], key_column)

    def measure(column: CorrelationColumn) -> tuple[KeySketch, str]:
        table_id, column_name = _column_id(column)
        key_column = column.get("key_column")
        if not isinstance(key_column, str):
            raise ValueError("each correlation column must provide key_column")
        resolve_column(table_id, column_name)
        resolve_column(table_id, key_column)
        return key_sketch(table_id, key_column), column_name

    def rank_overlap(
        reference: CandidateColumn,
        candidates: list[CandidateColumn],
    ) -> ToolResponse:
        """Rank known candidate keys by value overlap with a reference key.

        Use when both sides' key columns are known. Scores estimate Jaccard
        similarity. Zero scores are retained.

        Args:
            reference: Reference key column, identified by table ID and name.
            candidates: Candidate key columns, identified by table ID and name.
        """
        if not isinstance(candidates, list):
            return _error("candidates must be a list of column references")
        try:
            reference_id = _column_id(reference)
            resolve_column(*reference_id)

            reference_sketch = key_sketch(*reference_id)
            matches = []
            for candidate in candidates:
                table_id, column_name = _column_id(candidate)
                column = resolve_column(table_id, column_name)

                numeric = is_integer_dtype(column) or is_float_dtype(column)
                score = reference_sketch.overlap(
                    key_sketch(table_id, column_name),
                )
                matches.append(
                    ColumnMatch(
                        table_id,
                        column_name,
                        "Numerical" if numeric else "Categorical",
                        score,
                    ),
                )
        except ValueError as error:
            return _error(str(error))
        return _ranked_response(matches)

    def rank_correlation(
        reference: CorrelationColumn,
        candidates: list[CorrelationColumn],
    ) -> ToolResponse:
        """Rank known candidate measures by correlation on shared keys.

        Specify the key and measure on each side. Values are averaged per
        key, then ranked by absolute Pearson correlation. The signed
        coefficient is returned, and undefined correlations are skipped.

        Args:
            reference: Reference measure with table ID, column name and key.
            candidates: Candidate measures with table IDs, column names and
                keys. Key names can differ between tables.
        """
        if not isinstance(candidates, list):
            return _error("candidates must be a list of column references")

        matches: list[ColumnMatch] = []
        skipped = 0
        try:
            reference_sketch, reference_column = measure(reference)
            for candidate in candidates:
                sketch, column_name = measure(candidate)
                correlation = _finite_correlation(
                    reference_sketch,
                    sketch,
                    reference_column,
                    column_name,
                )
                if correlation is None:
                    skipped += 1
                    continue

                # Rank by magnitude and retain the signed coefficient.
                matches.append(
                    _CorrelationMatch(
                        candidate["table_id"],
                        column_name,
                        "Numerical",
                        abs(correlation),
                        candidate["key_column"],
                        correlation,
                    ),
                )
        except ValueError as error:
            return _error(str(error))
        return _ranked_response(matches, skipped, "with undefined correlation")

    return rank_overlap, rank_correlation


def _normalize_scores(matches: list[Match]) -> list[Match]:
    total = sum(match["score"] for match in matches)
    for match in matches:
        match["score"] /= total
    return matches


def _top_matches(matches: list[Match], limit: int) -> list[Match]:
    return sorted(matches, key=itemgetter("score"), reverse=True)[:limit]


def _match(column: ColumnMatch | ColumnRepresentation, score: float) -> Match:
    return Match(
        table_id=column.table_id,
        column_name=column.column_name,
        column_type=column.column_type,
        score=score,
    )


def _range_bound(value: _Bound) -> float | None:
    if value is None or (
        isinstance(value, str)
        and value.strip().lower() in ("", "null", "none")
    ):
        return None
    try:
        if not isinstance(value, bool):
            bound = float(value)
            if isfinite(bound):
                return bound
    except (TypeError, ValueError, OverflowError):
        pass
    raise ValueError("range bounds must be finite numbers or null")


def _range_bounds(
    min_val: _Bound, max_val: _Bound, allow_equal_bounds: bool
) -> tuple[float | None, float | None]:
    lower, upper = _range_bound(min_val), _range_bound(max_val)
    if lower == upper and (lower is None or not allow_equal_bounds):
        raise ValueError("provide distinct bounds or one open bound")
    return lower, upper


def _finite_correlation(
    source: KeySketch,
    target: KeySketch,
    source_measure: str,
    target_measure: str,
) -> float | None:
    value = source.correlation(target, source_measure, target_measure)
    if value is None or not isfinite(value):
        return None
    return value


class _TableRanker:
    """Score table candidates and cache sketches across discovery calls."""

    def __init__(
        self,
        index: ColumnIndex,
        frames: TableFrames,
        statistics: ColumnStatistics,
    ) -> None:
        self._index = index
        self._frames = frames
        self._statistics = statistics
        self._key_sketches: dict[tuple[str, str], KeySketch] = {}

    def rank_by_statistic(
        self,
        columns: Iterable[ColumnRepresentation],
        statistic_type: type[_Sketch],
        score: Callable[[_Sketch], float],
        result_cap: int,
    ) -> list[Match]:
        matches = []
        for column in columns:
            statistic = self._statistics.get(
                (column.table_id, column.column_name)
            )
            if isinstance(statistic, statistic_type):
                value = score(statistic)
                if value > 0:
                    matches.append(_match(column, value))
        return _top_matches(_normalize_scores(matches), result_cap)

    def key_sketch(self, column: ColumnRepresentation) -> KeySketch:
        key = (column.table_id, column.column_name)
        if key not in self._key_sketches:
            self._key_sketches[key] = KeySketch(
                self._frames[column.table_id], column.column_name
            )
        return self._key_sketches[key]

    def overlap(
        self, key: ColumnRepresentation, sources: list[KeySketch]
    ) -> float:
        sketch = self.key_sketch(key)
        return sum(source.overlap(sketch) for source in sources)

    def best_correlation(
        self,
        key: ColumnRepresentation,
        sources: list[tuple[KeySketch, str]],
    ) -> Match | None:
        target = self.key_sketch(key)
        best = None
        best_score = _CORRELATION_THRESHOLD
        for name in self._frames[key.table_id].columns:
            if name == key.column_name:
                continue
            column = self._index.get_column(key.table_id, name)
            if column.column_type != "Numerical":
                continue
            correlation = 0.0
            for source, measure in sources:
                value = _finite_correlation(source, target, measure, name)
                if value is not None:
                    correlation += value
            score = abs(correlation)
            if score > best_score:
                best = _match(column, score)
                best["key_column"] = key.column_name
                best["correlation"] = correlation
                best_score = score
        return best
