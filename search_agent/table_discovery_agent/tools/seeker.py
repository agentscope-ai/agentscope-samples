# -*- coding: utf-8 -*-
"""Expose column retrieval as an AgentScope tool."""

from collections.abc import Callable
from dataclasses import asdict
from typing import Literal

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from indexing import ColumnIndex


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
