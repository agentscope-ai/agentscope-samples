# -*- coding: utf-8 -*-
from loguru import logger
from .alias_toolkit import AliasToolkit


def share_tools(
    old_toolkit: AliasToolkit,
    new_toolkit: AliasToolkit,
    tool_list: list[str],
) -> None:
    """
    Share specified tools from an old toolkit to a new toolkit.

    This function copies tools from one toolkit to another based on the
    provided tool list. If a tool doesn't exist in the old toolkit,
    a warning is logged.

    Args:
        old_toolkit (Toolkit):
            The source toolkit containing tools to be shared.
        new_toolkit (Toolkit):
            The destination toolkit to receive the tools.
        tool_list (list[str]):
            List of tool names to be copied from old to new toolkit.

    Returns:
        None

    Note:
        This function modifies the new_toolkit in place.
        If a tool in tool_list is not found in old_toolkit,
        a warning is logged but execution continues.
    """
    for tool in tool_list:
        if tool in old_toolkit.tools and tool not in new_toolkit.tools:
            new_toolkit.tools[tool] = old_toolkit.tools[tool]
        elif tool in old_toolkit.tools:
            logger.warning(
                f"Tool {tool} is already in the provided new_toolkit",
                tool,
            )
        else:
            logger.warning(
                f"No tool {tool} in the provided old_toolkit",
                tool,
            )
