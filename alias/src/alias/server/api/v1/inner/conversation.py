# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
import uuid
from typing import Optional

from fastapi import APIRouter

from alias.server.api.deps import SessionDep
from alias.server.models.conversation import Conversation
from alias.server.schemas.common import PaginationParams
from alias.server.schemas.response import PagePayload, ResponseBase
from alias.server.services.conversation_service import (
    ConversationService,
)


class ListConversationsResponse(ResponseBase):
    payload: PagePayload[Conversation]


class GetConversationResponse(ResponseBase):
    payload: Conversation


router = APIRouter(prefix="/conversations", tags=["/inner/conversations"])


@router.get("", response_model=ListConversationsResponse)
async def list_conversations(
    session: SessionDep,
    user_id: uuid.UUID,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    order_by: Optional[str] = None,
    order_direction: Optional[str] = None,
) -> ListConversationsResponse:
    """List conversations."""
    pagination = PaginationParams.create(
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction,
    )

    service = ConversationService(session=session)

    filters = {"user_id": user_id}
    total = await service.count_by_fields(filters)
    conversations = await service.paginate(
        filters=filters,
        pagination=pagination,
    )

    return ListConversationsResponse(
        status=True,
        message="List conversation successfully.",
        payload=PagePayload(
            total=total,
            items=conversations,
        ),
    )


@router.get("/{conversation_id}", response_model=GetConversationResponse)
async def get_conversation(
    session: SessionDep,
    conversation_id: uuid.UUID,
) -> GetConversationResponse:
    """Get conversation."""
    service = ConversationService(session=session)
    conversation = await service.get(
        id=conversation_id,
    )
    return GetConversationResponse(
        status=True,
        message="Get conversation successfully.",
        payload=conversation,
    )
