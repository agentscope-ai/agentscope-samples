# -*- coding: utf-8 -*-
import base64
import io
import json
import os
import tarfile
from pathlib import Path
from typing import Optional

from loguru import logger

from agentscope_runtime.common.container_clients.docker_client import (  # noqa: E501  # pylint: disable=C0301
    DockerClient,
)
from alias.runtime.alias_sandbox import AliasSandbox


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".log",
    ".py",
    ".js",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".csv",
    ".tsv",
    ".sql",
    ".sh",
    ".bat",
    ".ps1",
    ".r",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".scala",
    ".dart",
    ".vue",
    ".jsx",
    ".tsx",
    ".sass",
    ".scss",
    ".less",
    ".styl",
    ".tex",
    ".rst",
    ".adoc",
    ".org",
    ".wiki",
    ".rtf",
}


def _valid_workspace_path(workspace_path: str) -> bool:
    try:
        # Resolve both paths to absolute paths
        path = Path(workspace_path).resolve()
        base = Path("/workspace").resolve()

        # Check if the resolved path is under the base directory
        return path.is_relative_to(base)
    except (OSError, ValueError):
        # Handle invalid paths
        return False


def list_workspace_directories(
    sandbox: AliasSandbox,
    directory: str = "/workspace",
    recursive: bool = False,
) -> dict:
    """
    List files in the specified directory within the /workspace.
    Args:
        sandbox (AliasSandbox): sandbox to extract
        directory (str): The directory to list files in.
        recursive (bool): Whether to list recursively.

    Return:
        dict:
            with lists of `files` and `dirs`, both in format of full paths
    """
    if not _valid_workspace_path(directory):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`directory` must be under `/workspace`",
                },
            ],
        }

    result = {"files": [], "directories": []}

    def process_item(item, current_base):
        print(current_base, item["name"])
        current_path = (
            os.path.join(current_base, item["name"])
            if current_base
            else item["name"]
        )

        if item["type"] == "file":
            result["files"].append(current_path)
        elif item["type"] == "directory":
            result["directories"].append(current_path)
            if "children" in item:
                for child in item["children"]:
                    process_item(child, current_path)

    if recursive:
        tool_result = sandbox.call_tool(
            "directory_tree",
            arguments={"path": directory},
        )
        directory_tree = json.loads(tool_result["content"][0]["text"])
        for item in directory_tree:
            process_item(item, directory)
    else:
        tool_result = sandbox.call_tool(
            "list_directory",
            arguments={"path": directory},
        )
        list_content = tool_result["content"][0]["text"]
        print(list_content)
        sub_dir_items = [
            item.strip() for item in list_content.split("\n") if item.strip()
        ]
        for item in sub_dir_items:
            if "[DIR]" in item:
                dir_name = item.replace("[DIR] ", "")
                result["directories"].append(os.path.join(directory, dir_name))
            elif "[FILE]" in item:
                file_name = item.replace("[FILE] ", "")
                result["files"].append(os.path.join(directory, file_name))
    return result


def get_workspace_file(
    sandbox: AliasSandbox,
    file_path: str,
) -> bytes:
    """
    Get the content of the specified file within the /workspace.

    Args:
        sandbox (AliasSandbox): sandbox to extract
        file_path (str): The file path to get the content of.

    Returns:
        content encoded in base64
    """
    if not _valid_workspace_path(file_path):
        return base64.b64encode(
            "`file_path` must be under `/workspace`".encode(),
        )
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={"command": f"base64 -i {file_path}"},
    )
    return tool_result["content"][0]["text"]


def create_or_edit_workspace_file(
    sandbox: AliasSandbox,
    file_path: str,
    content: str,
) -> dict:
    if not _valid_workspace_path(file_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`file_path` must be under `/workspace`",
                },
            ],
        }
    sandbox.call_tool(
        "run_shell_command",
        arguments={"command": f"touch {file_path}"},
    )
    fill_result = sandbox.call_tool(
        "write_file",
        arguments={"path": file_path, "content": content},
    )
    return fill_result


def create_workspace_directory(
    sandbox: AliasSandbox,
    directory_path: str,
) -> dict:
    """
    Create a directory within the /workspace directory.
    """
    if not _valid_workspace_path(directory_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`directory_path` must be under `/workspace`",
                },
            ],
        }
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={"command": f"mkdir -p {directory_path}"},
    )
    return tool_result


def delete_workspace_file(
    sandbox: AliasSandbox,
    file_path: str,
) -> dict:
    """
    Delete a file within the /workspace directory.
    """
    if not _valid_workspace_path(file_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`file_path` must be under `/workspace`",
                },
            ],
        }
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={"command": f"rm -rf {file_path}"},
    )
    return tool_result


def download_workspace_file_from_oss(
    sandbox: AliasSandbox,
    oss_url: str,
    to_path: str,
) -> dict:
    """
    Download a file from oss url to the /workspace directory.
    """
    if not _valid_workspace_path(to_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`file_path` must be under `/workspace`",
                },
            ],
        }
    logger.info(f"Prepared {to_path} from {oss_url}")
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={
            "command": "apt install wget",
        },
    )
    print(f"{tool_result}")
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={
            "command": f"wget -O {to_path} {oss_url}",
        },
    )
    print(f"{tool_result}")
    return tool_result


def delete_workspace_directory(
    sandbox: AliasSandbox,
    directory_path: str,
) -> dict:
    """
    Delete a directory within the /workspace directory.
    """
    if not _valid_workspace_path(directory_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`directory` must be under `/workspace`",
                },
            ],
        }
    tool_result = sandbox.call_tool(
        "run_shell_command",
        arguments={"command": f"rm -rf {directory_path}"},
    )
    return tool_result


def clean_workspace(sandbox: AliasSandbox):
    """
    Remove all files and subdirectories within the /workspace directory.
    """
    ls_result = list_workspace_directories(sandbox)
    for file in ls_result["files"]:
        delete_workspace_file(sandbox, file)

    for subdir in ls_result["directories"]:
        delete_workspace_directory(sandbox, subdir)


def download_complete_workspace(
    sandbox: AliasSandbox,
    save_dir: Optional[str] = None,
):
    """
    Download all files and subdirectories within the /workspace directory.
    """
    download_files = {}
    list_dir = list_workspace_directories(sandbox, recursive=True)
    for file_path in list_dir["files"]:
        file_content = get_workspace_file(sandbox, file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        if file_extension in TEXT_EXTENSIONS:
            text = base64.b64decode(file_content).decode("utf-8")
            download_files[file_path] = text
            if save_dir is not None:
                with open(
                    os.path.join(save_dir, file_name),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(text)
        else:
            content = base64.b64decode(file_content)
            download_files[file_path] = file_content  # this is base64
            if save_dir is not None:
                with open(os.path.join(save_dir, file_name), "wb") as f:
                    f.write(content)
        logger.info(f"Downloaded {file_path}")
    return download_files


def copy_local_file_to_workspace(
    sandbox: AliasSandbox,
    local_path: str,
    target_path: Optional[str] = None,
):
    """
    Copy a local file to a subdirectory under /workspace directory.
    If target_path is not provided, the file will be copied to /workspace
    with the same filename as the local file.
    """
    if target_path is None:
        filename = os.path.basename(local_path)
        target_path = os.path.join("/workspace", filename)

    if not _valid_workspace_path(target_path):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "`directory` must be under `/workspace`",
                },
            ],
        }

    client = sandbox.manager_api.client
    if not isinstance(client, DockerClient):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "Copying file is not support sandbox "
                    f"with client type {type(client)}",
                },
            ],
        }
    docker_client = client.client
    container = docker_client.containers.get(sandbox.sandbox_id)

    # Create a tar archive in memory
    tar_stream = io.BytesIO()
    # pylint: disable=R1732
    tar = tarfile.open(fileobj=tar_stream, mode="w")

    # Add file to tar archive
    tar.add(local_path, arcname=os.path.basename(target_path))
    tar.close()

    # Reset stream position
    tar_stream.seek(0)

    # Extract tar to container (directory path only)
    container.put_archive(os.path.dirname(target_path), tar_stream)

    return {
        "isError": False,
        "content": [
            {
                "type": "text",
                "text": f"{target_path}",
            },
        ],
    }
