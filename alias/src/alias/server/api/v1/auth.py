# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

from fastapi import APIRouter

from alias.server.api.deps import CurrentUser, SessionDep
from alias.server.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterResponse,
    RegisterUserRequest,
)
from alias.server.schemas.user import UserInfo
from alias.server.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    session: SessionDep,
    request: LoginRequest,
) -> LoginResponse:
    """Login a user."""
    auth_service = AuthService(session=session)
    user = await auth_service.authenticate(
        email=request.email,
        password=request.password,
    )
    token = await auth_service.get_jwt_token(user_id=user.id)
    return LoginResponse(
        status=True,
        message="Login successfully",
        payload=token,
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    session: SessionDep,
    form: RegisterUserRequest,
) -> RegisterResponse:
    """Register a new user."""
    auth_service = AuthService(session=session)
    user = await auth_service.create_user(
        email=form.email,
        password=form.password,
        username=form.username,
    )
    return RegisterResponse(
        status=True,
        message="Register user successfully.",
        payload=UserInfo.model_validate(user),
    )


@router.post(
    "/refresh-token",
    response_model=LoginResponse,
)
async def refresh_access_token(
    session: SessionDep,
    request: RefreshTokenRequest,
) -> LoginResponse:
    """Refresh the token."""
    auth_service = AuthService(session=session)
    token = await auth_service.refresh_token(
        refresh_token=request.refresh_token,
    )
    return LoginResponse(
        status=True,
        message="Refresh token successfully",
        payload=token,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
)
async def logout(
    current_user: CurrentUser,
    session: SessionDep,
) -> LogoutResponse:
    """Logout user."""
    return LogoutResponse(
        status=True,
        message="Logout successfully",
    )
