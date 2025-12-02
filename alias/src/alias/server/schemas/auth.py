# -*- coding: utf-8 -*-
# pylint: disable=W0107
from sqlmodel import SQLModel

from ..models.field import email_field, password_field
from .response import ResponseBase
from .user import AddUserRequest, AddUserResponse


class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CodeToken(SQLModel):
    token: str


class RefreshTokenRequest(SQLModel):
    refresh_token: str


class LoginRequest(SQLModel):
    email: str = email_field()
    password: str = password_field()


class LoginResponse(ResponseBase):
    payload: Token


class LogoutResponse(ResponseBase):
    pass


class ResetPasswordResponse(ResponseBase):
    pass


class RegisterUserRequest(AddUserRequest):
    """The request model used to register a new user."""

    pass


class RegisterResponse(AddUserResponse):
    """The response model used to register a new user."""

    pass
