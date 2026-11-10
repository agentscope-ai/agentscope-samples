# -*- coding: utf-8 -*-
"""Extract, verify, and rank by column constraints for table discovery."""

import json
from collections.abc import Mapping, Sequence
from math import isfinite
from operator import itemgetter
from typing import Any, Literal, TypedDict, cast

import pandas as pd
from agentscope.formatter import FormatterBase
from agentscope.message import Msg
from agentscope.model import ChatModelBase, ChatResponse

from indexing.column_matcher import ColumnNameMatcher
from table_tools.combiner import Match

from .prompts import COL_CONSTRAINT_PROMPT, CONSTRAINT_RETRY_HINT

Scalar = str | int | float | bool | None
ColumnType = Literal["Categorical", "Numerical"]


class QueryConstraint(TypedDict):
    """One column requirement with optional categorical or numeric values."""

    col_name: str
    col_type: ColumnType
    values: list[Scalar]


def _parse_constraints(text: str) -> list[QueryConstraint]:
    start, stop = text.find("["), text.rfind("]") + 1
    if start == -1 or not stop:
        raise ValueError("Expected a JSON array of column constraints.")
    entries = json.loads(text[start:stop])

    constraints: list[QueryConstraint] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.keys() != {
            "col_name",
            "col_type",
            "values",
        }:
            raise ValueError("Expected col_name, col_type, and values keys.")
        name = entry.get("col_name")
        column_type = entry.get("col_type")
        values = entry.get("values")
        if (
            not isinstance(name, str)
            or not name.strip()
            or column_type not in ("Categorical", "Numerical")
            or not isinstance(values, list)
        ):
            raise ValueError("Invalid column constraint.")
        if any(
            (value is not None and not isinstance(value, (str, int, float)))
            or (isinstance(value, float) and not isfinite(value))
            for value in values
        ):
            raise ValueError("Constraint values must be JSON scalars.")
        if column_type == "Numerical" and values:
            if len(values) != 2 or any(
                value is not None
                and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                )
                for value in values
            ):
                raise ValueError("Expected two numeric or null bounds.")
            lower, upper = values
            if lower is not None and upper is not None and lower >= upper:
                raise ValueError("Lower bound must be less than upper bound.")
            if lower is None and upper is None:
                values = []

        constraints.append(
            QueryConstraint(
                col_name=name.strip(),
                col_type=column_type,
                values=values,
            ),
        )
    return constraints


async def extract_constraints(
    query: str,
    table_schema: Sequence[str],
    model: ChatModelBase,
    formatter: FormatterBase,
) -> list[QueryConstraint]:
    """Extract requirements from the query.

    Raises:
        RuntimeError: If the model fails to return valid constraints.
    """
    prompt = COL_CONSTRAINT_PROMPT.format(
        query=query,
        table_schema=json.dumps(table_schema, ensure_ascii=False),
    )
    last_error: Exception | None = None
    for attempt in range(3):
        content = prompt
        if attempt:
            content += CONSTRAINT_RETRY_HINT
        try:
            messages = await formatter.format(
                [Msg(name="user", role="user", content=content)],
            )
            response = await model(messages)
            final: ChatResponse | None
            if isinstance(response, ChatResponse):
                final = response
            else:
                final = None
                async for chunk in response:
                    final = chunk
            if final is None:
                raise ValueError("The model returned no response.")
            text = "".join(
                block["text"]
                for block in final.content
                if block["type"] == "text"
            )
            return _parse_constraints(text)
        except Exception as error:
            last_error = error
    raise RuntimeError(
        "Could not extract column constraints after three attempts.",
    ) from last_error


def _in_range(
    value: Any,
    lower: int | float | None,
    upper: int | float | None,
) -> bool:
    try:
        return (lower is None or value >= lower) and (
            upper is None or value <= upper
        )
    except TypeError:
        return False


def satisfies(
    constraint: QueryConstraint,
    frame: pd.DataFrame,
    matcher: ColumnNameMatcher,
    *,
    numerical_threshold: float = 0.0,
) -> bool:
    """Check the best matching column for the required values or presence."""
    name = matcher.find_match(constraint["col_name"], frame.columns)
    if name is None:
        return False
    values = constraint["values"]
    if not values:
        return True
    column = frame[name]
    if constraint["col_type"] == "Categorical":
        return all(column.isin([value]).any() for value in values)

    non_null = column.dropna()
    if non_null.empty:
        return False
    lower, upper = cast(list[int | float | None], values)
    hits = (_in_range(value, lower, upper) for value in non_null)
    if numerical_threshold <= 0:
        return any(hits)
    return sum(hits) / len(non_null) >= numerical_threshold


def _ranker_columns(tool_name: str, inputs: Mapping[str, Any]) -> list[str]:
    if tool_name in ("rank_equality", "rank_range"):
        return [
            candidate["column_name"]
            for candidate in inputs.get("candidates", ())
        ]
    if tool_name in ("eq_ranker", "range_ranker"):
        name = inputs.get("column_name")
        if isinstance(name, str):
            return [name]
    return []


def resolve_constraints(
    constraints: Sequence[QueryConstraint],
    tool_name: str,
    inputs: Mapping[str, Any],
    matches: Sequence[Match],
    frames: Mapping[str, pd.DataFrame],
    matcher: ColumnNameMatcher,
) -> list[QueryConstraint]:
    """Return constraints still outstanding after verifying three tables."""
    sorted_matches = sorted(matches, key=itemgetter("score"), reverse=True)
    table_ids = list(
        dict.fromkeys(match["table_id"] for match in sorted_matches),
    )
    top_tables = [
        frames[table_id] for table_id in table_ids[:3] if table_id in frames
    ]
    target_columns = _ranker_columns(tool_name, inputs)

    remaining = []
    for constraint in constraints:
        if (
            constraint["values"]
            and matcher.find_match(constraint["col_name"], target_columns)
            is None
        ) or not any(
            satisfies(constraint, frame, matcher, numerical_threshold=0.5)
            for frame in top_tables
        ):
            remaining.append(constraint)
    return remaining


def rank_results(
    matches: Sequence[Match],
    initial_constraints: Sequence[QueryConstraint],
    frames: Mapping[str, pd.DataFrame],
    matcher: ColumnNameMatcher,
    *,
    min_constraint_matches: int = 1,
) -> list[Match]:
    """Order matches by constraints satisfied, then score, with a fallback."""
    counts = {}
    for table_id in dict.fromkeys(match["table_id"] for match in matches):
        frame = frames.get(table_id)
        counts[table_id] = (
            0
            if frame is None
            else sum(
                satisfies(constraint, frame, matcher)
                for constraint in initial_constraints
            )
        )
    ranked = sorted(
        matches,
        key=lambda match: (counts[match["table_id"]], match["score"]),
        reverse=True,
    )
    filtered = [
        match
        for match in ranked
        if counts[match["table_id"]] >= min_constraint_matches
    ]
    return filtered or ranked
