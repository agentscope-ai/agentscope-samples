# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"

import uuid
from typing import List, Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from .field import email_field, formatted_datetime_field, username_field


# Shared properties
class UserBase(SQLModel):
    """The base model used to represent a user."""

    email: EmailStr = email_field()
    username: str = username_field()
    avatar: Optional[str] = Field(default=None, nullable=True)
    is_active: bool = True
    is_superuser: bool = False
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()
    last_login_time: Optional[str] = Field(default=None, nullable=True)
    last_login_ip: Optional[str] = Field(default=None, nullable=True)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    password: Optional[str] = Field(default=None)
    oauth_provider: Optional[str] = Field(default=None, index=True)
    oauth_id: Optional[str] = Field(default=None, index=True)
    conversations: List["Conversation"] = Relationship(  # noqa: F821
        back_populates="owner",
    )
    parent_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id")
    parent: Optional["User"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "User.id"},
    )
    children: List["User"] = Relationship(back_populates="parent")

    @property
    def has_password(self) -> bool:
        """Check if the user has a password set."""
        return self.password is not None
