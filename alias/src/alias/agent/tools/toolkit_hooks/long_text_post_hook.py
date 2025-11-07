# -*- coding: utf-8 -*-
import json
import os.path
import uuid
import textwrap

from agentscope.tool import ToolResponse
from agentscope.message import ToolUseBlock, TextBlock

from alias.agent.utils.constants import TMP_FILE_DIR
from alias.agent.tools.sandbox_util import (
    create_or_edit_workspace_file,
    create_workspace_directory,
)


class LongTextPostHook:
    def __init__(self, sandbox):
        self.sandbox = sandbox

    def truncate_and_save_response(  # pylint: disable=R1710
        self,
        tool_use: ToolUseBlock,  # pylint: disable=W0613
        tool_response: ToolResponse,
    ) -> ToolResponse:
        """Post-process tool responses to prevent content overflow.

        This function ensures that tool responses don't exceed a predefined
        budget to prevent overwhelming the model with too much information.
        It truncates text content while preserving the structure of
        the response.

        Args:
            tool_use: The tool use block that triggered the response (unused).
            tool_response: The tool response to potentially truncate.

        Note:
            The budget is set to approximately 80K tokens
            (8194 * 10 characters) to ensure responses remain
            manageable for the language model.
        """
        # Set budget to prevent overwhelming the model with too much content
        budget = 8194 * 10  # Approximately 80K tokens of content
        append_hint = "\n\n[Content is too long and truncated....]"

        new_tool_response = ToolResponse(
            id=tool_response.id,
            stream=tool_response.stream,
            is_last=tool_response.is_last,
            is_interrupted=tool_response.is_interrupted,
            content=[],
        )
        if isinstance(tool_response.content, list):
            save_text_block = None
            for _i, block in enumerate(tool_response.content):
                if block["type"] == "text":
                    text = block["text"]
                    text_len = len(text)

                    # If this block exceeds remaining budget, truncate it
                    if text_len > budget:
                        # Calculate truncation threshold
                        # (80% of proportional budget)
                        threshold = int(budget * 0.85)
                        # save the original response
                        tmp_file_name_prefix = tool_use.get("name", "")
                        save_text_block = self._save_tmp_file(
                            tmp_file_name_prefix,
                            tool_response.content,
                        )
                        new_tool_response.append = (
                            text[:threshold] + append_hint
                        )
                        new_tool_response.content.append(
                            TextBlock(
                                type="text",
                                text=text[:threshold] + append_hint,
                            ),
                        )
                    else:
                        new_tool_response.content.append(block)
                    budget -= text_len
                    if budget <= 0 and save_text_block:
                        new_tool_response.content.append(save_text_block)
            return new_tool_response
        elif isinstance(tool_response.content, str):
            text_len = len(tool_response.content)
            text = tool_response.content
            if text_len > budget:
                tmp_file_name_prefix = tool_use.get("name", "")
                save_text_block = self._save_tmp_file(
                    tmp_file_name_prefix,
                    tool_response.content,
                )
                # Calculate truncation threshold (80% of proportional budget)
                threshold = int(budget / text_len * len(text) * 0.8)
                tool_response.content = text[:threshold] + append_hint
                tool_response.content = [
                    TextBlock(type="text", text=tool_response.content),
                    save_text_block,
                ]
                return tool_response
            return tool_response

    def _save_tmp_file(self, save_file_name_prefix: str, content: list | str):
        create_workspace_directory(self.sandbox, TMP_FILE_DIR)
        save_file_name = (
            save_file_name_prefix
            + "-"
            + str(
                uuid.uuid4().hex[:8],
            )
        )
        file_path = os.path.join(TMP_FILE_DIR, save_file_name)
        json_str = json.dumps(content, ensure_ascii=False, indent=2)
        wrapped = "\\n".join(
            [textwrap.fill(line, width=500) for line in json_str.split("\\n")],
        )
        create_or_edit_workspace_file(
            self.sandbox,
            file_path,
            wrapped,
        )
        return TextBlock(
            type="text",
            text=f"Dump the complete long file at {file_path}. "
            "Don't try to read the complete file directly. "
            "Use `grep -C 10 'YOUR_PATTERN' {file_path}` or "
            "other bash command to extract "
            "useful information.",
        )
