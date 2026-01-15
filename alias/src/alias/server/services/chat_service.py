# -*- coding: utf-8 -*-
# pylint: disable=C0301 W0622
# mypy: disable-error-code="arg-type"

import asyncio
import traceback
import uuid
from typing import Optional

from loguru import logger

from alias.server.core.config import settings
from alias.server.core.event import (
    ErrorEvent,
    HeartBeatEvent,
    StopEvent,
)
from alias.server.core.event_manager import EventManager
from alias.server.core.task_manager import task_manager
from alias.server.exceptions.base import BaseError
from alias.server.schemas.chat import ChatRequest
from alias.server.schemas.event import (
    MessageCreateEvent,
    MessageUpdateEvent,
    MessageFinishEvent,
    PlanCreateEvent,
    StateCreateEvent,
)

from alias.server.schemas.message import MessageInfo
from alias.server.schemas.session_entity import SessionEntity
from alias.server.services.action_service import ActionService
from alias.server.services.conversation_service import ConversationService
from alias.server.services.message_service import MessageService
from alias.server.services.session_service import SessionService
from alias.server.services.plan_service import PlanService
from alias.server.services.state_service import StateService
from alias.server.db.init_db import session_scope
from alias.agent.run import arun_agents
from alias.runtime.alias_sandbox import AliasSandbox


# pylint: disable=R0912
async def run_agent_worker(
    session_service: SessionService,
) -> None:
    """Run agent worker.

    Args:
        session_service: Session service instance.
    """
    session_entity = session_service.session_entity
    sandbox = session_service.sandbox
    agent_task = None

    try:
        agent_task = asyncio.create_task(
            arun_agents(
                session_service=session_service,
                sandbox=sandbox,
            ),
        )
        await agent_task

        if session_service:
            await session_service.put_event(StopEvent())

    except asyncio.CancelledError:
        logger.info(f"Task {session_entity.task_id} cancelled")
        if session_service:
            await session_service.put_event(
                StopEvent(),
            )
        if agent_task and not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
        raise

    except Exception as e:
        logger.error(
            f"Error in task {session_entity.task_id}: {e}\n"
            f"{traceback.format_exc()}",
        )
        if session_service:
            if isinstance(e, BaseError):
                await session_service.put_event(
                    ErrorEvent(message=e.message, code=e.code),
                )
            else:
                await session_service.put_event(
                    ErrorEvent(
                        message=str(e),
                        code=500,
                    ),
                )

    finally:
        try:
            if agent_task and not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except (asyncio.CancelledError, Exception):
                    pass

            logger.info(
                f"Run agent worker finished, task_id: "
                f"{session_entity.task_id}",
            )

        except Exception as e:
            logger.error(
                f"Error during cleanup for task {session_entity.task_id}: {e}",
            )


class ChatService:
    async def chat(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        chat_request: ChatRequest,
        task_id: Optional[uuid.UUID] = None,
    ):
        query = chat_request.query
        files = chat_request.files
        chat_type = chat_request.chat_type
        chat_mode = chat_request.chat_mode
        language_type = chat_request.language_type
        roadmap = chat_request.roadmap
        use_long_term_memory_service = (
            chat_request.use_long_term_memory_service or False
        )

        async with session_scope() as session:
            message_service = MessageService(session=session)
            filters = {"conversation_id": conversation_id}
            history_length = await message_service.count_by_fields(
                filters=filters,
            )
            task_id = task_id or uuid.uuid4()
            conversation = await ConversationService(
                session=session,
            ).get_conversation(conversation_id)

            sandbox = AliasSandbox(
                sandbox_id=conversation.sandbox_id,
                base_url=settings.SANDBOX_URL,
                bearer_token=settings.SANDBOX_BEARER_TOKEN,
            )

            message = await message_service.create_user_message(
                user_id=user_id,
                conversation_id=conversation_id,
                task_id=task_id,
                query=query,
                files=files,
                roadmap=roadmap,
            )

        action_service = ActionService()
        await action_service.record_chat(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message.id,
            query=query,
            chat_type=chat_type,
            history_length=history_length,
        )

        session_entity = SessionEntity(
            task_id=task_id,
            conversation_id=conversation_id,
            message_id=message.id,
            user_id=user_id,
            language_type=language_type,
            chat_mode=chat_mode,
            chat_type=chat_type,
            query=query,
            roadmap=roadmap,
            use_long_term_memory_service=use_long_term_memory_service,
        )

        event_manager = EventManager(
            task_id=task_id,
            user_id=user_id,
        )

        session_service = SessionService(
            session_entity=session_entity,
            event_manager=event_manager,
            sandbox=sandbox,
        )
        task = asyncio.create_task(
            run_agent_worker(
                session_service=session_service,
            ),
        )

        task_manager.register_task(
            task_id=task_id,
            task=task,
            user_id=user_id,
        )

        return self.handle_chat_response(session_service=session_service)

    # pylint: disable=R0915, R0913
    async def handle_chat_response(
        self,
        session_service: SessionService,
    ):
        session_entity = session_service.session_entity

        async def convert_outputs(
            messages,
            roadmap,
        ):
            outputs = dict({**session_entity.ids(), "data": {}})
            outputs["data"]["messages"] = messages
            outputs["data"]["roadmap"] = roadmap

            return outputs

        try:
            async with session_scope() as session:
                message_service = MessageService(session=session)
                plan_service = PlanService(session=session)
                state_service = StateService(session=session)
                create_message_time = None

                try:
                    async for event in session_service.listen():
                        messages = []
                        roadmap = {}
                        if isinstance(  # pylint: disable=R1720
                            event,
                            ErrorEvent,
                        ):
                            raise BaseError(
                                code=event.code,
                                message=event.message,
                            )
                        elif isinstance(event, StopEvent | None):
                            action_service = ActionService()
                            await action_service.record_task_stop(
                                user_id=session_entity.user_id,
                                conversation_id=session_entity.conversation_id,
                                task_id=session_entity.task_id,
                            )
                            break
                        elif isinstance(event, HeartBeatEvent):
                            pass
                        elif isinstance(event, MessageCreateEvent):
                            message = event.message
                            create_message_time = message.create_time
                            messages = [
                                MessageInfo.model_validate(
                                    message,
                                ).model_dump(),
                            ]
                        elif isinstance(event, MessageUpdateEvent):
                            message = event.message
                            if create_message_time:
                                message.create_time = create_message_time
                            messages = [
                                MessageInfo.model_validate(
                                    message,
                                ).model_dump(),
                            ]
                        elif isinstance(event, MessageFinishEvent):
                            message = event.message
                            if create_message_time:
                                message.create_time = create_message_time
                            messages = [
                                MessageInfo.model_validate(
                                    message,
                                ).model_dump(),
                            ]
                            await message_service.create(message)
                        elif isinstance(event, PlanCreateEvent):
                            plan = event.plan
                            await plan_service.create_plan(
                                conversation_id=plan.conversation_id,
                                content=plan.content,
                            )
                            roadmap = plan.roadmap.model_dump()
                        elif isinstance(event, StateCreateEvent):
                            state = event.state
                            await state_service.create_state(
                                conversation_id=state.conversation_id,
                                content=state.content,
                            )
                        output = await convert_outputs(
                            messages=messages,
                            roadmap=roadmap,
                        )
                        yield output
                        logger.warning(
                            f"conversation service yield outputs: {output}",
                        )
                except BaseError as e:
                    logger.error(f"{e}: {traceback.format_exc()}")
                    raise e
        except Exception as e:
            logger.error(f"{e}: {traceback.format_exc()}")
            raise BaseError(code=500, message=str(e)) from e
        logger.info("Handle_chat_response response finished")

    async def stop_chat(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> None:
        """Stop conversation."""
        logger.warning(
            f"Chat stopped by user: user_id={user_id}, task_id={task_id}",
        )
        await task_manager.stop_task(task_id=task_id)
