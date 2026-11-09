# -*- coding: utf-8 -*-
"""Register table discovery tools for AgentScope."""

from agentscope.tool import Toolkit

from indexing import ColumnIndex

from .combiner import combine_results
from .composite_seeker import create_composite_seekers
from .ranker import (
    ColumnStatistics,
    TableFrames,
    create_rankers,
    create_relationship_rankers,
)
from .seeker import create_seeker
from .termination import end_search

__all__ = ["create_toolkit"]


def create_toolkit(
    index: ColumnIndex,
    *,
    statistics: ColumnStatistics | None = None,
    frames: TableFrames | None = None,
) -> Toolkit:
    """Register discovery tools for the supplied lake resources."""
    toolkit = Toolkit()
    toolkit.register_tool_function(create_seeker(index))

    if statistics is not None:
        for ranker in create_rankers(statistics):
            toolkit.register_tool_function(ranker)

    if frames is not None:
        overlap, correlation = create_relationship_rankers(frames)
        toolkit.register_tool_function(overlap)
        toolkit.register_tool_function(correlation)
        for search in create_composite_seekers(
            index,
            frames,
            overlap,
            correlation,
        ):
            toolkit.register_tool_function(search)

    toolkit.register_tool_function(combine_results)
    toolkit.register_tool_function(end_search)
    return toolkit
