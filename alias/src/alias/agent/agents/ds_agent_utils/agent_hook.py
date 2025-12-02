# -*- coding: utf-8 -*-
import json
from typing import Any, TYPE_CHECKING
import re
import os
from pathlib import Path
from string import Template
from loguru import logger
from agentscope.message import Msg, TextBlock
from .ds_config import PROMPT_DS_BASE_PATH


if TYPE_CHECKING:
    from alias.agent.agents._data_science_agent import DataScienceAgent
else:
    DataScienceAgent = "alias.agent.agents.DataScienceAgent"


def parse_selected_files_from_response(response_text: str) -> list[str]:
    """
    Extract the JSON file list from the response text containing
    "Found files relevant to the query:", specifically from
     the ```...``` code block.

    Works correctly even if arbitrary content precedes the key sentence.
    """
    # Step 1: Locate content after the key sentence
    # Use non-greedy matching to find the part after
    # "Found files relevant to the query:"
    match = re.search(
        r"Found files relevant to the query:"
        r"\s*```(?:json)?\s*([\s\S]*?)\s*```",
        response_text,
    )

    if not match:
        return []  # No match found

    # Step 2: Parse JSON
    try:
        files_list = json.loads(match.group(1))
        # Ensure the result is a list of strings
        if isinstance(files_list, list) and all(
            isinstance(f, str) for f in files_list
        ):
            return files_list
        else:
            return []
    except json.JSONDecodeError:
        return []


def parse_user_message_and_files(
    msg: str,
) -> tuple[str, list[str], str | None]:
    """
    Parse the following from a user message string:
    - Original message content (with file list sections removed)
    - List of file paths (normalized to /workspace/... format)

    Supports two formats:
    1. "\n\nUser uploaded files:\n/path1\n/path2"
    2. "User Provided Attached Files:\n\t/path1\n\t/path2"

    Returns:
        (original_message: str, file_list: list[str], file_type: str | None)
    """
    if not msg:
        return "", [], None

    # Use a set to collect all file paths (automatic deduplication)
    file_paths = set()

    # ========== Handle Format 1: "User uploaded files:" ==========
    # Match from "User uploaded files:" to end of string
    pattern1 = r"(\n\nUser uploaded files:\s*\n(?:[^\n]*\n?)*)"
    match1 = re.search(pattern1, msg)
    if match1:
        full_match = match1.group(0)
        # Extract file block content (remove header line)
        files_block = (
            full_match.split("\n", 3)[-1]
            if full_match.count("\n") >= 3
            else ""
        )
        for line in files_block.strip().split("\n"):
            path = line.strip()
            if path and not path.startswith((" ", "\t", "-", "*", "User")):
                # Normalize path
                # if not path.startswith("/workspace"):
                #     path = "/workspace/" + path.lstrip("/")
                file_paths.add(path)
        # Remove this entire block from the original message
        msg = msg.replace(full_match, "", 1)

    # ========== Handle Format 2: "User Provided Attached Files:" ==========
    pattern2 = r"(User Provided Attached Files:\s*\n(?:\s*[^\n]*\n?)*)"
    match2 = re.search(pattern2, msg)
    if match2:
        full_match = match2.group(0)
        # Extract file block: process line by line, skip header
        lines = full_match.strip().split("\n")
        for line in lines[1:]:  # Skip the "User Provided Attached Files:" line
            path = line.strip().lstrip("\t -")
            if path and not path.startswith(("User", "```", "#", "//")):
                # if not path.startswith("/workspace"):
                #     path = "/workspace/" + path.lstrip("/")
                file_paths.add(path)
        # Remove this entire block from the original message
        msg = msg.replace(full_match, "", 1)

    # Clean up original message: remove extra blank lines
    original_message = msg.strip()

    file_type = (
        "\n\nUser uploaded files:\n"
        if match1
        else "\n\nUser Provided Attached Files:\n"
        if match2
        else None
    )

    # Return original message and sorted file list (for consistent testing)
    return original_message, sorted(file_paths), file_type


async def files_filter_pre_reply_hook(
    self: DataScienceAgent,
    kwargs: dict[str, Any],  # pylint: disable=W0613
) -> None:
    """Hook for loading user input to planner notebook"""
    messages = await self.memory.get_memory()
    latest_index = len(messages) - 1
    user_input = messages[-1].content[0]["text"]
    query, files_list, file_type = parse_user_message_and_files(user_input)

    # Even if the user only uploaded supplementary files in this interaction,
    # We will also check whether the previously uploaded files are relevant
    # to the question.
    self.uploaded_files = list(
        set(files_list) | set(getattr(self, "uploaded_files", [])),
    )

    if len(self.uploaded_files) < 100:
        logger.info(
            "Scalable files filtering: not enough files to filter.",
        )
    else:
        safe_query = json.dumps(query)
        safe_api_key = json.dumps(os.getenv("DASHSCOPE_API_KEY", ""))

        file_path = Path(PROMPT_DS_BASE_PATH) / "_files_filter_code.txt"
        with open(file_path, encoding="utf-8") as f:
            files_filter_code = f.read()

        template = Template(
            """
query = $query
files_list = $files_list
api_key = $api_key
await files_filter(query, files_list, api_key=api_key)
        """,
        )

        files_filter_code += template.substitute(
            query=safe_query,
            files_list=repr(self.uploaded_files),
            api_key=safe_api_key,
        )

        response = self.toolkit.sandbox.call_tool(
            "run_ipython_cell",
            {"code": files_filter_code},
        )
        selected_files = parse_selected_files_from_response(
            response["content"][0]["text"],
        )

        await self.memory.delete(latest_index)

        file_type_str = file_type if file_type is not None else ""
        text_content = query + file_type_str + "\n".join(selected_files)

        await self.memory.add(
            Msg(
                "user",
                content=[
                    TextBlock(type="text", text=text_content),
                ],
                role="user",
            ),
        )

        logger.info(
            "Use scalable files filtering: selected relevant files:"
            + "\n".join(selected_files),
        )
