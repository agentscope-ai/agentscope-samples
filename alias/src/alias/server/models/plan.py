# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column
from sqlmodel import JSON, Field, Relationship, SQLModel

from .field import formatted_datetime_field


class TaskState(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ABANDONED = "abandoned"


class SubTask(SQLModel):
    description: Optional[str] = Field(default=None)
    state: Optional[TaskState] = Field(default=None)


class Roadmap(SQLModel):
    subtasks: List[SubTask] = Field(default_factory=list)


class PlanBase(SQLModel):
    conversation_id: uuid.UUID = Field(
        foreign_key="conversation.id",
        nullable=False,
        ondelete="CASCADE",
    )
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()


class Plan(PlanBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    conversation: Optional["Conversation"] = Relationship(  # noqa F821
        back_populates="plans",
    )

    @property
    def roadmap(self) -> Roadmap:
        """
        Get roadmap from content. Content is the roadmap's JSON form directly.
        """
        if not self.content:
            return Roadmap()
        return Roadmap.model_validate(self.content)
