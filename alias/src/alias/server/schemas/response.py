# -*- coding: utf-8 -*-
"""The API response base model."""

from typing import Generic, List, TypeVar
from sqlmodel import Field, SQLModel


T = TypeVar("T")


class PagePayload(SQLModel, Generic[T]):
    """Pagination response."""

    items: List[T]
    total: int


class ResponseBase(SQLModel):
    status: bool = Field(nullable=True)
    message: str = Field(nullable=True)
    payload: dict | None = Field(default=None, nullable=True)
