# -*- coding: utf-8 -*-
# pylint: disable=C0301

import functools
import json
import uuid
import time
from typing import Any, List, Optional, AsyncGenerator
from loguru import logger


from alias.server.core.event import Event
from alias.server.core.event_manager import EventManager
from alias.server.db.init_db import session_scope
from alias.server.models.message import (
    BaseMessage,
    FilesMessage,
    Message,
    MessageState,
)
from alias.server.models.plan import Plan
from alias.server.models.state import State
from alias.server.schemas.event import (
    MessageCreateEvent,
    MessageFinishEvent,
    MessageUpdateEvent,
    PlanCreateEvent,
    StateCreateEvent,
)
from alias.server.schemas.session_entity import SessionEntity
from alias.server.services.file_service import FileService
from alias.server.services.plan_service import PlanService
from alias.server.services.state_service import StateService
from alias.server.services.message_service import MessageService


from alias.runtime.alias_sandbox import AliasSandbox


def log_time(func) -> Any:
    """Decorator to log method execution time."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.info(
                f"{func.__name__} took {duration:.3f} seconds",
            )

    return wrapper


class SessionService:
    def __init__(
        self,
        session_entity: SessionEntity,
        event_manager: Optional[EventManager] = None,
        sandbox: Optional[AliasSandbox] = None,
    ):
        self.session_entity = session_entity
        self.event_manager = event_manager
        self.sandbox = sandbox

    # State operations
    @log_time
    async def get_state(self) -> Optional[State]:
        async with session_scope() as session:
            state = await StateService(session=session).get_state(
                conversation_id=self.session_entity.conversation_id,
            )
            if state is None or not state.content:
                return None
            return json.loads(state.content)

    @log_time
    async def create_state(self, content: Any) -> State:
        if isinstance(content, dict):
            content = json.dumps(content)
        state = State(
            conversation_id=self.session_entity.conversation_id,
            content=content,
        )
        await self.put_event(StateCreateEvent(state=state))
        return state

    # Plan operations
    @log_time
    async def get_plan(self) -> Optional[Plan]:
        async with session_scope() as session:
            return await PlanService(session=session).get_plan(
                conversation_id=self.session_entity.conversation_id,
            )

    @log_time
    async def create_plan(self, content: Any) -> Plan:
        plan = Plan(
            conversation_id=self.session_entity.conversation_id,
            content=content,
        )
        await self.put_event(PlanCreateEvent(plan=plan))
        return plan

    # Message operations
    @log_time
    async def create_message(
        self,
        message: BaseMessage,
        message_id: Optional[uuid.UUID] = None,
    ) -> Message:
        # Handle file message
        if isinstance(message, FilesMessage):
            async with session_scope() as session:
                file_service = FileService(session=session)
                for file_item in message.files:
                    if file_item.url:
                        file = await file_service.load_sandbox_file(
                            user_id=self.session_entity.user_id,
                            conversation_id=(
                                self.session_entity.conversation_id
                            ),
                            filename=file_item.url,
                        )
                        file_item.url = file.storage_path
                        file_item.id = str(file.id)
                        file_item.size = file.size
        db_message = Message(
            id=message_id or uuid.uuid4(),
            conversation_id=self.session_entity.conversation_id,
            task_id=self.session_entity.task_id,
            message=message.model_dump(),
            parent_message_id=self.session_entity.message_id,
        )

        logger.info(f"session service create message: {db_message}")

        event = None
        if message.status == MessageState.FINISHED:
            event = MessageFinishEvent(message=db_message)
        elif not message_id:
            event = MessageCreateEvent(message=db_message)
        elif message_id:
            event = MessageUpdateEvent(message=db_message)

        if event:
            await self.put_event(event)
        return db_message

    @log_time
    async def get_messages(self) -> List[Message]:
        async with session_scope() as session:
            filters = {"conversation_id": self.session_entity.conversation_id}
            return await MessageService(session=session).paginate(
                filters=filters,
            )

    # Event operations
    async def put_event(self, event: Event) -> None:
        await self.event_manager.put(event)

    async def listen(self) -> AsyncGenerator[Event, None]:
        async for event in self.event_manager.listen():
            yield event
