# -*- coding: utf-8 -*-
# mypy: disable-error-code="name-defined"
from http import HTTPStatus
from typing import Optional
from loguru import logger
import httpx
from alias.server.core.config import settings
from alias.server.exceptions.base import ServiceError
from alias.server.exceptions.service import MemoryServiceError

from .base_client import BaseClient


class MemoryClient(BaseClient):
    base_url: Optional[str] = settings.USER_PROFILING_BASE_URL

    @classmethod
    async def is_available(cls) -> bool:
        """
        Check if memory service is available and healthy.

        Returns:
            True if memory service is configured and can be reached,
            False otherwise
        """
        if settings.USER_PROFILING_BASE_URL is None:
            return False

        # Check if the service is actually reachable by pinging the health
        # endpoint
        try:
            health_url = (
                f"{settings.USER_PROFILING_BASE_URL.rstrip('/')}/health"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == HTTPStatus.OK:
                    logger.debug(
                        f"Memory service health check passed: {health_url}",
                    )
                    return True
                else:
                    logger.warning(
                        f"Memory service health check failed with status "
                        f"{response.status_code}: {health_url}",
                    )
                    return False
        except httpx.TimeoutException:
            logger.warning(
                f"Memory service health check timeout: "
                f"{settings.USER_PROFILING_BASE_URL}",
            )
            return False
        except httpx.RequestError as e:
            logger.warning(
                f"Memory service health check failed: {e}",
            )
            return False
        except Exception as e:
            logger.warning(
                f"Unexpected error during memory service health check: {e}",
            )
            return False

    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if memory service is configured (synchronous, no network call).

        Note: This only checks if the service URL is configured, it does NOT
        verify that the service is actually available or healthy. For actual
        health checks, use the async is_available() method instead.

        Returns:
            True if memory service URL is configured, False otherwise
        """
        return settings.USER_PROFILING_BASE_URL is not None

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
                path="alias_memory_service/record_action",
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

    async def retrieve_user_profiling(
        self,
        uid: str,
        query: str,
        limit: int = 3,
        threshold: float = 0.3,
    ) -> Optional[str]:
        """
        Retrieve user profiling information based on query.
        Only items with is_confirmed == 1 will be retrieved and returned.

        Args:
            uid: User ID
            query: Query string to search for relevant profiling

        Returns:
            String containing retrieved profiling data (only confirmed items),
            or None if service is unavailable or no confirmed items found
        """
        if self.base_url is None:
            return None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await self._request(
                method="POST",
                path="alias_memory_service/user_profiling/retrieve",
                headers=headers,
                data={
                    "uid": uid,
                    "query": query,
                    "limit": limit,
                    "threshold": threshold,
                },
            )
            if response.status_code == HTTPStatus.OK:
                result = response.json()
                profiling_result_tmp = (
                    result.get("data").get("profiling").get("results")
                )

                profiling_result = None
                if profiling_result_tmp and len(profiling_result_tmp) > 0:
                    profiling_result = "\n".join(
                        [
                            item["memory"]
                            for item in profiling_result_tmp
                            if item.get("metadata", {}).get("is_confirmed")
                            == 1
                        ],
                    )
                    if profiling_result:  # Only log if there's actual content
                        logger.debug(f"Profiling result: {profiling_result}")
                    else:
                        profiling_result = None

                return profiling_result
            else:
                logger.warning(
                    f"Memory Service retrieve error: {response.status_code} - "
                    f"{response.text}",
                )
                return None
        except ServiceError as e:
            logger.warning(f"Memory Service retrieve error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error retrieving profiling: {e}")
            return None

    async def retrieve_tool_memory(
        self,
        uid: str,
        query: str,
    ) -> Optional[str]:
        """
        Retrieve tool memory information based on query.

        Args:
            uid: User ID
            query: Query string to search for relevant tool memory
                (e.g., "web_search,write_file" for specific tools)

        Returns:
            String containing retrieved tool memory answer, or None if
            service is unavailable

        Example:
            retrieve_tool_memory(uid="user123", query="web_search,write_file")
        """
        if self.base_url is None:
            return None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await self._request(
                method="POST",
                path="alias_memory_service/tool_memory/retrieve",
                headers=headers,
                data={"uid": uid, "query": query},
            )
            if response.status_code == HTTPStatus.OK:
                result = response.json()
                return result.get("data")
            else:
                logger.warning(
                    f"Memory Service retrieve tool memory error: "
                    f"{response.status_code} - {response.text}",
                )
                return None
        except ServiceError as e:
            logger.warning(f"Memory Service retrieve tool memory error: {e}")
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error retrieving tool memory: {e}",
            )
            return None

    async def add_to_longterm_memory(
        self,
        uid: str,
        content: list,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add content to user profiling.

        Args:
            uid: User ID
            content: Content to add to user profiling
            session_id: Session ID

        Returns:
            String containing the result of the add operation, or None if
            service is unavailable
        """
        if self.base_url is None:
            return None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await self._request(
                method="POST",
                path="alias_memory_service/user_profiling/add",
                headers=headers,
                data={
                    "uid": uid,
                    "content": content,
                    "session_id": session_id,
                },
            )
            if response.status_code == HTTPStatus.OK:
                result = response.json()
                return result.get("data")
            else:
                logger.warning(
                    f"Memory Service add to user profiling error: "
                    f"{response.status_code} - {response.text}",
                )
                return None
        except ServiceError as e:
            logger.warning(f"Memory Service add to user profiling error: {e}")
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error adding to user profiling: {e}",
            )
            return None
