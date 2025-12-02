# -*- coding: utf-8 -*-
import uuid
from typing import Any, Optional, Union
from alias.server.clients import MemoryClient
from alias.server.models.action import (
    FeedbackType,
)
from alias.server.schemas.chat import ChatType
from alias.server.schemas.action import (
    Action,
    ChatAction,
    EditRoadMapAction,
    FeedbackAction,
    SessionCollectionAction,
    ToolCollectionAction,
    TaskStopAction,
)


class ActionService:
    async def record_action(
        self,
        action: Union[Action, dict],
    ) -> Optional[dict]:
        if action is None:
            return None
        try:
            return await MemoryClient().record_action(action)
        except Exception:
            return None

    async def record_feedback(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        previous: Optional[FeedbackType] = None,
        current: Optional[FeedbackType] = None,
    ) -> None:
        action = FeedbackAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            previous=previous,
            current=current,
        )
        await self.record_action(action)

    async def record_task_stop(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> None:
        action = TaskStopAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            task_id=task_id,
        )
        await self.record_action(action)

    async def record_collect_tool(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        previous: Optional[bool] = False,
        current: Optional[bool] = False,
    ) -> None:
        action = ToolCollectionAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            previous=previous,
            current=current,
        )
        await self.record_action(action)

    async def record_collect_session(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        previous: Optional[bool] = False,
        current: Optional[bool] = False,
    ) -> None:
        action = SessionCollectionAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            previous=previous,
            current=current,
        )
        await self.record_action(action)

    async def record_chat(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_id: Optional[uuid.UUID] = None,
        query: Optional[str] = None,
        chat_type: Optional[ChatType] = None,
        history_length: int = 0,
    ) -> None:
        action = ChatAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            query=query,
            chat_type=chat_type,
            history_length=history_length,
        )
        await self.record_action(action)

    async def record_edit_roadmap(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        previous: Any,
        current: Any,
    ) -> None:
        action = EditRoadMapAction.create(
            user_id=user_id,
            conversation_id=conversation_id,
            previous=previous,
            current=current,
        )
        await self.record_action(action)
