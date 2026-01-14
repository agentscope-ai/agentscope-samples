# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import re
import uuid
import asyncio
from copy import deepcopy

from alias.server.clients.inner_client import InnerClient

try:
    from .logging_utils import setup_logging
except ImportError:
    from alias.memory_service.profiling_utils.logging_utils import (  # type: ignore[no-redef]  # noqa: E501  # pylint: disable=line-too-long
        setup_logging,
    )
logger = setup_logging()


def build_filters_and_metadata(
    *,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    input_metadata: Optional[Dict[str, Any]] = None,
    input_filters: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Construct storage metadata and query filters for memory operations.

    The implementation adapts the filtering helper used in the
    `mem0` project to support session-scoped metadata while
    allowing optional actor-level filtering. See
    https://github.com/mem0ai/mem0/tree/main/mem0 for the original context.

    Args:
        user_id: Identifier that scopes memory operations to a user.
        agent_id: Identifier that scopes operations to an agent.
        run_id: Identifier that scopes operations to a specific run.
        actor_id: Identifier used to filter memories by actor during retrieval.
        input_metadata: Metadata template to augment with session identifiers.
        input_filters: Filters to augment with session and actor identifiers.

    Returns:
        A tuple containing:

        * base_metadata_template: Metadata used for storing new memories.
        * effective_query_filters: Filters applied when querying memories.

    Raises:
        ValueError: If none of `user_id`, `agent_id`, or `run_id` are provided.
    """

    base_metadata_template = deepcopy(input_metadata) if input_metadata else {}
    effective_query_filters = deepcopy(input_filters) if input_filters else {}

    session_ids_provided = []

    if user_id:
        base_metadata_template["user_id"] = user_id
        effective_query_filters["user_id"] = user_id
        session_ids_provided.append("user_id")

    if agent_id:
        base_metadata_template["agent_id"] = agent_id
        effective_query_filters["agent_id"] = agent_id
        session_ids_provided.append("agent_id")

    if run_id:
        base_metadata_template["run_id"] = run_id
        effective_query_filters["run_id"] = run_id
        session_ids_provided.append("run_id")

    if not session_ids_provided:
        raise ValueError(
            "At least one of 'user_id', 'agent_id', or 'run_id' must be "
            "provided.",
        )

    resolved_actor_id = actor_id or effective_query_filters.get("actor_id")
    if resolved_actor_id:
        effective_query_filters["actor_id"] = resolved_actor_id

    return base_metadata_template, effective_query_filters


def run_async_in_thread(async_func, *args):
    """
    Execute an async callable in a synchronous context by creating a
    fresh event loop.

    This helper mirrors the utility used by the mem0 project for bridging
    async operations in synchronous workflows. See
    https://github.com/mem0ai/mem0/tree/main/mem0 for the original
    context.
    """

    return asyncio.run(async_func(*args))


def _normalize_is_confirmed(value: Any) -> int:
    """Convert various truthy/falsy inputs into strict integer flags."""

    # Handle None explicitly
    if value is None:
        return 0

    # Handle boolean and numeric types
    if isinstance(value, (bool, int, float)):
        return 1 if value else 0

    # Handle string types
    if isinstance(value, str):
        normalized = value.strip().lower()
        truthy_strings = {
            "1",
            "true",
            "yes",
            "y",
            "confirmed",
            "confirm",
            "done",
            "ok",
        }
        falsy_strings = {"0", "false", "no", "n", "pending", "unconfirmed"}

        if normalized in truthy_strings:
            return 1
        # Check falsy strings or try parsing as float
        if normalized in falsy_strings:
            result = 0
        else:
            # Try to parse as float
            try:
                result = 1 if float(normalized) else 0
            except ValueError:
                result = 0
        return result

    # Default: convert to bool then to int
    return 1 if bool(value) else 0


async def get_messages_by_session_id(session_id):
    try:
        # Create InnerClient instance
        client = InnerClient()

        # Convert session_id to UUID
        conversation_id = uuid.UUID(session_id)

        # Get messages using InnerClient
        messages = await client.get_messages(conversation_id)
        logger.info(
            f"Get Session Messages using InnerClient: {messages}",
        )
        messages = [item.model_dump() for item in messages]
        return messages
    except Exception as e:
        logger.error(
            f"Error getting messages for session {session_id}: " f"{str(e)}",
        )
        return []


def process_extracted_workflows_from_session_content_under_collection_action(
    extracted_results: list,
) -> list:
    """
    Transform extracted workflow data into structured message formats
    for storage
    Args:
        extracted_results (list): Raw workflow data containing tasks and
            action trajectories
    Returns:
        list: Structured messages ready for storage/display, formatted as
            user role messages
    """
    messages = []

    # Process each extracted workflow result
    for extracted_result in extracted_results:
        # Extract components from raw data with fallback defaults
        try:
            workflows = extracted_result.get("workflows", [])
            if not workflows:
                continue
        except Exception:
            continue
        task_type = extracted_result.get(
            "task_type",
            "Unknown Task Type",
        ).upper()

        content_lines = []
        # Build header section
        content_lines.append(
            f"I am satisfied with the following **{task_type}** task "
            f"solving process, and I collect it:",
        )
        content_lines.append(
            "Task Solving Process (decomposed into several sub-tasks in "
            "the solving order, and each sub-task contains several action "
            "steps):",
        )

        # Process each workflow as a sub-task
        for idx, workflow in enumerate(workflows, 1):
            if not isinstance(workflow, dict):
                logger.warning(f"Invalid workflow data: {workflow}")
                continue
            # Add sub-task header with description if available
            task_desc = workflow.get("task_description", "")
            content_lines.append(
                f"\n[Sub-task {idx}]: {task_desc}"
                if task_desc
                else f"\n[Sub-task {idx}]",
            )

            # Process individual action trajectories
            trajectories = workflow.get("trajectories", [])
            for t_idx, traj in enumerate(trajectories, 1):
                content_lines.append(f"  Action Step {t_idx}:")

                # Add reasoning/idea if present
                if reason := traj.get("reason", ""):
                    content_lines.append(f"    - Rationale/Idea: {reason}")

                # Add concrete action if present
                if action := traj.get("action", ""):
                    content_lines.append(f"    - Concrete Action: {action}")

        # Combine lines into final message content
        content = "\n".join(content_lines)

        # Package as user message
        messages.append(
            {
                "role": "user",  # Maintains chat message structure format
                "content": content,  # Formatted workflow documentation
            },
        )

    return messages


def format_session_content(
    session_content: list,
    max_messages: int | None = 200000,
    truncate_strategy: str = "only_meta_planner_messages",
) -> list:
    """
    Convert raw session content messages into standardized format for
    processing. If max_messages is not None, truncate the session content
    by the truncate_strategy.

    Attention: this function is only used for COLLECT_SESSION action !!!!
    Args:
        session_content (list): Raw list of message objects from chat
            session
        truncate_strategy (str): The strategy to truncate the session
            content, default is "only_meta_planner_messages", which means
            truncate the session content by the meta-planner messages
        max_messages (int | None): The maximum number of messages to
            return, if None, means no limit, default is 200000
    Returns:
        list: Reformatted messages with standardized structure containing:
            - role: Preferred sender identifier (name > role)
            - content: Message text
            - create_time: Creation time
            - id: Message ID
            - status: Message status
            - type: Message type
            - arguments: Message arguments (only for tool calls)
            - tool_name: Tool name
    """
    formatted_messages = []
    if session_content is None:
        return formatted_messages
    for message_obj in session_content:
        message = message_obj["message"]
        # Build formatted message entry with fallback values
        formatted_messages.append(
            {
                "role": (
                    message["name"] if message["name"] else message["role"]
                ),
                "content": message["content"],
                "create_time": message_obj["create_time"],
                "id": message_obj["id"],
                "status": message["status"],
                "type": message["type"] if "type" in message else None,
                "arguments": (
                    message["arguments"] if "arguments" in message else None
                ),
                "tool_name": (
                    message["tool_name"] if "tool_name" in message else None
                ),
            },
        )
    if max_messages is not None:
        total_length = sum(
            len(message["content"]) for message in formatted_messages
        )
        if total_length > max_messages:
            logger.info(
                f"Total length of session content: {total_length}, "
                f"max_messages: {max_messages}",
            )
            if truncate_strategy == "only_meta_planner_messages":
                # Filter out messages that are not from task-meta-planner role
                original_count = len(formatted_messages)
                formatted_messages = [
                    message
                    for message in formatted_messages
                    if message.get("role") == "task-meta-planner"
                ]
                removed_count = original_count - len(formatted_messages)
                logger.info(
                    f"Removed {removed_count} messages that are not from "
                    f"task-meta-planner role",
                )
                logger.info(
                    f"Truncated session content to "
                    f"{len(formatted_messages)} messages by "
                    f"only_meta_planner_messages strategy",
                )
            else:
                raise ValueError(
                    f"Invalid truncate strategy: {truncate_strategy}",
                )
    return formatted_messages


def _extract_bracket_content(
    text: str,
    start_pos: int,
    open_char: str,
    close_char: str,
) -> Optional[Tuple[int, int]]:
    """
    Extract content between matching brackets/braces from a given position.
    Returns (start, end) indices if a valid match is found, None otherwise.
    """
    if text[start_pos] != open_char:
        return None

    count = 1
    start = start_pos
    pos = start_pos + 1
    in_string = False
    escape_next = False

    while pos < len(text) and count > 0:
        char = text[pos]
        if escape_next:
            escape_next = False
        elif char == "\\" and in_string:
            escape_next = True
        elif char == '"' and not escape_next:
            in_string = not in_string
        elif not in_string:
            if char == open_char:
                count += 1
            elif char == close_char:
                count -= 1
        pos += 1

    if count == 0:
        return (start, pos)
    return None


def _extract_json_candidates(text: str) -> List[str]:
    """Extract potential JSON candidates (objects and arrays) from text."""
    candidates = []
    i = 0
    while i < len(text):
        # Try to extract object
        result = _extract_bracket_content(text, i, "{", "}")
        if result:
            start, end = result
            candidates.append(text[start:end])
            i = end
        else:
            # Try to extract array
            result = _extract_bracket_content(text, i, "[", "]")
            if result:
                start, end = result
                candidates.append(text[start:end])
                i = end
            else:
                i += 1
    return candidates


def _clean_json_string(json_str: str) -> str:
    """Clean and normalize a JSON string for parsing."""
    json_str = json_str.strip()
    json_str = re.sub(r"^```(?:json|JSON)?\s*", "", json_str)
    json_str = re.sub(r"\s*```$", "", json_str)

    # Handle nested braces
    if json_str.startswith("{") and json_str.endswith("}"):
        temp = json_str
        while temp.startswith("{{") and temp.endswith("}}") and len(temp) > 2:
            inner = temp[1:-1].strip()
            if inner.startswith("{") and inner.endswith("}"):
                test_inner = _normalize_python_to_json(inner)
                try:
                    json.loads(test_inner)
                    temp = inner
                except json.JSONDecodeError:
                    break
            else:
                break
        json_str = temp

    return _normalize_python_to_json(json_str)


def _normalize_python_to_json(json_str: str) -> str:
    """Convert Python-style syntax to valid JSON."""
    json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)  # Key names
    json_str = re.sub(
        r":\s*'([^']*)'",
        r': "\1"',
        json_str,
    )  # String values
    json_str = re.sub(
        r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:",
        r'\1"\2":',
        json_str,
    )
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    json_str = re.sub(r"\bTrue\b", "true", json_str)
    json_str = re.sub(r"\bFalse\b", "false", json_str)
    json_str = re.sub(r"\bNone\b", "null", json_str)
    return json_str


def _try_parse_json(
    json_str: str,
) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """Try to parse a JSON string, with fallback to cleaned version."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            cleaned_str = _clean_json_string(json_str)
            return json.loads(cleaned_str)
        except json.JSONDecodeError:
            return None


def extract_json_from_text(
    text: str,
    return_all: bool = False,
) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
    """
    Extract JSON object from text.
    Args:
        text (str): Text to extract JSON from.
        return_all (bool): IF True, return a list of all JSON objects
            found in the text. Otherwise, return the first one found.
    Returns:
        Dict/List/None: JSON object(s) found in the text.
    """
    json_candidates = _extract_json_candidates(text)
    valid_jsons: List[Dict[str, Any]] = []
    for candidate in json_candidates:
        parsed = _try_parse_json(candidate)
        if parsed is not None and isinstance(parsed, dict):
            valid_jsons.append(parsed)
    if return_all:
        return valid_jsons
    return valid_jsons[0] if valid_jsons else None
