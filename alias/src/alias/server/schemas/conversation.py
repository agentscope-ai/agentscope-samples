# -*- coding: utf-8 -*-
import uuid
from typing import List, Optional

from sqlmodel import SQLModel

from alias.server.models.conversation import ConversationBase
from alias.server.schemas.chat import ChatMode
from .response import ResponseBase


class ConversationInfo(ConversationBase):
    id: uuid.UUID


class CreateConversationRequest(SQLModel):
    name: Optional[str] = ""
    description: Optional[str] = ""
    chat_mode: Optional[ChatMode] = ChatMode.GENERAL


class CreateConversationResponse(ResponseBase):
    payload: ConversationInfo


class PageConversationInfo(SQLModel):
    total: int
    items: List[ConversationInfo]


class ListConversationsResponse(ResponseBase):
    payload: PageConversationInfo


class GetConversationResponse(ResponseBase):
    payload: ConversationInfo


class DeleteConversationPayload(SQLModel):
    conversation_id: uuid.UUID


class DeleteConversationResponse(ResponseBase):
    payload: DeleteConversationPayload


class ShareFileRequest(SQLModel):
    filename: str
    share: Optional[bool] = True


class UpdateConversationRequest(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    collect: Optional[bool] = None
    share: Optional[bool] = None
    pin: Optional[bool] = None


class UpdateConversationResponse(SQLModel):
    payload: ConversationInfo
