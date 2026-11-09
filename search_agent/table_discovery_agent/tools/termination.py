# -*- coding: utf-8 -*-
"""Signal completion of the current discovery branch."""

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse


def end_search() -> ToolResponse:
    """Finish the current branch when its candidates answer the request."""
    return ToolResponse(
        content=[TextBlock(type="text", text="Finish the current branch.")],
        metadata={"end_search": True},
    )
