# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, Optional, Union

from fastapi_limiter import FastAPILimiter
from pydantic import ValidationError

from agentscope_runtime.engine.runner import Runner
from agentscope_runtime.engine.schemas.agent_schemas import (
    AgentRequest,
    AgentResponse,
    Error,
    RunStatus,
    SequenceNumberGenerator,
)

from alias.server.db.init_db import (
    close_database,
    initialize_database,
    session_scope,
)
from alias.server.core.task_manager import task_manager
from alias.server.exceptions.base import BaseError
from alias.runtime.runtime_compat.adapter.alias_stream_adapter import (
    adapt_alias_message_stream,
)
from alias.server.schemas.chat import ChatRequest
from alias.server.services.chat_service import ChatService
from alias.server.services.conversation_service import ConversationService
from alias.server.utils.logger import setup_logger
from alias.server.utils.redis import redis_client


class AliasRunner(Runner):
    FRAMEWORK_TYPE = "Alias"

    def __init__(
        self,
        default_chat_mode: str = "general",
        default_conv_name: str = "webui",
    ) -> None:
        super().__init__()
        self.framework_type = self.FRAMEWORK_TYPE
        self.default_chat_mode = default_chat_mode
        self.default_conv_name = default_conv_name

        self._session_conv_cache: Dict[str, uuid.UUID] = {}

    async def stop(self) -> None:
        if not getattr(self, "_health", False):
            return
        await super().stop()

    async def query_handler(self, *args: Any, **kwargs: Any) -> Any:
        user_id: uuid.UUID = kwargs["user_id"]
        conversation_id: uuid.UUID = kwargs["conversation_id"]
        chat_request: ChatRequest = kwargs["chat_request"]
        task_id: uuid.UUID = kwargs.get("task_id") or uuid.uuid4()

        service = ChatService()
        response_gen = await service.chat(
            user_id=user_id,
            conversation_id=conversation_id,
            chat_request=chat_request,
            task_id=task_id,
        )
        return response_gen

    async def init_handler(self, *args: Any, **kwargs: Any) -> None:
        print("🚀 Starting Alias API Server...")
        setup_logger()

        await initialize_database()
        await task_manager.start()

        await redis_client.ping()
        try:
            await FastAPILimiter.init(redis_client)
        except Exception as exc:
            print(f"redis init error: {str(exc)}")

        print("✅ Alias startup complete.")

    async def shutdown_handler(self, *args: Any, **kwargs: Any) -> None:
        print("Executing Alias shutdown logic...")
        await task_manager.stop()
        await close_database()
        print("Alias shutdown complete.")

    @staticmethod
    def _extract_text_from_agent_request(req_dict: Dict[str, Any]) -> str:
        agent_input = req_dict.get("input")
        if isinstance(agent_input, str):
            return agent_input

        if isinstance(agent_input, list) and agent_input:
            last = agent_input[-1]
            if isinstance(last, dict):
                content = last.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    for blk in reversed(content):
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            return blk.get("text") or ""
                if "text" in last and isinstance(last["text"], str):
                    return last["text"]
        return ""

    @staticmethod
    def _to_uuid(val: Any) -> Optional[uuid.UUID]:
        if val is None:
            return None
        if isinstance(val, uuid.UUID):
            return val
        try:
            return uuid.UUID(str(val))
        except Exception:
            return None

    @staticmethod
    def _stable_uuid_from_string(s: str) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"alias::{s}")

    async def _get_or_create_conversation_id(
        self,
        session_id: str,
        user_uuid: uuid.UUID,
    ) -> uuid.UUID:
        if session_id in self._session_conv_cache:
            return self._session_conv_cache[session_id]

        async with session_scope() as session:
            service = ConversationService(session=session)
            conversation = await service.create_conversation(
                user_id=user_uuid,
                name=self.default_conv_name,
                description="created by AgentScope Runtime WebUI",
                chat_mode=self.default_chat_mode,
            )

        conv_id = getattr(conversation, "id", None)
        conv_id = (
            conv_id
            if isinstance(conv_id, uuid.UUID)
            else self._to_uuid(conv_id)
        )
        if conv_id is None:
            raise RuntimeError(
                "ConversationService.create_conversation() "
                "returned invalid id: "
                f"{conversation}",
            )

        self._session_conv_cache[session_id] = conv_id
        return conv_id

    async def stream_query_native(
        self,
        request: Union[AgentRequest, dict],
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        if not self._health:
            raise RuntimeError(
                "Runner has not been started. Please call "
                "'await runner.start()' or use 'async with Runner()' "
                "before calling 'stream_query'.",
            )

        req_dict = (
            request if isinstance(request, dict) else request.model_dump()
        )
        user_id = kwargs.get("user_id") or self._to_uuid(
            req_dict.get("user_id"),
        )
        conversation_id = kwargs.get("conversation_id") or self._to_uuid(
            req_dict.get("conversation_id"),
        )
        task_id = (
            kwargs.get("task_id")
            or self._to_uuid(req_dict.get("task_id"))
            or uuid.uuid4()
        )

        if user_id is None or conversation_id is None:
            yield {
                "error": "missing_context",
                "code": 422,
                "message": (
                    "Native mode requires user_id and conversation_id "
                    "in kwargs or request body."
                ),
            }
            return

        try:
            chat_request_obj = ChatRequest.model_validate(req_dict)
        except ValidationError as exc:
            yield {
                "error": "invalid_request",
                "code": 422,
                "message": "ChatRequest validation failed",
                "detail": exc.errors(),
            }
            return
        except Exception as exc:
            yield {
                "error": "invalid_request",
                "code": 500,
                "message": str(exc),
            }
            return

        try:
            result = self.query_handler(
                user_id=user_id,
                conversation_id=conversation_id,
                task_id=task_id,
                chat_request=chat_request_obj,
            )
            if asyncio.iscoroutine(result):
                result = await result

            async for chunk in result:
                yield chunk

        except Exception as exc:
            if isinstance(exc, BaseError):
                yield {"error": exc.message, "code": exc.code}
            else:
                yield {
                    "error": str(exc),
                    "code": 500,
                    "error_type": exc.__class__.__name__,
                }
            return

        yield "[DONE]"

    async def stream_query(
        self,
        request: Union[AgentRequest, dict],
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        if not self._health:
            raise RuntimeError(
                "Runner has not been started. Please call "
                "'await runner.start()' or use 'async with Runner()' "
                "before calling 'stream_query'.",
            )

        if isinstance(request, AgentRequest):
            req_dict = request.model_dump()
        elif isinstance(request, dict):
            req_dict = request
        else:
            if hasattr(request, "model_dump"):
                req_dict = request.model_dump()
            else:
                req_dict = dict(request)

        request_id = req_dict.get("id") or str(uuid.uuid4())
        session_id = req_dict.get("session_id") or f"session_{uuid.uuid4()}"
        seq_gen = SequenceNumberGenerator()

        response = AgentResponse(id=request_id)
        response.session_id = session_id
        yield seq_gen.yield_with_sequence(response)

        response.in_progress()
        yield seq_gen.yield_with_sequence(response)

        user_text = self._extract_text_from_agent_request(req_dict)
        if not user_text:
            err = Error(
                code="422",
                message="Empty input text in AgentRequest.input.",
            )
            yield seq_gen.yield_with_sequence(response.failed(err))
            return

        raw_user_id = req_dict.get("user_id") or session_id
        user_uuid = self._to_uuid(
            raw_user_id,
        ) or self._stable_uuid_from_string(
            str(raw_user_id),
        )

        conversation_id = self._to_uuid(req_dict.get("conversation_id"))
        if conversation_id is None:
            try:
                conversation_id = await self._get_or_create_conversation_id(
                    session_id=session_id,
                    user_uuid=user_uuid,
                )
            except Exception as exc:
                err = Error(
                    code="500",
                    message=f"Failed to create conversation: {exc}",
                )
                yield seq_gen.yield_with_sequence(response.failed(err))
                return

        task_id = self._to_uuid(req_dict.get("task_id")) or uuid.uuid4()

        try:
            req_chat_mode = req_dict.get("chat_mode") or self.default_chat_mode

            chat_request_obj = ChatRequest.model_validate(
                {
                    "query": user_text,
                    "chat_mode": req_chat_mode,
                },
            )
        except ValidationError as exc:
            err = Error(
                code="422",
                message=f"ChatRequest validation failed: {exc}",
            )
            yield seq_gen.yield_with_sequence(response.failed(err))
            return

        try:
            result = self.query_handler(
                user_id=user_uuid,
                conversation_id=conversation_id,
                task_id=task_id,
                chat_request=chat_request_obj,
            )
            if asyncio.iscoroutine(result):
                result = await result

            async for event in adapt_alias_message_stream(result):
                try:
                    if (
                        getattr(event, "status", None) == RunStatus.Completed
                        and getattr(event, "object", None) == "message"
                    ):
                        response.add_new_message(event)
                except Exception:
                    # Best-effort bookkeeping
                    pass

                yield seq_gen.yield_with_sequence(event)

        except Exception as exc:
            if isinstance(exc, BaseError):
                err = Error(code=str(exc.code), message=exc.message)
            else:
                err = Error(
                    code="500",
                    message=f"Error happens in `query_handler`: {exc}",
                )
            yield seq_gen.yield_with_sequence(response.failed(err))
            return

        try:
            if response.output:
                response.usage = response.output[-1].usage
        except IndexError:
            # Avoid empty message
            pass

        yield seq_gen.yield_with_sequence(response.completed())
        return
