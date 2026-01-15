# -*- coding: utf-8 -*-
import uuid
from enum import Enum
from typing import List, Optional

from sqlmodel import SQLModel
from alias.server.models.message import RoadmapChange
from .response import ResponseBase


class ChatType(str, Enum):
    CHAT = "chat"
    TASK = "task"


class ChatMode(str, Enum):
    GENERAL = "general"
    DEEPREASONING = "dr"
    BROWSER = "browser"
    DATASCIENCE = "ds"
    FINANCE = "finance"


class LanguageType(str, Enum):
    ZH_HANS = "zh-Hans"
    EN_US = "en-US"


class StopChatPayload(SQLModel):
    task_id: uuid.UUID
    conversation_id: uuid.UUID


class StopChatResponse(ResponseBase):
    payload: StopChatPayload


class ChatRequest(SQLModel):
    query: str
    files: List[uuid.UUID] = []
    chat_type: Optional[ChatType] = ChatType.TASK
    language_type: Optional[LanguageType] = LanguageType.EN_US
    chat_mode: Optional[ChatMode] = ChatMode.GENERAL
    roadmap: Optional[RoadmapChange] = None
    use_long_term_memory_service: Optional[bool] = False


class ContinueChatRequest(SQLModel):
    body: Optional[dict] = None
