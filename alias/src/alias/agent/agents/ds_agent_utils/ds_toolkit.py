# -*- coding: utf-8 -*-
import traceback
import os
from functools import partial
from agentscope.message import ToolUseBlock, TextBlock
from agentscope.tool import ToolResponse
from agentscope_runtime.sandbox.box.sandbox import Sandbox
from alias.agent.tools import AliasToolkit
from alias.agent.tools.improved_tools import DashScopeMultiModalTools

from .tools.prepare_dataset.clean_messy_spreadsheet import (
    clean_messy_spreadsheet,
)
from .tools.multimodal.image_understanding import (
    summarize_image,
    answer_question_about_image,
)


def run_ipython_cell_post_hook(
    post_funcs: list,
    sandbox: Sandbox,
    tool_use: ToolUseBlock,
    tool_response: ToolResponse,
) -> ToolResponse:
    for func in post_funcs:
        tool_response = func(sandbox, tool_use, tool_response)
    return tool_response


def ansi_escape_post_hook(
    _sandbox: Sandbox,
    _tool_use: ToolUseBlock,
    tool_response: ToolResponse,
) -> ToolResponse:
    for block in tool_response.content:
        if "text" in block:
            # Remove ANSI escape sequences
            import re

            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            block["text"] = ansi_escape.sub("", block["text"])
    return tool_response


def summarize_plt_chart_hook(
    sandbox: Sandbox,
    _tool_use: ToolUseBlock,
    tool_response: ToolResponse,
) -> ToolResponse:
    code = r"""
# Obtain the latest chart summary
all_summaries = monitor.get_all_summaries()
if all_summaries:
    print(all_summaries)
    # Clear existing summaries to avoid duplication
    monitor.clear_all_summaries()
"""

    try:
        chart_summary = sandbox.call_tool("run_ipython_cell", {"code": code})[
            "content"
        ][0]["text"]
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError from e

    if len(chart_summary) > 0:
        text_block: TextBlock = tool_response.content[0]

        text_block["text"] = (
            f"{text_block['text']}\n\n"
            f"Latest chart summary:\n{chart_summary}"
        )

    return tool_response


def truncate_long_text_post_hook(
    _sandbox: Sandbox,
    _tool_use: ToolUseBlock,
    tool_response: ToolResponse,
    max_chars: int = 5000,
    suffix: str = "...[Text truncated due to length]...",
    tail_length: int = 50,
) -> ToolResponse:
    """
    Truncate overly long text responses

    Args:
        sandbox: AgentScope sandbox environment
        tool_use: Tool invocation block
        tool_response: Original tool response
        max_chars: Maximum allowed character count
        suffix: Suffix to append after truncation

    Returns:
        Truncated ToolResponse
    """
    for block in tool_response.content:
        if isinstance(block, dict) and "text" in block:
            text = block["text"]
            total_len = len(text)
            if total_len > max_chars:
                head_part = text[:max_chars]
                tail_part = text[-tail_length:] if tail_length > 0 else ""
                block["text"] = head_part + suffix + tail_part

    return tool_response


def _add_tool_postprocessing_func(toolkit: AliasToolkit) -> None:
    for tool_func, _ in toolkit.tools.items():
        if tool_func.startswith("run_ipython_cell"):
            funcs: list = [ansi_escape_post_hook]
            funcs.append(summarize_plt_chart_hook)
            toolkit.tools[tool_func].postprocess_func = partial(
                run_ipython_cell_post_hook,
                funcs,
                toolkit.sandbox,
            )


def add_ds_specific_tool(toolkit: AliasToolkit) -> None:
    # add summarize chart post processing for run_ipython_cell
    _add_tool_postprocessing_func(toolkit)

    # add spreadsheet to json tool
    toolkit.register_tool_function(
        partial(clean_messy_spreadsheet, toolkit=toolkit),
    )

    # add multimodal image understanding tools
    dash_scope_multimodal_tool_set = DashScopeMultiModalTools(
        sandbox=toolkit.sandbox,
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
    )
    toolkit.register_tool_function(
        partial(
            summarize_image,
            dash_scope_multimodal_tool_set=dash_scope_multimodal_tool_set,
        ),
    )
    toolkit.register_tool_function(
        partial(
            answer_question_about_image,
            dash_scope_multimodal_tool_set=dash_scope_multimodal_tool_set,
        ),
    )
