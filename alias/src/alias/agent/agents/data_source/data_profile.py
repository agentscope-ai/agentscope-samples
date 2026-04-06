# -*- coding: utf-8 -*-
import os
import base64
import tempfile
from typing import Any, Dict
from io import BytesIO
from pathlib import Path
import requests

from alias.agent.agents.data_source._typing import SourceType
from alias.agent.agents.data_source._data_profiler_factory import (
    DataProfilerFactory,
)
from alias.agent.tools.sandbox_util import (
    get_workspace_file,
)
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox
from alias.agent.utils.llm_call_manager import (
    LLMCallManager,
)


def _get_binary_buffer(
    sandbox: AliasSandbox,
    file_url: str,
):
    if file_url.startswith(("http://", "https://")):
        response = requests.get(file_url)
        response.raise_for_status()
        buffer = BytesIO(response.content)
    else:
        buffer = BytesIO(
            base64.b64decode(get_workspace_file(sandbox, file_url)),
        )
    return buffer


def _copy_file_from_sandbox_with_original_name(
    sandbox: AliasSandbox,
    file_path: str,
) -> str:
    """
    Copies a file from the sandbox environment
    or a URL to a local temporary file.

    Args:
        sandbox (AliasSandbox): The sandbox environment instance.
        path (str): Source path or URL.

    Returns:
        str: The path to the local temporary file.
    """
    # Handle different types of file URLs
    if file_path.startswith(("http://", "https://")):
        # For web URLs, use the URL directly
        file_source = file_path
    else:
        # For local files, save to a temporary file
        file_buffer = _get_binary_buffer(
            sandbox,
            file_path,
        )
        # Create a temporary file with the same name as the original file
        temp_dir = tempfile.mkdtemp()
        target_file_name = os.path.basename(file_path)
        full_path = Path(temp_dir) / target_file_name
        with open(full_path, "wb") as f:
            f.write(file_buffer.getvalue())
        file_source = full_path
    return str(file_source)


async def data_profile(
    sandbox: AliasSandbox,
    sandbox_path: str,
    source_type: SourceType,
    llm_call_manager: LLMCallManager,
) -> Dict[str, Any]:
    """
    Generates a detailed profile and summary for data source using LLMs.

    Args:
        sandbox (AliasSandbox): The sandbox environment instance.
        path (str): The location of the data source.
                    - For files: A file path or URL.
                    - For databases: A connection string (DSN).
        source_type (SourceType): The type of the data source.
        llm_call_manager: Manager for handling LLM calls

    Returns:
        Dict: An object containing the generated text profile of the data.

    Raises:
        ValueError: If the provided `source_type` is not supported.
    """

    if source_type in [SourceType.CSV, SourceType.EXCEL, SourceType.IMAGE]:
        local_path = _copy_file_from_sandbox_with_original_name(
            sandbox,
            sandbox_path,
        )
    elif source_type == SourceType.RELATIONAL_DB:
        local_path = sandbox_path
    else:
        raise ValueError(f"Unsupported source type {source_type}")

    profiler = DataProfilerFactory.get_profiler(
        llm_call_manager=llm_call_manager,
        path=local_path,
        source_type=source_type,
    )

    return await profiler.generate_profile()
