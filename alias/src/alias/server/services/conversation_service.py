# -*- coding: utf-8 -*-
# pylint: disable=C0301 W0622
# mypy: disable-error-code="arg-type"

import uuid
from typing import List, Optional, Tuple, Union, Dict, Any

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.dao.conversation_dao import ConversationDao
from alias.server.exceptions.service import (
    AccessDeniedError,
    ConversationNotFoundError,
)
from alias.server.core.config import settings
from alias.server.models.conversation import Conversation
from alias.server.models.message import Message
from alias.server.models.plan import Plan, Roadmap
from alias.server.schemas.chat import ChatMode
from alias.server.schemas.common import PaginationParams
from alias.server.services.action_service import ActionService
from alias.server.services.base_service import BaseService
from alias.server.services.message_service import MessageService
from alias.server.services.plan_service import PlanService
from alias.server.services.state_service import StateService

from alias.server.utils.timestamp import get_current_time

from alias.runtime.alias_sandbox import AliasSandbox


class ConversationService(BaseService[Conversation]):
    _model_cls = Conversation
    _dao_cls = ConversationDao

    def __init__(
        self,
        session: AsyncSession,
    ):
        """Initialize conversation service."""
        super().__init__(session)
        self.message_service = MessageService(session=session)
        self.plan_service = PlanService(session=session)
        self.state_service = StateService(session=session)

    async def _validate_exists(self, instance_id: uuid.UUID) -> None:
        conversation = await self.get(instance_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": instance_id},
            )

    async def _validate_update(
        self,
        instance_id: uuid.UUID,
        obj_in: Union[Dict[str, Any], Conversation],
    ) -> None:
        conversation = await self.get(instance_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": instance_id},
            )

    async def _validate_delete(self, instance_id: uuid.UUID) -> None:
        conversation = await self.get(instance_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": instance_id},
            )

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        name: Optional[str] = "",
        description: Optional[str] = "",
        chat_mode: Optional[ChatMode] = ChatMode.GENERAL,
    ):
        sandbox = AliasSandbox(
            base_url=settings.SANDBOX_URL,
            bearer_token=settings.SANDBOX_BEARER_TOKEN,
        )
        sandbox.__enter__()

        conversation_data = Conversation(
            user_id=user_id,
            name=name or "New conversation",
            description=description,
            sandbox_id=sandbox.sandbox_id,
            sandbox_url=sandbox.desktop_url.replace(
                "localhost",
                settings.SANDBOX_PUBLIC_HOST,
            ),
            chat_mode=chat_mode,
        )
        conversation = await self.create(conversation_data)
        logger.info(f"Created conversation: {conversation.id}")
        return conversation

    async def get_sandbox(self, conversation_id: uuid.UUID) -> AliasSandbox:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )
        sandbox = AliasSandbox(
            sandbox_id=conversation.sandbox_id,
            base_url=settings.SANDBOX_URL,
            bearer_token=settings.SANDBOX_BEARER_TOKEN,
        )
        return sandbox

    async def list_conversations(
        self,
        user_id: uuid.UUID,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[int, List[Conversation]]:
        filters = {"user_id": user_id}
        total = await self.count_by_fields(filters=filters)
        conversations = await self.paginate(
            filters={"user_id": user_id},
            pagination=pagination,
        )
        return total, conversations

    async def list_conversation_messages(
        self,
        user_id: uuid.UUID,  # pylint: disable=W0613
        conversation_id: uuid.UUID,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[int, List[Message]]:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )
        if conversation.user_id != user_id:
            raise AccessDeniedError(
                extra_info={"conversation_id": conversation_id},
            )
        filters = {"conversation_id": conversation_id}
        total = await self.message_service.count_by_fields(filters=filters)
        messages = await self.message_service.paginate(
            filters=filters,
            pagination=pagination,
        )
        return total, messages

    async def delete_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        """Delete conversation and all its sessions."""
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )

        if conversation.user_id != user_id:
            raise AccessDeniedError(
                extra_info={"conversation_id": conversation_id},
            )

        await self.message_service.delete_messages(
            conversation_id=conversation_id,
        )
        await self.state_service.delete_state(conversation_id=conversation_id)
        await self.plan_service.delete_plan(conversation_id=conversation_id)

        sandbox = AliasSandbox(
            sandbox_id=conversation.sandbox_id,
            base_url=settings.SANDBOX_URL,
            bearer_token=settings.SANDBOX_BEARER_TOKEN,
        )
        sandbox._cleanup()  # pylint: disable=W0212
        await self.delete(conversation_id)
        return conversation

    async def get_roadmap(self, conversation_id: uuid.UUID) -> Plan:
        roadmap = await self.plan_service.get_roadmap(conversation_id)
        return roadmap

    async def update_roadmap(
        self,
        conversation_id: uuid.UUID,
        roadmap: Roadmap,
        user_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> Plan:
        previous_roadmap = await self.plan_service.get_roadmap(conversation_id)

        action_service = ActionService()
        await action_service.record_edit_roadmap(
            user_id=user_id,
            conversation_id=conversation_id,
            previous=previous_roadmap,
            current=roadmap,
        )

        roadmap = await self.plan_service.update_roadmap(
            conversation_id=conversation_id,
            roadmap=roadmap,
            **kwargs,
        )

        return roadmap

    async def update_conversation(
        self,
        conversation_id: uuid.UUID,
        **kwargs,
    ) -> Conversation:
        conversation = await self.get(conversation_id)
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
                conversation.update_time = get_current_time()
        return await self.update(conversation_id, conversation)

    async def collect_conversation(
        self,
        conversation_id: uuid.UUID,
        collect: Optional[bool] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )

        action_service = ActionService()
        await action_service.record_collect_session(
            user_id=user_id,
            conversation_id=conversation_id,
            previous=conversation.collected,
            current=collect,
        )
        conversation.collected = collect
        return await self.update(conversation_id, conversation)

    async def share_conversation(
        self,
        conversation_id: uuid.UUID,
        share: Optional[bool] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )
        if conversation.user_id != user_id:
            raise AccessDeniedError(
                extra_info={"conversation_id": conversation_id},
            )
        conversation.shared = share
        return await self.update(conversation_id, conversation)

    async def pin_conversation(
        self,
        conversation_id: uuid.UUID,
        pin: Optional[bool] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )

        if conversation.user_id != user_id:
            raise AccessDeniedError(
                extra_info={"conversation_id": conversation_id},
            )
        conversation.pinned = pin
        return await self.update(conversation_id, conversation)

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )
        return conversation
