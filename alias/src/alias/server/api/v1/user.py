# -*- coding: utf-8 -*-
"""The user related API endpoints"""
import uuid
from typing import Optional

from fastapi import APIRouter

from alias.server.api.deps import (
    CurrentSuperUser,
    CurrentUser,
    SessionDep,
)
from alias.server.schemas.common import PaginationParams
from alias.server.schemas.user import (
    AddUserRequest,
    AddUserResponse,
    DeleteUserResponse,
    GetUserResponse,
    ListUsersResponse,
    PageUserInfo,
    UpdateUserResponse,
    UserInfo,
    UserUpdateRequest,
)
from alias.server.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=AddUserResponse)
async def add_user(
    current_user: CurrentSuperUser,
    session: SessionDep,
    form: AddUserRequest,
) -> AddUserResponse:
    """Add a new user."""
    user_service = UserService(session=session)
    user = await user_service.create_user(
        email=form.email,
        password=form.password,
        username=form.username,
        parent_id=current_user.id,
    )
    return AddUserResponse(
        status=True,
        message="Add user successfully.",
        payload=UserInfo.model_validate(user),
    )


@router.get("", response_model=ListUsersResponse)
async def list_users(
    current_user: CurrentSuperUser,
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
    total, users = await user_service.list_users(
        parent_id=current_user.id,
        pagination=pagination,
    )
    return ListUsersResponse(
        status=True,
        message="List users successfully.",
        payload=PageUserInfo(
            total=total,
            items=[UserInfo.model_validate(user) for user in users],
        ),
    )


@router.get("/me", response_model=GetUserResponse)
async def get_me(current_user: CurrentUser) -> GetUserResponse:
    """Get current user."""
    user_info = UserInfo.model_validate(current_user)
    return GetUserResponse(
        status=True,
        message="Get user successfully.",
        payload=user_info,
    )


@router.post("/me/name", response_model=UpdateUserResponse)
async def update_name(
    current_user: CurrentUser,
    session: SessionDep,
    request: UserUpdateRequest,
) -> UpdateUserResponse:
    """Update own user name."""
    user_service = UserService(session=session)
    user = await user_service.update_user(
        user_id=current_user.id,
        username=request.username,
    )
    return UpdateUserResponse(
        status=True,
        message="Update user name successfully.",
        payload=UserInfo.model_validate(user),
    )


@router.post("/me/password", response_model=UpdateUserResponse)
async def update_password(
    current_user: CurrentUser,
    session: SessionDep,
    request: UserUpdateRequest,
) -> UpdateUserResponse:
    """Update own user password."""
    user_service = UserService(session=session)
    user = await user_service.update_user(
        user_id=current_user.id,
        password=request.password,
        new_password=request.new_password,
    )
    return UpdateUserResponse(
        status=True,
        message="Update user password successfully.",
        payload=UserInfo.model_validate(user),
    )


@router.post("/me/avatar", response_model=UpdateUserResponse)
async def update_avatar(
    current_user: CurrentUser,
    session: SessionDep,
    request: UserUpdateRequest,
) -> UpdateUserResponse:
    """Update user avatar."""
    user_service = UserService(session=session)
    user = await user_service.update_user(
        user_id=current_user.id,
        avatar=request.avatar,
    )
    return UpdateUserResponse(
        status=True,
        message="Update avatar successfully.",
        payload=UserInfo.model_validate(user),
    )


@router.delete("/me", response_model=DeleteUserResponse)
async def delete_me(
    current_user: CurrentUser,
    session: SessionDep,
) -> DeleteUserResponse:
    """Delete own user."""
    user_service = UserService(session=session)
    await user_service.delete_user(user_id=current_user.id)
    return DeleteUserResponse(
        status=True,
        message="Delete me successfully.",
        payload=current_user.id,
    )


@router.get("/{user_id}", response_model=GetUserResponse)
async def get_user(
    current_user: CurrentSuperUser,
    session: SessionDep,
    user_id: uuid.UUID,
) -> GetUserResponse:
    """Get specified user."""
    user_service = UserService(session=session)
    user_info = await user_service.get_user(
        parent_id=current_user.id,
        user_id=user_id,
    )
    return GetUserResponse(
        status=True,
        message="Get user successfully.",
        payload=user_info,
    )


@router.delete("/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    current_user: CurrentSuperUser,
    session: SessionDep,
    user_id: uuid.UUID,
) -> DeleteUserResponse:
    """Delete specified user."""
    user_service = UserService(session=session)
    await user_service.delete_user(parent_id=current_user.id, user_id=user_id)
    return DeleteUserResponse(
        status=True,
        message="Delete user successfully.",
        payload=user_id,
    )
