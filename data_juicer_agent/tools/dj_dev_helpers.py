# -*- coding: utf-8 -*-
"""
DataJuicer Development Tools

Tools for developing DataJuicer operators, including access to basic
documentation and example code for different operator types.
"""

import os
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

# DataJuicer home path - should be configured based on your environment
DATA_JUICER_PATH = os.getenv("DATA_JUICER_PATH", None)

BASIC_LIST_RELATIVE = [
    "data_juicer/ops/base_op.py",
    "docs/DeveloperGuide.md",
    "docs/DeveloperGuide_ZH.md",
]


def get_basic_files() -> ToolResponse:
    """Get basic DataJuicer development files content.

    Returns the content of essential files needed for DJ operator
    development:
    - base_op.py: Base operator class
    - DeveloperGuide.md: English developer guide
    - DeveloperGuide_ZH.md: Chinese developer guide

    Returns:
        ToolResponse: Combined content of all basic development files
    """

    global DATA_JUICER_PATH, BASIC_LIST_RELATIVE
    if DATA_JUICER_PATH is None:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "DATA_JUICER_PATH is not configured. Please ask the "
                        "user to provide the DATA_JUICER_PATH"
                    ),
                ),
            ],
        )

    try:
        comb_content = "# DataJuicer Operator Development Basic Files\n\n"

        for relative_path in BASIC_LIST_RELATIVE:
            file_path = os.path.join(DATA_JUICER_PATH, relative_path)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    file_n = os.path.basename(file_path)
                    comb_content += f"## {file_n}\n\n```"
                    flag = "python" if file_n.endswith(".py") else "markdown"
                    comb_content += f"{flag}\n"
                    comb_content += content
                    comb_content += "\n```\n\n"
                except Exception as e:
                    comb_content += (
                        f"## {os.path.basename(file_path)} (Read Failed)\n"
                    )
                    comb_content += f"Error: {str(e)}\n\n"

        return ToolResponse(
            content=[TextBlock(type="text", text=comb_content)],
        )

    except Exception as e:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error occurred while getting basic files: {str(e)}",
                ),
            ],
        )


async def get_operator_example(
    requirement_description: str,
    limit: int = 2,
) -> ToolResponse:
    """Get example operators based on requirement description using
    dynamic search.

    Args:
        requirement_description (str): Natural language description of
            the operator requirement
        limit (int): Maximum number of example operators to return
            (default: 2)

    Returns:
        ToolResponse: Example operator code and test files based on
            the requirement
    """

    global DATA_JUICER_PATH
    if DATA_JUICER_PATH is None:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "DATA_JUICER_PATH is not configured. Please ask the "
                        "user to provide the DATA_JUICER_PATH"
                    ),
                ),
            ],
        )

    try:
        # Import retrieve_ops from op_manager
        from .op_manager.op_retrieval import retrieve_ops

        # Query relevant operators using the requirement description
        # Use retrieval mode from environment variable if set
        retrieval_mode = os.environ.get("RETRIEVAL_MODE", "auto")
        tool_names = await retrieve_ops(
            requirement_description,
            limit=limit,
            mode=retrieval_mode,
        )

        if not tool_names:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "No relevant operators found for requirement: "
                            f"{requirement_description}\n"
                            "Please try with more specific keywords or "
                            "check if DATA_JUICER_PATH is properly "
                            "configured."
                        ),
                    ),
                ],
            )

        comb_content = (
            f"# Dynamic Operator Examples for: {requirement_description}\n\n"
        )
        comb_content += (
            f"Found {len(tool_names)} relevant operators (limit: {limit})\n\n"
        )

        # Process each found operator
        for i, tool_name in enumerate(tool_names[:limit]):
            comb_content += f"## {i+1}. {tool_name}\n\n"

            op_type = tool_name.split("_")[-1]

            operator_path = f"data_juicer/ops/{op_type}/{tool_name}.py"

            # Try to find operator source file
            full_path = os.path.join(DATA_JUICER_PATH, operator_path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    operator_code = f.read()

                comb_content += "### Source Code\n"
                comb_content += "```python\n"
                comb_content += operator_code
                comb_content += "\n```\n\n"
            else:
                comb_content += "**Note:** Source code file not found for"
                comb_content += f" `{tool_name}`.\n\n"

            test_path = f"tests/ops/{op_type}/test_{tool_name}.py"

            full_test_path = os.path.join(DATA_JUICER_PATH, test_path)
            if os.path.exists(full_test_path):
                with open(full_test_path, "r", encoding="utf-8") as f:
                    test_code = f.read()

                comb_content += "### Test Code\n"
                comb_content += f"**File Path:** `{test_path}`\n\n"
                comb_content += "```python\n"
                comb_content += test_code
                comb_content += "\n```\n\n"

            else:
                comb_content += (
                    f"**Note:** Test file not found for `{tool_name}`.\n\n"
                )

            comb_content += "---\n\n"

        return ToolResponse(
            content=[TextBlock(type="text", text=comb_content)],
        )

    except Exception as e:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Error occurred while getting operator examples: "
                        f"{str(e)}\n"
                        "Please check the requirement description and try "
                        "again."
                    ),
                ),
            ],
        )


def configure_data_juicer_path(data_juicer_path: str) -> ToolResponse:
    """Configure DataJuicer path.
    If the user provides the data_juicer_path, please use this method to
    configure it.

    Args:
        data_juicer_path (str): Path to DataJuicer installation

    Returns:
        ToolResponse: Configuration result
    """

    global DATA_JUICER_PATH

    data_juicer_path = os.path.expanduser(data_juicer_path)

    try:
        if not os.path.exists(data_juicer_path):
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "Specified DataJuicer path does not exist: "
                            f"{data_juicer_path}"
                        ),
                    ),
                ],
            )

        # Update global DATA_JUICER_PATH
        DATA_JUICER_PATH = data_juicer_path

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "DataJuicer path has been updated to: ",
                        f"{DATA_JUICER_PATH}",
                    ),
                ),
            ],
        )

    except Exception as e:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Error occurred while configuring DataJuicer path: "
                        f"{str(e)}"
                    ),
                ),
            ],
        )
