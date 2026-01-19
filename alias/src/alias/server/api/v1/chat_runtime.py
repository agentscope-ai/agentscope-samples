# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
import json
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from starlette.types import Receive

from alias.server.api.deps import CurrentUser
from alias.server.exceptions.base import BaseError
from alias.server.schemas.chat import (
    ChatRequest,
    StopChatPayload,
    StopChatResponse,
)
from alias.server.services.chat_service import ChatService
from alias.server.utils.request_context import request_context_var
from alias.runtime.runtime_compat.runner.alias_runner import AliasRunner

router = APIRouter(prefix="/conversations", tags=["conversations/chat"])


class EnhancedStreamingResponse(StreamingResponse):
    """
    StreamingResponse with client disconnect handling.
    """

    def __init__(
        self,
        content: Any,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(content, *args, **kwargs)
        self.user_id = user_id
        self.task_id = task_id

    async def listen_for_disconnect(self, receive: Receive) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                logger.warning(
                    f"Chat stopped by disconnect from client: "
                    f"task_id={self.task_id}",
                )
                service = ChatService()
                await service.stop_chat(
                    user_id=self.user_id,
                    task_id=self.task_id,
                )
                break


def _to_raw_sse_event(data: Any) -> str:
    """
    Convert a chunk from runner.stream_query_native into
    a raw SSE event string.
    """
    if data == "[DONE]":
        return "data: [DONE]\n\n"

    if hasattr(data, "model_dump"):
        data = data.model_dump()

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def event_generator(
    runner: AliasRunner,
    request_dict: dict,
    **runner_kwargs: Any,
) -> AsyncIterator[str]:
    """
    Convert AliasRunner.stream_query_native output into
    a raw SSE string stream.
    """
    try:
        async for chunk in runner.stream_query_native(
            request_dict,
            **runner_kwargs,
        ):
            yield _to_raw_sse_event(chunk)
    except Exception as e:
        if not isinstance(e, BaseError):
            e = BaseError(code=500, message=str(e))
        error_data = {
            "code": e.code,
            "message": e.message,
        }
        yield _to_raw_sse_event(error_data)
        yield _to_raw_sse_event("[DONE]")


@router.post("/{conversation_id}/chat")
async def chat(
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
    chat_request: ChatRequest,
) -> EnhancedStreamingResponse:
    """Run chat via AliasRunner and stream results as SSE."""
    request_context = request_context_var.get()
    request_id = request_context.request_id
    task_id = uuid.UUID(request_id) if request_id else uuid.uuid4()
    user_id = current_user.id

    from alias.runtime.runtime_compat.runner.alias_runner_singleton import (
        get_alias_runner,
    )

    runner = await get_alias_runner()

    request_dict = chat_request.model_dump()

    return EnhancedStreamingResponse(
        event_generator(
            runner,
            request_dict,
            user_id=user_id,
            conversation_id=conversation_id,
            task_id=task_id,
        ),
        media_type="text/event-stream",
        user_id=user_id,
        task_id=task_id,
    )


@router.post(
    "/{conversation_id}/chat/{task_id}/stop",
    response_model=StopChatResponse,
)
async def stop_chat(
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
    task_id: uuid.UUID,
) -> StopChatResponse:
    service = ChatService()
    await service.stop_chat(
        user_id=current_user.id,
        task_id=task_id,
    )
    return StopChatResponse(
        status=True,
        message="Stop chat successfully.",
        payload=StopChatPayload(
            conversation_id=conversation_id,
            task_id=task_id,
        ),
    )
