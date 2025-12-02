# -*- coding: utf-8 -*-
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from alias.server.api.deps import SessionDep
from alias.server.schemas.common import PaginationParams
from alias.server.schemas.response import PagePayload, ResponseBase
from alias.server.models.message import Message

from alias.server.services.message_service import MessageService


router = APIRouter(
    prefix="/messages",
    tags=["inner/messages"],
)


class ListMessagesResponse(ResponseBase):
    payload: PagePayload[Message]


class GetMessageResponse(ResponseBase):
    payload: Message


@router.get("", response_model=ListMessagesResponse)
async def list_messages(
    session: SessionDep,
    conversation_id: uuid.UUID,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    order_by: Optional[str] = None,
    order_direction: Optional[str] = None,
) -> ListMessagesResponse:
    """List chat messages for inner service."""
    try:
        pagination = PaginationParams.create(
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )

        service = MessageService(session=session)
        filters = {"conversation_id": conversation_id}

        total = await service.count_by_fields(filters)
        messages = await service.paginate(
            filters=filters,
            pagination=pagination,
        )

        return ListMessagesResponse(
            status=True,
            message="List messages successfully.",
            payload=PagePayload(
                total=total,
                items=messages,
            ),
        )
    except Exception as e:
        logger.error(f"Error listing messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list messages: {str(e)}",
        ) from e


@router.get("/{message_id}", response_model=GetMessageResponse)
async def get_message(
    session: SessionDep,
    message_id: uuid.UUID,
) -> GetMessageResponse:
    """Get message."""
    service = MessageService(session=session)
    message = await service.get(id=message_id)
    return GetMessageResponse(
        status=True,
        message="Get message successfully.",
        payload=message,
    )
