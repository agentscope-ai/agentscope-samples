# -*- coding: utf-8 -*-
import json
import os
import base64
import asyncio
from io import BytesIO
from typing import Dict, List
import pandas as pd

from pydantic import BaseModel, Field

from loguru import logger
from agentscope_runtime.sandbox.box.sandbox import Sandbox
from agentscope._utils._common import _create_tool_from_base_model
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock, Msg
from alias.agent.tools.sandbox_util import (
    get_workspace_file,
    create_or_edit_workspace_file,
)
from alias.agent.agents.ds_agent_utils import get_prompt_from_file


from alias.agent.agents.ds_agent_utils.utils import model_call_with_retry
from alias.agent.agents.ds_agent_utils.ds_config import (
    PROMPT_DS_BASE_PATH,
    MODEL_FORMATTER_MAPPING,
    MODEL_CONFIG_NAME,
)

convert_prompt = get_prompt_from_file(
    os.path.join(
        PROMPT_DS_BASE_PATH,
        "_spreadsheet_to_json.md",
    ),
    False,
)


class RelTableModel(BaseModel):
    tables: Dict[str, List[List]] = Field(
        default_factory=dict,
        description=(
            "Extracted structured tables dictionary. "
            "Each key is a table name (e.g., 'employee_records'), "
            "and each value is a 2D list: the first sublist "
            "contains column names, "
            "and subsequent sublists are data rows. "
            "The special key '__metadata' stores non-tabular "
            "descriptive text as a list of strings."
        ),
        json_schema_extra={
            "example": {
                "employee_records": [
                    [
                        "Name",
                        "Employee ID",
                        "Department",
                        "Hire Date",
                        "Monthly Salary (¥)",
                        "Regular Status",
                    ],
                    [
                        "Li Ming",
                        "E005",
                        "Tech Dept",
                        "2021-06-12",
                        18000,
                        "Yes",
                    ],
                    [
                        "Wang Fang",
                        "E006",
                        "Sales Dept",
                        "2022-03-08",
                        15000,
                        "Yes",
                    ],
                ],
                "project_performance": [
                    [
                        "Evaluation Item",
                        "Weight (%)",
                        "Score (5-point)",
                        "Met Target?",
                    ],
                    ["Technical Completion", 30, 4.6, "Yes"],
                    ["Schedule Control", 25, 4.2, "Yes"],
                ],
                "__metadata": [
                    "Data Source: Finance & Operations Dept",
                    (
                        "Note: No major returns this quarter; "
                        "employee data excludes interns."
                    ),
                ],
            },
        },
    )


async def to_relation_table(data):
    """
    Convert spreadsheet data to structured relational tables using LLM

    Args:
        data: List of rows where each row contains index and data values
        model_name (str): Model name to use, default is "qwen-max"

    Returns:
        dict: Dictionary of structured tables with table names as keys and
        2D arrays as values (first row = headers, subsequent rows = data),
        returns None on failure
    """
    system_prompt = convert_prompt
    user_content = "\n".join(
        "\t".join(list(map(str, [idx] + d))) for idx, d in enumerate(data)
    )

    try:
        format_tool = _create_tool_from_base_model(RelTableModel)

        # Call LLM
        model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
        res = await model_call_with_retry(
            model,
            formatter,
            [
                Msg("system", system_prompt, "system"),
                Msg("user", user_content, "user"),
            ],
            tool_json_schemas=[format_tool],
            tool_choice=format_tool["function"]["name"],
        )

        tables = res.content[-1]["input"]["tables"]
        return tables
    except Exception as e:
        logger.error(f"LLM processing failed: {e}")
        return None


def get_excel_file_from_workspace(sandbox: Sandbox, file_path: str) -> dict:
    """
    Read specified file from sandbox /workspace and parse its content
    as Excel sheets.

    Args:
        sandbox (AliasSandbox): Sandbox instance
        file_path (str): File path within workspace
                        (must start with /workspace/)

    Returns:
        dict: Dictionary with sheet names as keys and pandas DataFrames
              as values
    """

    # Call underlying function to get base64-encoded content
    b64_content = get_workspace_file(sandbox, file_path)
    clean_b64 = b64_content.strip().replace("\n", "").replace("\r", "")
    excel_bytes = base64.b64decode(clean_b64)

    # Read all sheets
    all_sheets = pd.read_excel(BytesIO(excel_bytes), sheet_name=None)
    return all_sheets


def get_sheet_meta_data(excel_file):
    """
    Extract the number of rows in each sheet and the maximum sheet row count.

    Args:
        excel_file: ExcelFile object containing multiple sheets

    Returns:
        tuple: A tuple containing:
            - sheet_rows (dict): Dictionary mapping sheet names to row counts
            - max_rows (int): Maximum number of rows among all sheets
    """
    sheet_rows = {}

    for sheet_name, df in excel_file.items():
        sheet_rows[sheet_name] = len(df)

    max_rows = max(sheet_rows.values()) if sheet_rows else 0

    return sheet_rows, max_rows


def get_sheet_data(excel_file):
    """
    Extract the content in each sheet and convert to list format.

    Args:
        excel_file (dict): Dictionary with sheet names as keys and pandas
        DataFrames as values

    Returns:
        dict: Dictionary with sheet names as keys and 2D list as values, where:
            - First row contains column headers
            - Subsequent rows contain data values
    """
    result = {}
    for name, df in excel_file.items():
        table = [df.columns.tolist()] + df.values.tolist()
        result[name] = table
    return result


def write_json_to_workspace(
    sandbox: Sandbox,
    file_path: str,
    data: dict,
) -> dict:
    """
    Write a Python dictionary (JSON-compatible) to a specified file in
    the sandbox /workspace.

    Args:
        sandbox (AliasSandbox): Sandbox instance
        file_path (str): Target file path (must start with /workspace/)
        data (dict): JSON data to be written

    Returns:
        dict: Raw return result from sandbox tool call
            (including isError field, etc.)

    Raises:
        ValueError: If input data is not JSON serializable
    """
    try:
        # Serialize to JSON string (indented for readability, optional)
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except TypeError as e:
        raise ValueError(f"Input data is not JSON serializable: {e}") from e

    # Call write function
    result = create_or_edit_workspace_file(sandbox, file_path, json_str)
    return result


async def extract_structured_tables_with_llms(original_data):
    """
    Use LLM to convert raw spreadsheet data from multiple sheets into
    structured relational tables.

    Args:
        original_data (dict): Dictionary with sheet names as keys and
        raw data as values

    Returns:
        dict: Dictionary with sheet names as keys and structured table
            data as values, where each structured table follows the
            RelTableModel format
    """

    futures = [to_relation_table(data) for data in original_data.values()]

    converted_data_list = await asyncio.gather(*futures)
    converted_data = dict(zip(original_data.keys(), converted_data_list))

    return converted_data


def extract_raw_valid_data(original_data):
    """
    Extract non-empty rows from each sheet and organize them into a
    structured JSON format.

    This function processes each sheet by extracting rows with non-null
    values and organizing them by row index, filtering out completely
    empty rows.

    Args:
        original_data (dict): Dictionary with sheet names as keys and
                              pandas DataFrames as values

    Returns:
        dict: Nested dictionary structure where:
            - Top-level keys are sanitized sheet names (alphanumeric only)
            - Second-level keys are row identifiers in format "Row {index}"
            - Values are dicts of non-null cell data per row.
    """
    combined_json = {}
    for sheet_name, df in original_data.items():
        sheet_data = {}
        for i in range(df.shape[0]):
            row = df.iloc[i]
            non_null = row.dropna()
            if len(non_null) > 0:
                sheet_data[f"Row {i}"] = non_null.to_dict()
        safe_sheet_name = "".join(c for c in sheet_name if c.isalnum())
        combined_json[safe_sheet_name] = sheet_data

    return combined_json


async def clean_messy_spreadsheet(toolkit, file: str) -> ToolResponse:
    """
    Clean the given messy spreadsheet and convert it into a readable JSON
    representation.

    Args:
        file (`str`):
            Path to the spreadsheet
    """

    try:
        # Step 1: Read and display content of all sheets
        excel_file = get_excel_file_from_workspace(toolkit.sandbox, file)
        _, max_rows = get_sheet_meta_data(excel_file)

        output_path = file.rsplit(".", 1)[0] + ".json"
        if max_rows < 150:
            original_data = get_sheet_data(excel_file)
            converted_data = await extract_structured_tables_with_llms(
                original_data,
            )
            response = (
                "The messy file has been converted to a readable JSON file"
                f" at {output_path}."
                "\n\nThe JSON structure is organized as follows:"
                "\n\nThe top-level keys represent sheet names."
                "\nUnder each sheet, the value is an extracted structured "
                "tables dictionary, where:"
                "\nEach key is a table name (e.g., 'employee_records')."
                "\nEach value is a 2D list:"
                "\nThe first sublist contains column names."
                "\nSubsequent sublists are data rows."
                "\nA special key '__metadata' stores any non-tabular "
                "descriptive text as a list of strings."
                "\nYou should now access the JSON file, interpret its content "
                "based on this structure, and extract the data needed for "
                "your task."
            )
        else:
            converted_data = extract_raw_valid_data(excel_file)
            response = (
                "The messy file has been converted to a readable JSON file"
                f" at {output_path}."
                "\n\nThe JSON structure is organized as follows:"
                "\n\nThe top-level keys represent sheet names."
                "\nUnder each sheet, the value is a dictionary capturing "
                "non-empty rows from that sheet:"
                '\nKey: String in the format "Row i", where i is the original '
                "zero-based row index in the Excel sheet."
                "\nValue: A dictionary containing only the non-null cells in"
                " that row, where:\nKeys are column names,"
                "\nValues are the corresponding cell values."
                "\nYou should now access the JSON file, interpret its content "
                "based on this structure, and extract the data needed for your"
                " task."
            )

        write_json_to_workspace(toolkit.sandbox, output_path, converted_data)

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=response,
                ),
            ],
        )

    except Exception:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Fail to convert the messy file to readable format."
                        "Try alternative ways to handle the file. "
                    ),
                ),
            ],
        )
