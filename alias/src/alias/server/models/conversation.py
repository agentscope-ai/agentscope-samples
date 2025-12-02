# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"
import uuid
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from alias.server.schemas.chat import ChatMode

from .field import formatted_datetime_field
from .message import Message
from .plan import Plan
from .state import State
from .user import User


class ConversationBase(SQLModel):
    name: str
    description: Optional[str] = Field(default=None)
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()
    collected: Optional[bool] = Field(
        default=False,
        description="Collect can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    pinned: Optional[bool] = Field(
        default=False,
        description="Pinned can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    shared: Optional[bool] = Field(
        default=False,
        description="Shared can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    running: Optional[bool] = Field(
        default=False,
        description="Running can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    deleted: Optional[bool] = Field(
        default=False,
        description="Deleted can be True or False",
        sa_column_kwargs={"server_default": "0"},
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
    )
    chat_mode: Optional[ChatMode] = ChatMode.GENERAL
    sandbox_id: str
    sandbox_url: str


class Conversation(ConversationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner: Optional[User] = Relationship(back_populates="conversations")
    messages: List[Message] = Relationship(back_populates="conversation")
    plans: List[Plan] = Relationship(back_populates="conversation")
    state: Optional[State] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "delete"},
    )
