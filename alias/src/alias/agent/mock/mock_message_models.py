# -*- coding: utf-8 -*-
"""Mock message models for cli without server."""
import uuid
from enum import Enum
from typing import Any, Optional, Literal
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class MockFileBase:
    filename: str
    mime_type: str
    extension: str
    storage_path: str
    size: int = -1
    storage_type: str = "unknown"
    create_time: str = "xxxyyy"
    update_time: str = "xxxyyy"
    user_id: uuid.UUID = uuid.uuid4()


class MockFile(MockFileBase):  # type: ignore[call-arg]
    id: uuid.UUID = uuid.uuid4()


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
    """Base message class for cli."""

    role: str = "assistant"
    content: Any = ""
    name: Optional[str] = None
    type: Optional[str] = "text"
    status: MessageState = MessageState.FINISHED


class UserMessage(BaseMessage):
    """User message for cli."""

    role: str = "user"
    name: str = "User"


class MockMessage:
    id: uuid.UUID = uuid.uuid4()
    message: Optional[dict] = None
    files: list[Any] = []
    create_time: str = "xxxyyy"
    update_time: str = "xxxyyy"


class SubTaskToPrint(BaseModel):
    description: str = Field(..., description="description of subtask")
    state: Literal["todo", "in_progress", "done", "abandoned"]


class PlanToPrint(BaseModel):
    subtasks: list[SubTaskToPrint] = Field(default_factory=list)
