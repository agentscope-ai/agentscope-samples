# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
import json
import uuid

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
from alias.server.services.chat_service import (
    ChatService,
)
from alias.server.utils.request_context import request_context_var

router = APIRouter(prefix="/conversations", tags=["conversations/chat"])


class EnhancedStreamingResponse(StreamingResponse):
    """Enhanced StreamingResponse with disconnect handling"""

    def __init__(
        self,
        content,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        *args,
        **kwargs,
    ):
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


async def event_generator(generator):
    try:
        async for chunk in generator:
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        if not isinstance(e, BaseError):
            e = BaseError(code=500, message=str(e))
        error_data = {
            "code": e.code,
            "message": e.message,
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/{conversation_id}/chat")
async def chat(
    current_user: CurrentUser,
    conversation_id: uuid.UUID,
    chat_request: ChatRequest,
):
    request_context = request_context_var.get()
    request_id = request_context.request_id
    service = ChatService()
    task_id = uuid.UUID(request_id) if request_id else uuid.uuid4()
    user_id = current_user.id

    response = await service.chat(
        user_id=user_id,
        conversation_id=conversation_id,
        chat_request=chat_request,
        task_id=task_id,
    )

    return EnhancedStreamingResponse(
        event_generator(generator=response),
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
