# -*- coding: utf-8 -*-

import uuid
from typing import List, Optional

from fastapi.encoders import jsonable_encoder
from sqlmodel import Field, SQLModel

from alias.server.models.action import FeedbackType
from alias.server.models.message import DetailedMessageBase

from .response import ResponseBase


class MessageInfo(DetailedMessageBase):
    id: uuid.UUID

    def model_dump(self) -> dict:
        data = super().model_dump()
        data = jsonable_encoder(data)
        return data


class GetMessageResponse(ResponseBase):
    payload: MessageInfo


class PageMessageInfo(SQLModel):
    total: int
    items: List[MessageInfo]


class ListMessagesResponse(ResponseBase):
    payload: PageMessageInfo


class UpdateMessageRequest(SQLModel):
    feedback: Optional[FeedbackType] = Field(
        default=None,
        description="Feedback can be 'like', 'dislike', or None",
    )
    collect: Optional[bool] = False


class UpdateMessageResponse(ResponseBase):
    payload: MessageInfo
