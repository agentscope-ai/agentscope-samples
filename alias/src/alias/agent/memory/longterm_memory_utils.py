# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Any

from alias.server.services.session_service import SessionService
from alias.server.models.message import Message

# Import related models to ensure they are registered in SQLAlchemy's
# class registry
# This is necessary for SQLAlchemy to resolve string references in
# relationships
# pylint: disable=unused-import
from alias.server.models.conversation import Conversation  # noqa: F401,E501
from alias.server.models.plan import Plan  # noqa: F401,E501
from alias.server.models.user import User  # noqa: F401,E501
from alias.server.models.state import State  # noqa: F401,E501


def filter_latest_user_message(messages: list[Any]) -> Any:
    """Filter the latest user message from the list of messages.

    Args:
        messages: List of message objects

    Returns:
        The latest user message
    """
    if messages is None:
        return None
    latest_user_msg = None
    action_message_id = None
    has_earlier_user_msg = False
    for cur_msg in reversed(messages):
        msg_body = cur_msg["message"]
        if msg_body["role"] == "user":
            if latest_user_msg is None:
                # Found the latest user message
                latest_user_msg = msg_body["content"]
                action_message_id = cur_msg["id"]
            else:
                # Found an earlier user message before the latest one
                has_earlier_user_msg = True
                break
    return latest_user_msg, action_message_id, has_earlier_user_msg


def _convert_message_data_to_dict(message_data: Any) -> dict[str, Any] | None:
    """Convert message_data to a dictionary.

    Args:
        message_data: Message data that can be dict, object with to_dict(),
            model_dump(), or other types

    Returns:
        Dictionary representation of message_data, or None if conversion fails
    """
    if message_data is None:
        return None

    if isinstance(message_data, dict):
        return message_data
    if hasattr(message_data, "to_dict"):
        return message_data.to_dict()
    if hasattr(message_data, "model_dump"):
        return message_data.model_dump()
    # Fallback: try to convert to dict
    if hasattr(message_data, "__dict__"):
        return dict(message_data)
    return message_data


def _convert_files_to_list(files: list[Any]) -> list[dict[str, Any]]:
    """Convert file objects to a list of dictionaries.

    Args:
        files: List of file objects

    Returns:
        List of dictionaries representing file objects
    """
    files_list = []
    if not files:
        return files_list

    for f in files:
        file_dict = {
            "id": str(f.id) if hasattr(f, "id") else None,
            "filename": getattr(f, "filename", None),
            "mime_type": getattr(f, "mime_type", None),
            "extension": getattr(f, "extension", None),
            "storage_path": getattr(f, "storage_path", None),
            "size": getattr(f, "size", None),
            "storage_type": getattr(f, "storage_type", None),
            "create_time": getattr(f, "create_time", None),
            "update_time": getattr(f, "update_time", None),
            "user_id": str(getattr(f, "user_id", None))
            if hasattr(f, "user_id")
            else None,
        }
        files_list.append(file_dict)
    return files_list


def _get_timestamp_with_fallback(
    obj: Any,
    attr_name: str,
) -> str:
    """Get timestamp from object attribute or use current time as fallback.

    Args:
        obj: Object to get timestamp from
        attr_name: Attribute name to check for timestamp

    Returns:
        ISO format timestamp string
    """
    timestamp = getattr(obj, attr_name, None)
    if timestamp is None or not isinstance(timestamp, str):
        return datetime.now(timezone.utc).isoformat()
    return timestamp


def convert_mock_messages_to_dict(
    messages: list[Any],
    session_service: SessionService,
) -> list[Any]:
    """Convert MockMessage objects to Message objects, then to dictionaries
    for serialization.

    This function converts MockMessage objects to Message model instances
    first, filling in all required fields, then serializes them to
    dictionaries.
    Other message types (Pydantic models, dicts, etc.) are returned as-is
    since they are already serializable.

    Args:
        messages: List of message objects
        session_service: SessionService instance to get conversation_id and
            task_id

    Returns:
        List of messages with MockMessage objects converted to Message dicts,
        other types unchanged
    """
    converted = []
    # Get required fields from session_service
    conversation_id = session_service.session_entity.conversation_id
    task_id = getattr(session_service.session_entity, "task_id", None)

    for msg in messages:
        # Check if it's a MockMessage by type name to avoid import issues
        msg_type_name = type(msg).__name__
        msg_type_module = type(msg).__module__
        is_mock_message = (
            msg_type_name == "MockMessage"
            and "mock_message_models" in msg_type_module
        )

        if is_mock_message:
            # Convert message_data to dictionary
            message_dict = _convert_message_data_to_dict(msg.message)
            if message_dict is None:
                message_dict = {}

            # Convert files to list of dicts if needed
            files_list = _convert_files_to_list(msg.files)
            if files_list:
                message_dict["files"] = files_list

            # Get create_time and update_time from MockMessage instance, or
            # use current time as fallback
            create_time = _get_timestamp_with_fallback(msg, "create_time")
            update_time = _get_timestamp_with_fallback(msg, "update_time")

            # Create Message object with all required fields
            message_obj = Message(
                id=msg.id,
                message=message_dict,
                create_time=create_time,
                update_time=update_time,
                feedback=None,
                collected=False,
                task_id=task_id,
                conversation_id=conversation_id,
                parent_message_id=None,
                meta_data={},
            )

            # Convert Message object to dict using model_dump()
            msg_dict = message_obj.model_dump(
                exclude={"conversation", "parent", "replies"},
            )
            converted.append(msg_dict)
        else:
            # Other message types (Pydantic models, dicts, etc.) are already
            # serializable
            converted.append(msg)
    return converted
