# -*- coding: utf-8 -*-
import traceback
import uuid
from typing import Optional, Any

from agentscope.memory import LongTermMemoryBase
from agentscope.message import Msg, TextBlock
from agentscope.tool import ToolResponse
from loguru import logger

from alias.server.clients.memory_client import MemoryClient
from alias.server.schemas.action import ChatAction, ChatType, TaskStopAction
from alias.server.services.session_service import SessionService

from alias.agent.memory.longterm_memory_utils import (
    convert_mock_messages_to_dict,
    filter_latest_user_message,
)


def _get_query_from_msgs(msgs: Msg | list[Msg] | None) -> str:
    if isinstance(msgs, Msg):
        return msgs.content
    elif isinstance(msgs, list):
        return "\n".join([_.content for _ in msgs])
    else:
        return ""


class AliasLongTermMemory(LongTermMemoryBase):
    def __init__(self, session_service: SessionService):
        super().__init__()
        self.session_service = session_service
        self.memory_client = MemoryClient()

    async def record(
        self,
        msgs: list[Msg],  # pylint: disable=unused-argument
    ):
        """Record the given messages to the memory.

        This function is only used when the frontend service is not running.
        When the frontend service is running, the action of recording session
        messages to tool memory is triggered when the user starts a new
        conversation, and the backend service will call the record_action of
        the memory client to record the session messages to tool memory.
        This function will record user message and create TASK_STOP action
        and CHAT action.

        Args:
            msgs (`list[Msg]`): The messages to record to the memory.

        Returns:
            `None`: If the frontend service is running, return None.
            If the frontend service is not running, record TASK_STOP action
            and return None.
        """
        # If frontend service is running, return None
        event_manager = getattr(self.session_service, "event_manager", None)
        if event_manager is not None:
            logger.warning("Frontend service is running, returning None")
            return None

        # If frontend service is not running, record TASK_STOP action
        try:
            # Get task_id safely, as it might not exist in mock SessionEntity
            task_id = getattr(
                self.session_service.session_entity,
                "task_id",
                "",
            )
            if task_id == "":
                task_id = uuid.uuid4()
                logger.warning(
                    f"task_id not found in session_entity, generating "
                    f"random task_id: {task_id}",
                )
            messages = await self.session_service.get_messages()
            # Convert MockMessage objects to Message objects, then to dicts
            # for serialization
            serialized_messages = convert_mock_messages_to_dict(
                messages,
                self.session_service,
            )

            action = TaskStopAction.create(
                user_id=self.session_service.session_entity.user_id,
                conversation_id=(
                    self.session_service.session_entity.conversation_id
                ),
                task_id=task_id,
                data={
                    "session_content": serialized_messages,
                },
            )
            await self.memory_client.record_action(action)
            logger.info("Recorded TASK_STOP action successfully")

            (
                last_user_query,
                action_message_id,
                has_earlier_user_msg,
            ) = filter_latest_user_message(serialized_messages)
            if last_user_query:
                record_chat_action = ChatAction.create(
                    user_id=self.session_service.session_entity.user_id,
                    conversation_id=(
                        self.session_service.session_entity.conversation_id
                    ),
                    message_id=action_message_id,
                    chat_type=ChatType.TASK if has_earlier_user_msg else None,
                    history_length=2 if has_earlier_user_msg else 0,
                    session_content=serialized_messages,
                    query=last_user_query,
                )
                await self.memory_client.record_action(record_chat_action)
                logger.info("Recorded CHAT action successfully")
            return
        except Exception as e:
            # Log error but don't raise, as this is a background operation
            error_traceback = traceback.format_exc()
            logger.error(
                f"Failed to record TASK_STOP action: {str(e)}\n"
                f"Traceback:\n{error_traceback}",
            )
            return

    async def retrieve(self, query: Msg | list[Msg] | None) -> Optional[str]:
        """Retrieve the memory based on the given query.

        Args:
            query (`Msg` | `list[Msg]` | `None`): The query to search for in
                the memory. If the query is a list of messages, join the
                content of the messages into a single string. If the query is
                None or empty, return None.

        Returns:
            Optional[str]: The retrieved memory as string text. If the query
                is None or empty, return None.
        """
        query_str = _get_query_from_msgs(query)
        if not query_str:
            logger.warning("No query provided")
            return None
        try:
            uid = str(self.session_service.session_entity.user_id)
            result = await self.memory_client.retrieve_user_profiling(
                uid=uid,
                query=query_str,
            )
            logger.info(
                f"Retrieved user profiling: {result} "
                f"based on query: {query_str}",
            )
            return result
        except Exception as e:
            logger.error(f"Failed to retrieve user profiling: {str(e)}")
            return None

    async def tool_memory_retrieve(
        self,
        query: str,
    ) -> ToolResponse:
        """Retrieve the tool-use experience of the tools in the query.

        The query should be the concatenation of tool names separated by
        commas. For example, "tool1,tool2,tool3".

        Args:
            query (`str`): It should be the concatenation of tool names
                separated by commas. For example, "tool1,tool2,tool3".

        Returns:
            `ToolResponse`: A ToolResponse containing the retrieved tool
                memory as string text. If the query is empty, return a
                ToolResponse with a text block containing the message
                "No query provided".
        """
        if not query:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="No query provided",
                    ),
                ],
            )
        try:
            uid = str(self.session_service.session_entity.user_id)
            tool_memory = await self.memory_client.retrieve_tool_memory(
                uid=uid,
                query=query,
            )
            if not tool_memory:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="No tool memory found",
                        ),
                    ],
                )
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=tool_memory,
                    ),
                ],
            )
        except Exception as e:
            logger.error(f"Failed to retrieve tool memory: {str(e)}")
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error retrieving tool memory: {str(e)}",
                    ),
                ],
            )

    async def record_to_memory(  # pylint: disable=unused-argument
        self,
        thinking: str,
        content: list[str],
        **kwargs: Any,  # noqa: ARG002
    ) -> ToolResponse:
        """Use this function to record important information that you may
        need later. The target content should be specific and concise, e.g.
        who, when, where, do what, why, how, etc.

        Args:
            thinking (`str`):
                Your thinking and reasoning about what to record.
            content (`list[str]`):
                The content to remember, which is a list of strings.
        """
        try:
            logger.info(f"Recording to memory: {thinking} {content}")
            if not thinking:
                thinking = ""
            if not content:
                content = []

            uid = str(self.session_service.session_entity.user_id)
            session_id = str(
                self.session_service.session_entity.conversation_id,
            )

            # Combine thinking and content
            combined_content_str = ""
            if thinking:
                combined_content_str = thinking
            if content:
                content_str = "\n".join(content)
                if combined_content_str:
                    combined_content_str = (
                        f"{combined_content_str}\n{content_str}"
                    )
                else:
                    combined_content_str = content_str

            if not combined_content_str.strip():
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="No content to record.",
                        ),
                    ],
                )

            # Record as user message
            content_dicts = [
                {
                    "role": "user",
                    "content": combined_content_str,
                },
            ]
            results = await self.memory_client.add_to_longterm_memory(
                uid=uid,
                content=content_dicts,
                session_id=session_id,
            )

            result_text = results if results else "submitted for processing"
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            f"Successfully recorded content to memory: "
                            f"{result_text}"
                        ),
                    ),
                ],
            )

        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Error recording memory: {str(e)}",
                    ),
                ],
            )

    async def retrieve_from_memory(
        self,
        keywords: list[str],
    ) -> ToolResponse:
        """Retrieve the memory based on the given keywords.

        Args:
            keywords (`list[str]`): The keywords to search for in the memory.
                It should be specific and concise, e.g. the person's name,
                the date, the location, etc. During retrieval, each keyword
                is issued as an independent query against the memory store.

        Returns:
            `ToolResponse`: A ToolResponse containing the retrieved memories
                as string text.
        """
        results_all = ""
        uid = str(self.session_service.session_entity.user_id)
        for keyword in keywords:
            results = await self.memory_client.retrieve_user_profiling(
                uid=uid,
                query=keyword,
            )
            if results:
                results_all += results + "\n"
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=results_all,
                ),
            ],
        )
