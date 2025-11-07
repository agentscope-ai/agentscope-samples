# -*- coding: utf-8 -*-
"""The utilities for deep research agent"""
import json
import os
import re
from typing import Any, Sequence, Type, Union

from pydantic import BaseModel

from agentscope.tool import Toolkit, ToolResponse

TOOL_RESULTS_MAX_WORDS = 30000


def get_prompt_from_file(
    file_path: str,
    return_json: bool,
) -> Union[str, dict]:
    """Get prompt from file"""
    with open(os.path.join(file_path), "r", encoding="utf-8") as f:
        if return_json:
            prompt = json.load(f)
        else:
            prompt = f.read()
    return prompt


async def count_by_words(sentence: str) -> float:
    """Count words of a sentence"""
    words = re.findall(
        r"\w+|[^\w\s]",
        sentence,
        re.UNICODE,
    )

    word_count = 0.0
    for word in words:
        if re.match(r"\w+", word):
            word_count += 1.0
    return word_count


def generate_structure_output(**kwargs: Any) -> ToolResponse:
    """Generate a structured output tool response.

    This function is designed to be used as a tool function for generating
    structured outputs. It takes arbitrary keyword arguments and wraps them
    in a ToolResponse with metadata.

    Args:
        **kwargs: Arbitrary keyword arguments that should match the format
            of the expected structured output specification.

    Returns:
        ToolResponse: A tool response object with empty content and the
            provided kwargs as metadata.

    Note:
        The input parameters should be in the same format as the specification
        and include as much detail as requested by the calling context.
    """
    return ToolResponse(content=[], metadata=kwargs)


def get_dynamic_tool_call_json(data_model_type: Type[BaseModel]) -> list[dict]:
    """Generate JSON schema for dynamic tool calling with a given data model.

    Creates a temporary toolkit, registers the structure output function,
    and configures it with the specified data model to generate appropriate
    JSON schemas for tool calling.

    Args:
        data_model_type: A Pydantic BaseModel class that defines the expected
            structure of the tool output.

    Returns:
        A dictionary containing the JSON schemas for the configured tool,
        suitable for use in API calls that support structured outputs.

    Example:
        class MyModel(BaseModel):
            name: str
            value: int

        schema = get_dynamic_tool_call_json(MyModel)
    """
    tmp_toolkit = Toolkit()
    tmp_toolkit.register_tool_function(generate_structure_output)
    tmp_toolkit.set_extended_model(
        "generate_structure_output",
        data_model_type,
    )
    return tmp_toolkit.get_json_schemas()


def get_structure_output(blocks: list | Sequence) -> dict:
    """Extract structured output from a sequence of blocks.

    Processes a list or sequence of blocks to extract tool use outputs
    and combine them into a single dictionary. This is typically used
    to parse responses from language models that include tool calls.

    Args:
        blocks: A list or sequence of blocks that may contain tool use
            information. Each block should be a dictionary with 'type'
            and 'input' keys for tool use blocks.

    Returns:
        A dictionary containing the combined input data from all tool
        use blocks found in the input sequence.

    Example:
        blocks = [
            {"type": "tool_use", "input": {"name": "test"}},
            {"type": "text", "content": "Some text"},
            {"type": "tool_use", "input": {"value": 42}}
        ]
        result = PromptBase.get_structure_output(blocks)
        # result: {"name": "test", "value": 42}
    """

    dict_output = {}
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            dict_output.update(block.get("input", {}))
    return dict_output


def load_prompt_dict() -> dict:
    """Load prompt into dict"""
    prompt_dict = {}
    cur_dir = os.path.dirname(os.path.abspath(__file__))

    prompt_dict["add_note"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_worker_additional_sys_prompt.md",
        ),
        return_json=False,
    )

    prompt_dict["tool_use_rule"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_tool_usage_rules.md",
        ),
        return_json=False,
    )

    prompt_dict["decompose_sys_prompt"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_decompose_subtask.md",
        ),
        return_json=False,
    )

    prompt_dict["expansion_sys_prompt"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_deeper_expansion.md",
        ),
        return_json=False,
    )

    prompt_dict["summarize_sys_prompt"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_inprocess_report.md",
        ),
        return_json=False,
    )

    prompt_dict["reporting_sys_prompt"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_deepresearch_summary_report.md",
        ),
        return_json=False,
    )

    prompt_dict["reflect_sys_prompt"] = get_prompt_from_file(
        file_path=os.path.join(
            cur_dir,
            "built_in_prompt/prompt_reflect_failure.md",
        ),
        return_json=False,
    )

    prompt_dict["reasoning_prompt"] = (
        "## Current Subtask:\n{objective}\n"
        "## Working Plan:\n{plan}\n"
        "{knowledge_gap}\n"
        "## Research Depth:\n{depth}"
    )

    prompt_dict["previous_plan_inst"] = (
        "## Previous Plan:\n{previous_plan}\n"
        "## Current Subtask:\n{objective}\n"
    )

    prompt_dict["max_depth_hint"] = (
        "The search depth has reached the maximum limit. So the "
        "current subtask can not be further decomposed and "
        "expanded anymore. I need to find another way to get it "
        "done no matter what."
    )

    prompt_dict["expansion_inst"] = (
        "Review the web search results and identify whether "
        "there is any information that can potentially help address "
        "checklist items or fulfill knowledge gaps of the task, "
        "but whose content is limited or only briefly mentioned.\n"
        "**Ultimate Task Checklist:**\n{checklist}\n"
        "**Current Knowledge Gaps:**\n{knowledge_gaps}\n"
        "**Current Search Query:**\n{search_query}\n"
        "**Search Results:**\n{search_results}\n"
        "**Output:**\n"
    )

    prompt_dict["follow_up_judge_sys_prompt"] = (
        "1. You have conducted a web search and extraction "
        "to obtain additional information. Now, you assess whether, "
        "after both the web search and extraction process, "
        "the information content is adequate to "
        "address the given task. Mark those items in `Current Knowledge Gaps` "
        " as [x] if there is information for that. \n"
        "2. If the gathered information inspires you, "
        "and you believe diving deeper following this can help providing more "
        "comprehensive analysis of the user query, "
        "formulate the dive-deeper plan in `subtask` field; "
        "otherwise, you can leave it empty."
    )

    prompt_dict[
        "retry_hint"
    ] = "Something went wrong when {state}. I need to retry."

    prompt_dict["need_deeper_hint"] = (
        "The information is insufficient and I need to make deeper "
        "research to fill the knowledge gap."
    )

    prompt_dict[
        "sufficient_hint"
    ] = "The information after web search and extraction is sufficient enough!"

    prompt_dict["no_result_hint"] = (
        "I mistakenly called the `summarize_intermediate_results` tool as "
        "there exists no milestone result to summarize now."
    )

    prompt_dict["summarize_hint"] = (
        "Based on your work history above, examine which step in the "
        "following working plan has been completed. Mark the fulfill "
        "knowledge gap with [x] (e.g., [x] Search yyy; [x] learn zzz) "
        "and leave the uncompleted steps unchanged. You MUST return only "
        "the updated plan, preserving exactly the same format as the "
        "original plan. Do not include any explanations, reasoning, "
        "or section headers such as '## Knowledge Gaps:', just output the"
        "updated status itself."
        "\n\n## Knowledge Gaps:\n{knowledge_gaps}"
    )

    prompt_dict["summarize_inst"] = (
        "**Ultimate Task:**\n{objective}\n"
        "**Ultimate Checklist:**\n{root_gaps}\n"
        "**Knowledge Gaps:**\n{cur_gaps}\n"
        "**Gathered Information:**\n{tool_result}"
    )

    prompt_dict["update_report_hint"] = (
        "To condense the gathered information, I have replaced the "
        "original bulk search results from the research phase with the "
        "following report that consolidates and summarizes the essential "
        "findings:\n {intermediate_report}\n\n"
        "Such report has been saved to the {report_path}. "
    )

    prompt_dict["save_report_hint"] = (
        "The milestone results of the current item in working plan "
        "are summarized into the following report:\n{intermediate_report}"
    )

    prompt_dict["reflect_instruction"] = (
        "## Work History:\n{conversation_history}\n"
        "## Current Objective:\n{objective}\n"
        "## Working Plan:\n{plan}\n"
        "## Knowledge Gaps:\n{knowledge_gaps}\n"
    )

    prompt_dict["subtask_complete_hint"] = (
        "Subtask ‘{cur_obj}’ is completed. Now the current subtask "
        "fallbacks to '{next_obj}'"
    )

    return prompt_dict
