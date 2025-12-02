# -*- coding: utf-8 -*-
# mypy: disable-error-code="call-arg, name-defined"
import uuid
from typing import Optional

from sqlmodel import Field, SQLModel

from .field import formatted_datetime_field


class FileBase(SQLModel):
    filename: str
    mime_type: str
    extension: str
    size: int
    storage_path: str = Field(nullable=False)
    storage_type: str = Field(default="local", nullable=False)
    create_time: str = formatted_datetime_field()
    update_time: str = formatted_datetime_field()
    shared: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": "0"},
    )
    user_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description=(
            "Conversation ID (required for sandbox files to "
            "determine which sandbox to use)"
        ),
    )


class File(FileBase, table=True):  # type: ignore[call-arg]
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
