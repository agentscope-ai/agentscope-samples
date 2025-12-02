# -*- coding: utf-8 -*-
"""The user related services"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.core.config import settings
from alias.server.exceptions.service import (
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    UserNotFoundError,
)
from alias.server.models.user import User
from alias.server.schemas.auth import Token
from alias.server.services.jwt_service import JwtService
from alias.server.services.user_service import UserService
from alias.server.utils.security import (
    verify_password,
)


class AuthService:
    """Service layer for login."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Initialize the service layer for login."""
        self.user_service = UserService(
            session=session,
        )

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate the user by email and password."""
        user = await self.user_service.get_user_by_email(email=email)
        if not user:
            raise UserNotFoundError(extra_info={"email": email})
        if user.password and not verify_password(password, user.password):
            raise IncorrectPasswordError()
        user = await self.user_service.update_last_login_info(user_id=user.id)
        return user

    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh the jwt token by refresh token."""
        user = await self.get_user_by_token(refresh_token)
        return await self.get_jwt_token(user_id=user.id)

    async def get_jwt_token(self, user_id: uuid.UUID) -> Token:
        """Get the jwt token by user id."""
        expire_time = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        access_payload = {
            "exp": expire_time,
            "user_id": str(user_id),
        }
        access_token = JwtService().encode(access_payload)

        refresh_payload = {
            "user_id": str(user_id),
            "timestamp": str(datetime.now(timezone.utc)),
        }
        refresh_token = JwtService().encode(refresh_payload)

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def get_user_by_token(self, token: str) -> User:
        """Get the user info by token."""
        payload = JwtService().decode(token)
        user_id = uuid.UUID(payload.get("user_id"))
        user = await self.user_service.get(user_id)
        if not user:
            raise UserNotFoundError(extra_info={"user_id": user_id})
        return user

    async def create_user(
        self,
        email: str,
        username: str,
        password: Optional[str] = None,
        oauth_id: Optional[str] = None,
        oauth_provider: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> User:
        """Create a new user."""
        user = await self.user_service.get_user_by_email(email=email)
        if user:
            raise EmailAlreadyExistsError()

        user = await self.user_service.create_user(
            email=email,
            password=password,
            username=username,
            is_superuser=True,
            oauth_id=oauth_id,
            oauth_provider=oauth_provider,
            parent_id=user_id,
        )
        return user
