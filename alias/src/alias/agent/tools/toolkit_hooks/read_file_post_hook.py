# -*- coding: utf-8 -*-
from agentscope.message import ToolUseBlock, TextBlock
from agentscope.tool import ToolResponse


def _summarize_csv(text_block: TextBlock) -> None:
    """
    Replace the full CSV with a preview (first 5 rows) and a line count.
    """
    recommend_tool = "run_ipython_cell"
    head_len = 5

    lines = text_block["text"].splitlines()
    preview = "\n".join(lines[:head_len])

    text_block["text"] = (
        f"CSV Top-{head_len} rows preview ({len(lines)} total rows)\n"
        f"{preview}\n"
        f"Use code tool (e.g., {recommend_tool}) "
        "to process the data instead of reading all of it"
    )


def read_file_post_hook(
    tool_use: ToolUseBlock,
    tool_response: ToolResponse,
) -> ToolResponse:
    """
    Condense large CSV outputs after `read_file` or `read_multiple_files`.

    Returns the (possibly modified) ToolResponse so the agent sees only
    a brief snippet instead of the entire file.
    """
    tool_name = tool_use.get("name", "")

    # --- read_file ---------------------------------------------------------
    if tool_name == "read_file":
        path: str = str(tool_use["input"].get("path", ""))
        if path.lower().endswith(".csv"):
            _summarize_csv(tool_response.content[0])

    # --- read_multiple_files ----------------------------------------------
    elif tool_name == "read_multiple_files":
        paths = tool_use["input"].get("paths", [])
        for i, path in enumerate(paths):
            if path.lower().endswith(".csv"):
                # Match each path to its corresponding block
                _summarize_csv(tool_response.content[i])

    return tool_response
