# -*- coding: utf-8 -*-
"""
Enhanced read_file tool function with offset and limit support.

This module provides an improved read_file tool that wraps the
original read_file functionality and adds support for
reading specific line ranges from files.
"""
import os
from typing import Optional

from loguru import logger

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from alias.agent.utils.constants import TMP_FILE_DIR
from alias.agent.tools.sandbox_util import (
    TEXT_EXTENSIONS,
    create_or_edit_workspace_file,
    create_workspace_directory,
)
from alias.runtime.alias_sandbox import AliasSandbox

TO_MARKDOWN_SUPPORT_MAPPING = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".pptx",
}


class ImprovedFileOperations:
    """
    A set of enhanced file system tools with sandbox.
    """

    def __init__(self, sandbox: AliasSandbox):
        """init with sandbox"""
        self.sandbox = sandbox

    async def read_file(  # pylint: disable=R0911,R0912
        self,
        file_path: str,
        offset: int = 0,
        limit: Optional[int] = 50,
    ) -> ToolResponse:
        """
        Read a file with optional line offset and limit support.
        Support reading all kinds of text file, plus files with extensions in
        the following list:
        [".pdf", ".docx", ".doc", ".xlsx" and ".pptx"]

        Args:
            file_path (str): The absolute path to the file to read
            offset (int, optional):
                The line number to start reading from (starting from 0).
                Default is 0.
            limit (int, optional):
                The number of lines to read. Default to 50.
                If set to `None`, then it will read all content after `offset`.

        Returns:
            ToolResponse:
                A ToolResponse containing the file content or
                error information. The content includes line numbers
                when offset/limit are used.
        """
        try:
            # Validate input parameters
            if offset is not None and offset < 0:
                return ToolResponse(
                    metadata={"success": False, "error": "Invalid offset"},
                    content=[
                        TextBlock(
                            type="text",
                            text="Error: offset must be >= 0",
                        ),
                    ],
                )

            if limit is not None and limit < 1:
                return ToolResponse(
                    metadata={"success": False, "error": "Invalid limit"},
                    content=[
                        TextBlock(
                            type="text",
                            text="Error: limit must be >= 1",
                        ),
                    ],
                )

            # If no toolkit provided, we can't proceed
            if self.sandbox is None:
                return ToolResponse(
                    metadata={
                        "success": False,
                        "error": "No sandbox provided",
                    },
                    content=[
                        TextBlock(
                            type="text",
                            text="Error: No sandbox provided to "
                            "call the original read_file tool",
                        ),
                    ],
                )

            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension in TEXT_EXTENSIONS:
                # First, read the entire file using the original read_file tool
                params = {
                    "path": file_path,
                }
                # Call the original read_file tool
                tool_res = self.sandbox.call_tool(
                    name="read_file",
                    arguments=params,
                )
            elif file_extension in TO_MARKDOWN_SUPPORT_MAPPING:
                tool_res = _transfer_to_markdown_text(file_path, self.sandbox)
            else:
                tool_res = {}

            # Extract content from the tool response
            if (
                tool_res.get("isError", True)
                and len(tool_res.get("content", [])) > 0
            ):
                return ToolResponse(
                    metadata={
                        "success": False,
                        "error": "Error when read file",
                    },
                    content=tool_res.get("content", []),
                )
            elif (
                tool_res.get("isError", True)
                and len(tool_res.get("content", [])) == 0
            ):
                return ToolResponse(
                    metadata={"success": False, "error": "Empty response"},
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Fail to read file on path {file_path}",
                        ),
                    ],
                )

            # Get the text content from the first content block
            full_content = ""
            for block in tool_res.get("content", []):
                if isinstance(block, dict) and "text" in block:
                    full_content += block["text"] + "\n"

            # Split into lines
            lines = full_content.splitlines(keepends=True)
            total_lines = len(lines)

            # If no offset/limit specified, return entire file
            if offset is None and limit is None:
                return ToolResponse(
                    metadata={"success": True, "total_lines": total_lines},
                    content=[
                        TextBlock(
                            type="text",
                            text=full_content,
                        ),
                    ],
                )

            # Handle offset and limit
            start_line = offset or 0  # 0-based index
            end_line = start_line + (limit or total_lines)

            # Validate range
            if start_line >= total_lines:
                return ToolResponse(
                    metadata={"success": False, "error": "Invalid range"},
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Error: Start line {offset} is "
                            f"beyond file length ({total_lines} lines).",
                        ),
                    ],
                )

            # Clamp end_line to file length
            end_line = min(end_line, total_lines)

            # Extract the requested lines
            selected_lines = lines[start_line:end_line]

            content = "".join(selected_lines)

            # Add summary information
            summary = (
                f"Read lines {start_line}-{end_line} of "
                f"{total_lines} total lines from '{file_path}'"
            )

            # save as markdown
            return_content = [
                TextBlock(
                    type="text",
                    text=content,
                ),
                TextBlock(
                    type="text",
                    text=summary,
                ),
            ]
            if file_extension in TO_MARKDOWN_SUPPORT_MAPPING:
                file_name_with_ext = os.path.basename(file_path)
                filename_without_ext = os.path.splitext(file_name_with_ext)[0]
                file_path = os.path.join(
                    TMP_FILE_DIR,
                    filename_without_ext + ".md",
                )
                create_workspace_directory(self.sandbox, TMP_FILE_DIR)
                create_or_edit_workspace_file(
                    self.sandbox,
                    file_path,
                    full_content,
                )
                return_content.append(
                    TextBlock(
                        type="text",
                        text=(
                            "NOTICE: "
                            "The (full) file is converted as markdown file"
                            " and saved completely at: "
                            f"{file_path}"
                        ),
                    ),
                )

            return ToolResponse(
                metadata={
                    "success": True,
                    "total_lines": total_lines,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                    "lines_read": len(selected_lines),
                },
                content=return_content,
            )
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return ToolResponse(
                metadata={"success": False, "error": str(e)},
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error reading file '{file_path}': {str(e)}",
                    ),
                ],
            )


def _transfer_to_markdown_text(
    file_path: str,
    sandbox: AliasSandbox = None,
) -> dict:
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in TO_MARKDOWN_SUPPORT_MAPPING:
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": f"File extension '{ext}' not supported in "
                    f"{TO_MARKDOWN_SUPPORT_MAPPING}.",
                },
            ],
        }

    params = {
        "uri": "file:" + file_path,
    }
    try:
        result = sandbox.call_tool(  # pylint: disable=W0621
            name="convert_to_markdown",
            arguments=params,
        )
        content = result.get("content", [])
        new_content = []
        for i, _block in enumerate(content):
            if content[i].get("text", "").startswith("Converted content:"):
                continue
            if content[i].get("text", "").startswith("Output file:"):
                continue
            new_content.append(result["content"][i])

        result["content"] = new_content
    except Exception as e:
        result = {
            "isError": True,
            "error": str(e),
        }

    return result
