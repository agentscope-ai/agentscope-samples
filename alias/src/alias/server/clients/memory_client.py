# -*- coding: utf-8 -*-
# mypy: disable-error-code="name-defined"
from http import HTTPStatus
from typing import Optional
from loguru import logger
from alias.server.core.config import settings
from alias.server.exceptions.base import ServiceError
from alias.server.exceptions.service import MemoryServiceError

from .base_client import BaseClient


class MemoryClient(BaseClient):
    base_url: Optional[str] = settings.USER_PROFILING_BASE_URL

    async def record_action(
        self,
        action: "Action",  # noqa: F821
    ):
        if self.base_url is None:
            return None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await self._request(
                method="POST",
                path="user_profiling/record_action",
                headers=headers,
                data=action,
            )
            if response.status_code == HTTPStatus.OK:
                return response.json()
            else:
                raise MemoryServiceError(
                    code=response.status_code,
                    message=(
                        f"Memory Service record action error: "
                        f"{response.text}"
                    ),
                )
        except ServiceError as e:
            logger.error(e)
            raise MemoryServiceError(code=e.code, message=e.message) from e
        except Exception as e:
            logger.error(e)
            raise MemoryServiceError(message=str(e)) from e
