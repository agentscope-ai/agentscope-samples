# -*- coding: utf-8 -*-
import json

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse


def todo_write(agent, todos) -> ToolResponse:
    """
    Create and manage a structured task list for the current coding session.

    Args:
        todos (`list[dict]`):
            Task list. Each task must contain:
            - id (`str`): Non-empty unique identifier.
            - content (`str`): Non-empty description.
            - status (`{'pending', 'in_progress', 'completed'}`):
              Current task state.

    Returns:
        `dict`:
            Dictionary in the form ``{'todos': [...]}`` whose content is the
            validated input list.
    """

    # Validate input parameters
    if not isinstance(todos, list):
        raise TypeError("todos must be a list")

    # Validate the structure of each task
    for todo in todos:
        if not isinstance(todo, dict):
            raise TypeError("Each task must be a dictionary type")

        # Check required fields
        required_fields = ["id", "content", "status"]
        for field in required_fields:
            if field not in todo:
                raise ValueError(f"Task is missing required field: {field}")

        # Validate field types
        if not isinstance(todo["id"], str) or not todo["id"].strip():
            raise ValueError("Task id must be a non-empty string")

        if not isinstance(todo["content"], str) or len(todo["content"]) < 1:
            raise ValueError("Task content must be a non-empty string")

        # Check status value
        valid_statuses = ["pending", "in_progress", "completed"]
        if todo["status"] not in valid_statuses:
            raise ValueError(f"Task status must be one of {valid_statuses}")

        # Validate priority value
        if "priority" in todo:
            valid_priorities = ["high", "medium", "low"]
            if todo["priority"] not in valid_priorities:
                raise ValueError(
                    f"Task 'priority' must be one of {valid_priorities}",
                )
        else:
            pass

    # Ensure only one task is in 'in_progress' status
    in_progress_count = sum(
        1 for todo in todos if todo["status"] == "in_progress"
    )
    if in_progress_count > 1:
        raise ValueError("Only one task can be in 'in_progress' status")

    agent.todo_list = todos

    # Return the formatted task list
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=json.dumps(todos),
            ),
        ],
    )
