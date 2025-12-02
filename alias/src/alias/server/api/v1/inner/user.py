# -*- coding: utf-8 -*-
"""The user related API endpoints"""
import uuid
from typing import Optional

from fastapi import APIRouter

from alias.server.api.deps import (
    SessionDep,
    InnerAPIAuth,
)
from alias.server.schemas.common import PaginationParams
from alias.server.schemas.response import PagePayload, ResponseBase
from alias.server.models.user import User
from alias.server.services.user_service import UserService

router = APIRouter(
    prefix="/users",
    tags=["inner/users"],
    dependencies=[InnerAPIAuth],
)


class ListUsersResponse(ResponseBase):
    payload: PagePayload[User]


class GetUserResponse(ResponseBase):
    payload: User


@router.get("", response_model=ListUsersResponse)
async def list_users(
    session: SessionDep,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    order_by: Optional[str] = None,
    order_direction: Optional[str] = None,
) -> ListUsersResponse:
    """List users."""
    pagination = PaginationParams.create(
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction,
    )

    user_service = UserService(session=session)

    total = await user_service.count_by_fields({})
    users = await user_service.paginate(
        pagination=pagination,
    )
    return ListUsersResponse(
        status=True,
        message="List users successfully.",
        payload=PagePayload(
            total=total,
            items=users,
        ),
    )


@router.get("/{user_id}", response_model=GetUserResponse)
async def get_user(
    session: SessionDep,
    user_id: uuid.UUID,
) -> GetUserResponse:
    """Get specified user."""
    user_service = UserService(session=session)

    user = await user_service.get_user(
        user_id=user_id,
    )

    return GetUserResponse(
        status=True,
        message="Get user successfully.",
        payload=user,
    )
