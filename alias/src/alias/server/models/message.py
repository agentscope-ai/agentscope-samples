# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"

import uuid
from enum import Enum
from typing import List, Optional

from sqlmodel import JSON, Field, Relationship, SQLModel

from .action import FeedbackType
from .field import formatted_datetime_field
from .plan import Roadmap


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    RESPONSE = "response"
    CHAT = "chat"
    THOUGHT = "thought"
    SUB_RESPONSE = "sub_response"
    SUB_THOUGHT = "sub_thought"
    TOOL_CALL = "tool_call"
    CLARIFICATION = "clarification"
    ROADMAP = "roadmap"
    FILES = "files"
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class ToolIconType(str, Enum):
    TOOL = "tool"
    BROWSER = "browser"
    FILE = "file"


class SelectionType(str, Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"


class MessageState(str, Enum):
    RUNNING = "running"
    WAITING = "waiting"
    FINISHED = "finished"
    ERROR = "error"


class BaseMessage(SQLModel):
    name: Optional[str] = Field(default=None)
    role: Optional[MessageRole] = Field(default=None)
    status: Optional[MessageState] = Field(default=MessageState.FINISHED)


class AssistantMessage(BaseMessage):
    role: MessageRole = Field(default=MessageRole.ASSISTANT)


class ResponseMessage(AssistantMessage):
    type: MessageType = MessageType.RESPONSE
    content: Optional[str] = Field(default=None)


class ChatMessage(AssistantMessage):
    type: MessageType = MessageType.CHAT
    content: Optional[str] = Field(default=None)


class ThoughtMessage(AssistantMessage):
    type: MessageType = MessageType.THOUGHT
    content: Optional[str] = Field(default=None)


class SubResponseMessage(AssistantMessage):
    type: MessageType = MessageType.SUB_RESPONSE
    content: Optional[str] = Field(default=None)


class SubThoughtMessage(AssistantMessage):
    type: MessageType = MessageType.SUB_THOUGHT
    content: Optional[str] = Field(default=None)


class ToolCallMessage(AssistantMessage):
    type: MessageType = MessageType.TOOL_CALL
    content: Optional[str] = Field(default=None)
    arguments: Optional[dict] = Field(default_factory=dict, sa_type=JSON)
    name: Optional[str] = Field(default=None)
    tool_name: Optional[str] = Field(default=None)
    icon: Optional[ToolIconType] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)


class ToolUseMessage(ToolCallMessage):
    type: MessageType = MessageType.TOOL_USE


class ToolResultMessage(ToolCallMessage):
    type: MessageType = MessageType.TOOL_RESULT


class ClarificationMessage(AssistantMessage):
    type: MessageType = MessageType.CLARIFICATION
    content: Optional[str] = Field(default=None)
    options: Optional[List[str]] = Field(default_factory=list)
    selection_type: Optional[SelectionType] = Field(
        default=SelectionType.SINGLE,
    )


class FileItem(SQLModel):
    id: Optional[str] = Field(default=None)
    filename: Optional[str] = Field(default=None)
    size: Optional[int] = Field(default=None)
    url: Optional[str] = Field(default=None)


class FilesMessage(AssistantMessage):
    type: MessageType = MessageType.FILES
    files: Optional[List[FileItem]] = Field(default_factory=list)


class RoadmapChange(SQLModel):
    previous: Optional[Roadmap] = None
    current: Optional[Roadmap] = None


class UserMessage(BaseMessage):
    role: MessageRole = Field(default=MessageRole.USER)
    status: MessageState = MessageState.FINISHED
    type: MessageType = MessageType.USER
    content: Optional[str] = Field(default=None)
    files: Optional[List[FileItem]] = Field(default_factory=list)
    roadmap: Optional[RoadmapChange] = None

    @property
    def filenames(self) -> List[str]:
        return (
            [file.url for file in self.files if file.url] if self.files else []
        )


class SystemMessage(BaseMessage):
    role: MessageRole = Field(default=MessageRole.SYSTEM)
    type: MessageType = MessageType.SYSTEM
    content: Optional[str] = Field(default=None)
    status: MessageState = MessageState.FINISHED


class DetailedMessageBase(SQLModel):
    message: Optional[dict] = Field(default=None, sa_type=JSON)
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()
    feedback: Optional[FeedbackType] = Field(default=None)
    collected: Optional[bool] = Field(
        default=False,
        description="Collect can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    task_id: Optional[uuid.UUID] = Field(default=None)
    conversation_id: uuid.UUID = Field(
        foreign_key="conversation.id",
        index=True,
        ondelete="CASCADE",
    )
    parent_message_id: Optional[uuid.UUID] = Field(
        foreign_key="message.id",
        index=True,
    )
    meta_data: Optional[dict] = Field(default_factory=dict, sa_type=JSON)


class Message(DetailedMessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation: Optional["Conversation"] = Relationship(  # noqa F821
        back_populates="messages",
    )
    parent: Optional["Message"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={"remote_side": "Message.id"},
    )
    replies: List["Message"] = Relationship(back_populates="parent")
