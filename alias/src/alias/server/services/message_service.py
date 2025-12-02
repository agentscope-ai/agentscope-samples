# -*- coding: utf-8 -*-
import uuid
from typing import List, Optional, Tuple, Union, Dict, Any

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.dao.message_dao import MessageDao
from alias.server.exceptions.service import (
    InvalidToolMessageError,
    MessageNotFoundError,
)
from alias.server.models.action import FeedbackType
from alias.server.models.message import (
    BaseMessage,
    FileItem,
    Message,
    MessageType,
    UserMessage,
    RoadmapChange,
)
from alias.server.schemas.common import PaginationParams
from alias.server.services.action_service import ActionService
from alias.server.services.base_service import BaseService
from alias.server.services.file_service import FileService


class MessageService(BaseService[Message]):
    _model_cls = Message
    _dao_cls = MessageDao

    def __init__(
        self,
        session: AsyncSession,
    ):
        """Initialize message service."""
        super().__init__(session)
        self.file_service = FileService(session=session)

    async def _validate_exists(
        self,
        instance_id: uuid.UUID,
    ) -> None:
        message = await self.get(instance_id)
        if not message:
            raise MessageNotFoundError(extra_info={"message_id": instance_id})

    async def _validate_update(
        self,
        instance_id: uuid.UUID,
        obj_in: Union[Dict[str, Any], Message],
    ) -> None:
        message = await self.get(instance_id)
        if not message:
            raise MessageNotFoundError(extra_info={"message_id": instance_id})

    async def _validate_delete(self, instance_id: uuid.UUID) -> None:
        message = await self.get(instance_id)
        if not message:
            raise MessageNotFoundError(extra_info={"message_id": instance_id})

    async def create_user_message(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        task_id: uuid.UUID,
        query: str,
        files: List[uuid.UUID] = None,
        roadmap: Optional[RoadmapChange] = None,
    ) -> Message:
        message_id = uuid.uuid4()
        files = files or []
        file_items = []

        for file_id in files:
            file = await self.file_service.upload_to_sandbox(
                file_id=file_id,
                conversation_id=conversation_id,
                user_id=user_id,
            )
            if file:
                file_item = FileItem(
                    id=str(file.id),
                    filename=file.filename,
                    size=file.size,
                    url=file.storage_path,
                )
                file_items.append(file_item)

        message = UserMessage(
            content=query,
            files=file_items,
            roadmap=roadmap,
        )

        return await self.create_message(
            conversation_id=conversation_id,
            message=message,
            message_id=message_id,
            task_id=task_id,
        )

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        message: BaseMessage,
        message_id: Optional[uuid.UUID] = None,
        task_id: Optional[uuid.UUID] = None,
        parent_message_id: Optional[uuid.UUID] = None,
    ) -> Message:
        message_id = message_id or uuid.uuid4()
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            task_id=task_id,
            message=message.model_dump(),
            parent_message_id=parent_message_id,
        )
        message = await self.create(message)
        logger.info(f"Created message: {message.id}")
        return message

    async def list_messages(
        self,
        conversation_id: uuid.UUID,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[int, List[Message]]:
        filters = {"conversation_id": conversation_id}
        total = await self.count_by_fields(filters=filters)
        messages = await self.paginate(
            pagination=pagination,
            filters=filters,
        )
        return total, messages

    async def feedback_message(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        feedback: FeedbackType,
    ) -> Message:
        message = await self.get(message_id)
        if not message:
            raise MessageNotFoundError(extra_info={"message_id": message_id})

        action_service = ActionService()
        await action_service.record_feedback(
            user_id=user_id,
            conversation_id=message.conversation_id,
            message_id=message_id,
            previous=message.feedback,
            current=feedback,
        )
        message.feedback = feedback

        return await self.update(message_id, message)

    async def collect_tool_message(
        self,
        message_id: uuid.UUID,
        collect: bool,
        user_id: uuid.UUID,
    ) -> Message:
        message = await self.get(message_id)
        if not message:
            raise MessageNotFoundError(extra_info={"message_id": message_id})

        message_json = message.message
        if message_json.get("type", MessageType.USER) != MessageType.THOUGHT:
            raise InvalidToolMessageError(
                message="Message is not a tool message",
                extra_info={"message_id": message_id},
            )

        action_service = ActionService()
        await action_service.record_collect_tool(
            user_id=user_id,
            conversation_id=message.conversation_id,
            message_id=message_id,
            previous=message.collected,
            current=collect,
        )
        message.collected = collect
        return await self.update(message_id, message)

    async def delete_messages(
        self,
        conversation_id: uuid.UUID,
    ) -> None:
        await self.delete_all_by_field("conversation_id", conversation_id)
