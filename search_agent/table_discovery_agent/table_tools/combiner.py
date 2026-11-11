# -*- coding: utf-8 -*-
"""Combine discovery results by table identity."""

from math import isfinite
from typing import Literal

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from typing_extensions import NotRequired, TypedDict


class Match(TypedDict):
    """A candidate column with its score and optional correlation evidence."""

    table_id: str
    column_name: str
    column_type: str
    score: float
    key_column: NotRequired[str]
    correlation: NotRequired[float]


def _best_by_table(matches: list[Match]) -> dict[str, Match]:
    if not isinstance(matches, list):
        raise ValueError("each input must be a list of candidate matches")

    best: dict[str, Match] = {}
    for match in matches:
        if not isinstance(match, dict) or any(
            not isinstance(match.get(field), str)
            for field in ("table_id", "column_name", "column_type")
        ):
            raise ValueError(
                "each match must provide table_id, column_name "
                "and column_type",
            )
        score = match.get("score")
        try:
            valid = (
                isinstance(score, (float, int))
                and not isinstance(score, bool)
                and isfinite(score)
            )
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("each match must have a finite numeric score")

        table_id = match["table_id"]
        previous = best.get(table_id)
        # A strict comparison keeps the earliest match on ties.
        if previous is None or match["score"] > previous["score"]:
            best[table_id] = match
    return best


def combine_results(
    left: list[Match],
    right: list[Match],
    operation: Literal["intersection", "union", "difference"],
) -> ToolResponse:
    """Combine two existing discovery results by table ID.

    Keep the highest-scored match per retained table, preferring the left
    result on ties.

    Args:
        left: Candidate matches from the first discovery result.
        right: Candidate matches from the second discovery result.
        operation: Intersection keeps shared tables. Union keeps tables
            from either list. Difference removes tables returned on the
            right from the left list.
    """
    try:
        if operation not in ("intersection", "union", "difference"):
            raise ValueError(
                "operation must be intersection, union or difference",
            )
        left_by_table = _best_by_table(left)
        right_by_table = _best_by_table(right)
    except ValueError as error:
        return ToolResponse(
            content=[TextBlock(type="text", text=str(error))],
            metadata={"error": str(error)},
        )

    matches = []
    for table_id, match in left_by_table.items():
        right_match = right_by_table.get(table_id)
        if operation == "difference":
            if right_match is None:
                matches.append(match)
        elif right_match is not None:
            matches.append(
                right_match
                if right_match["score"] > match["score"]
                else match,
            )
        elif operation == "union":
            matches.append(match)

    if operation == "union":
        matches.extend(
            match
            for table_id, match in right_by_table.items()
            if table_id not in left_by_table
        )

    lines = [
        f"{match['table_id']}.{match['column_name']} "
        f"score={match['score']:.4f}"
        for match in matches
    ]
    summary = "\n".join(lines) or "No matching tables."
    return ToolResponse(
        content=[TextBlock(type="text", text=summary)],
        metadata={"matches": matches},
    )
