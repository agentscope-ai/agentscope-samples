# -*- coding: utf-8 -*-
"""The jwt related services"""

import jwt
from loguru import logger

from alias.server.core.config import settings
from alias.server.exceptions.service import (
    InvalidTokenError,
    TokenExpiredError,
)


class JwtService:
    """Service layer for jwt token."""

    def __init__(self) -> None:
        """Initialize the service layer for jwt token."""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM

    def encode(self, payload: dict) -> str:
        return jwt.encode(
            payload=payload,
            key=self.secret_key,
            algorithm=self.algorithm,
        )

    def decode(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                jwt=token,
                key=self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            logger.error("JWT token is expired.", token=token)
            raise TokenExpiredError(
                extra_info={"token": token, "error": str(e)},
            ) from e
        except (jwt.InvalidTokenError, jwt.InvalidSignatureError) as e:
            logger.error(f"Invalid JWT token: {token}", token=token)
            raise InvalidTokenError(
                extra_info={"token": token, "error": str(e)},
            ) from e
