# -*- coding: utf-8 -*-
import os
from agentscope.tool import ToolResponse
from alias.agent.agents.ds_agent_utils import get_prompt_from_file
from alias.agent.agents.ds_agent_utils.ds_config import (
    PROMPT_DS_BASE_PATH,
    VL_MODEL_NAME,
)


def summarize_image(
    dash_scope_multimodal_tool_set,
    image_path: str,
) -> ToolResponse:
    """
    Use a vision-language model to extract all information from the image,
    including text, objects, layout relationships, chart conclusions, etc.

    Args:
        image_path (str): Path to the image file, e.g., '/workspace/image.jpg'
    """

    summary_prompt = get_prompt_from_file(
        os.path.join(
            PROMPT_DS_BASE_PATH,
            "_summary_image_prompt.md",
        ),
        False,
    )

    return dash_scope_multimodal_tool_set.dashscope_image_to_text(
        image_url=image_path,
        prompt=summary_prompt,
        model=VL_MODEL_NAME,
    )


def answer_question_about_image(
    dash_scope_multimodal_tool_set,
    image_path: str,
    question: str,
) -> ToolResponse:
    """
    Answer questions about image content using a vision-language model,
    based on the provided image and question.

    Args:
        image_path (str): Path to the image file,
                        e.g., '/workspace/image.jpg'
        question (str): A natural language question about the image content,
                        e.g., "How many cats are in the image?"
    """
    qa_prompt = (
        f"Question: {question}\n"
        "Please answer accurately based on the image content. "
        "Keep your response concise and clear."
    )

    return dash_scope_multimodal_tool_set.dashscope_image_to_text(
        image_url=image_path,
        prompt=qa_prompt,
        model=VL_MODEL_NAME,
    )
