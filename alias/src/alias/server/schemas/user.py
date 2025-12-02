# -*- coding: utf-8 -*-
import uuid
from typing import List, Optional

from pydantic import EmailStr
from sqlmodel import SQLModel

from ..models.field import email_field, password_field, username_field
from ..models.user import UserBase
from .response import ResponseBase


class AddUserRequest(SQLModel):
    email: EmailStr = email_field()
    password: str = password_field()
    username: str = username_field()


class UserUpdateRequest(SQLModel):
    username: Optional[str] = username_field()
    password: Optional[str] = password_field()
    new_password: Optional[str] = password_field()
    avatar: Optional[str] = None


class UserInfo(UserBase):
    id: uuid.UUID
    has_password: bool = False


class AddUserResponse(ResponseBase):
    payload: UserInfo


class GetUserResponse(ResponseBase):
    payload: UserInfo


class UpdateUserResponse(ResponseBase):
    payload: UserInfo


class DeleteUserResponse(ResponseBase):
    payload: uuid.UUID


class PageUserInfo(SQLModel):
    total: int
    items: List[UserInfo]


class ListUsersResponse(ResponseBase):
    payload: PageUserInfo
