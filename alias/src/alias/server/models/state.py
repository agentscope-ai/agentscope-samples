# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"
import uuid
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from .field import formatted_datetime_field


class StateBase(SQLModel):
    conversation_id: uuid.UUID = Field(
        foreign_key="conversation.id",
        nullable=False,
        ondelete="CASCADE",
        unique=True,
        index=True,
    )
    content: Optional[str] = None
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()


class State(StateBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation: Optional["Conversation"] = Relationship(  # noqa F821
        back_populates="state",
    )
