# -*- coding: utf-8 -*-


import json
from typing import Optional, Union
import httpx
from loguru import logger
from pydantic import BaseModel

from alias.server.exceptions.base import ServiceError


class BaseClient:
    base_url: Optional[str] = None

    def _prepare_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _prepare_data(
        self,
        data: Optional[Union[dict, BaseModel, str]],
    ) -> Optional[str]:
        if data is None:
            return None

        if isinstance(data, str):
            return data
        elif isinstance(data, BaseModel):
            return data.json()
        elif isinstance(data, dict):
            return json.dumps(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[dict] = None,
        data: Optional[Union[dict, BaseModel, str]] = None,
        params: Optional[dict] = None,
    ):
        url = self._prepare_url(path)
        headers = headers or {}
        if headers.get("Content-Type") == "application/json":
            data = self._prepare_data(data)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=str(url),
                    headers=headers,
                    data=data,
                    params=params,
                )
                return response
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {str(e)}")
            raise ServiceError(
                message=f"Request to {path} timed out",
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Request failed: {str(e)}")
            raise ServiceError(
                message=f"Request to {path} failed: {str(e)}",
            ) from e
        except Exception as e:
            logger.error(str(e))
            raise ServiceError(
                message=f"Request {path} error: {str(e)}",
            ) from e
