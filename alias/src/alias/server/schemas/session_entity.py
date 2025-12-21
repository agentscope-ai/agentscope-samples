# -*- coding: utf-8 -*-
import uuid
from typing import Optional
from sqlmodel import SQLModel
from alias.server.schemas.chat import LanguageType, ChatMode, ChatType
from alias.server.models.message import RoadmapChange


class SessionEntity(SQLModel):
    user_id: uuid.UUID
    conversation_id: uuid.UUID
    task_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    language_type: Optional[LanguageType] = LanguageType.EN_US
    chat_mode: Optional[ChatMode] = ChatMode.GENERAL
    chat_type: Optional[ChatType] = ChatType.TASK
    query: Optional[str] = None
    roadmap: Optional[RoadmapChange] = None
    use_long_term_memory_service: Optional[bool] = False

    def ids(self):
        return {
            "task_id": str(self.task_id),
            "conversation_id": str(self.conversation_id),
            "message_id": str(self.message_id),
            "user_id": str(self.user_id),
        }
