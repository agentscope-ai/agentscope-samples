# -*- coding: utf-8 -*-
from typing import Annotated, Optional

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.core.config import settings
from alias.server.db.init_db import get_session
from alias.server.exceptions.base import PermissionDeniedError
from alias.server.exceptions.service import AccessDeniedError
from alias.server.models.user import User
from alias.server.services.auth_service import AuthService

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/",
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(session: SessionDep, token: TokenDep) -> User:
    return await AuthService(session=session).get_user_by_token(token=token)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError()
    return current_user


CurrentSuperUser = Annotated[User, Depends(get_current_active_superuser)]


async def verify_inner_api_key(
    api_key: Optional[str] = Header(None, alias="X-Inner-Api-Key"),
) -> bool:
    if not settings.INNER_API_KEY:
        return True

    if api_key != settings.INNER_API_KEY:
        raise AccessDeniedError(message="Invalid inner api key")

    return True


InnerAPIAuth = Depends(verify_inner_api_key)
