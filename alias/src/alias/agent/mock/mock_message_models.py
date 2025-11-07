# -*- coding: utf-8 -*-
"""Mock message models for local testing without api_server dependency."""
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class MessageState(str, Enum):
    """Message state enumeration."""

    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class MessageType(str, Enum):
    """Message type enumeration."""

    RESPONSE = "response"
    SUB_RESPONSE = "sub_response"
    THOUGHT = "thought"
    SUB_THOUGHT = "sub_thought"
    TOOL_CALL = "tool_call"
    CLARIFICATION = "clarification"
    FILES = "files"
    SYSTEM = "system"


class BaseMessage(BaseModel):
    """Base message class for local testing."""

    role: str = "assistant"
    content: Any = ""
    name: Optional[str] = None
    type: Optional[str] = "text"
    status: MessageState = MessageState.FINISHED


class UserMessage(BaseMessage):
    """User message for local testing."""

    role: str = "user"
    name: str = "User"


class MockMessage:
    id: uuid.UUID = uuid.uuid4()
    message: Optional[dict] = None
    files: list[Any] = []
