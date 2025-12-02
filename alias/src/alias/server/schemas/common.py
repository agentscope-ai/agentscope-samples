# -*- coding: utf-8 -*-
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderDirection(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    order_by: Optional[str] = Field(default=None, description="Order by")
    order_direction: OrderDirection = Field(
        default=OrderDirection.DESC,
        description="Order direction",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._skip = None

    @property
    def skip(self) -> int:
        return self._skip if self._skip else (self.page - 1) * self.page_size

    @skip.setter
    def skip(self, value: int):
        self._skip = value

    @property
    def limit(self) -> int:
        return self.page_size

    @classmethod
    def create(
        cls,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
    ):
        if all(
            param is None
            for param in [page, page_size, order_by, order_direction]
        ):
            return None

        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if order_by is not None:
            params["order_by"] = order_by
        if order_direction is not None:
            params["order_direction"] = order_direction

        return cls(**params)
