# -*- coding: utf-8 -*-
# mypy: disable-error-code="name-defined"

import uuid
from typing import Optional, Union
from http import HTTPStatus
from loguru import logger

from pydantic import BaseModel
from alias.server.core.config import settings
from alias.server.exceptions.base import ServiceError
from alias.server.exceptions.service import (
    MessageServiceError,
    PlanServiceError,
    StateServiceError,
)
from alias.server.models.message import Message
from alias.server.models.plan import Plan
from alias.server.models.state import State
from .base_client import BaseClient


class InnerClient(BaseClient):
    base_url: Optional[str] = f"{settings.BACKEND_URL}/api/v1/inner/"

    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[dict] = None,
        data: Optional[Union[dict, BaseModel, str]] = None,
        params: Optional[dict] = None,
    ):
        headers = headers or {}
        if settings.INNER_API_KEY:
            headers["X-Inner-Api-Key"] = settings.INNER_API_KEY

        return await super()._request(
            method=method,
            path=path,
            headers=headers,
            data=data,
            params=params,
        )

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
    ):
        logger.info(f"Get message: {conversation_id}")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        params = {
            "conversation_id": str(conversation_id),
        }
        try:
            response = await self._request(
                method="GET",
                path="messages",
                headers=headers,
                params=params,
            )
            if response.status_code == HTTPStatus.OK:
                payload = response.json().get("payload", {})
                items = payload.get("items", [])
                return [Message.model_validate(item) for item in items]
            else:
                raise MessageServiceError(
                    code=response.status_code,
                    message=f"Message Service error: {response}",
                )
        except ServiceError as e:
            logger.error(str(e))
            raise MessageServiceError(code=e.code, message=e.message) from e
        except Exception as e:
            logger.error(str(e))
            raise MessageServiceError(message=str(e)) from e

    async def get_plan(
        self,
        conversation_id: uuid.UUID,
    ):
        logger.info(f"Get plan: {conversation_id}")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        params = {
            "conversation_id": str(conversation_id),
        }
        try:
            response = await self._request(
                method="GET",
                path="plans",
                headers=headers,
                params=params,
            )
            if response.status_code == HTTPStatus.OK:
                payload = response.json().get("payload", {})
                items = payload.get("items", [])
                return (
                    [Plan.model_validate(item) for item in items][0]
                    if items
                    else None
                )
            else:
                raise PlanServiceError(
                    code=response.status_code,
                    message=f"Plan Service error: {response.text}",
                )
        except ServiceError as e:
            logger.error(str(e))
            raise PlanServiceError(code=e.code, message=e.message) from e

    async def get_state(
        self,
        conversation_id: uuid.UUID,
    ):
        logger.info(f"Get state: {conversation_id}")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        params = {
            "conversation_id": str(conversation_id),
        }
        try:
            response = await self._request(
                method="GET",
                path="state",
                headers=headers,
                params=params,
            )
            if response.status_code == HTTPStatus.OK:
                payload = response.json().get("payload", {})
                items = payload.get("items", [])
                return (
                    [State.model_validate(item) for item in items][0]
                    if items
                    else None
                )
            else:
                raise StateServiceError(
                    code=response.status_code,
                    message=f"State Service error: {response.text}",
                )
        except ServiceError as e:
            logger.error(str(e))
            raise StateServiceError(code=e.code, message=e.message) from e
