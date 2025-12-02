# -*- coding: utf-8 -*-
# pylint: disable=W0212,R0911
import json
import os
import uuid
from typing import Union, Optional

from agentscope.message import Msg, ToolUseBlock, ToolResultBlock

from alias.server.models.message import (
    ClarificationMessage,
    MessageState,
    ResponseMessage,
    MessageType,
    BaseMessage,
    ThoughtMessage,
    SubThoughtMessage,
    SubResponseMessage,
    FilesMessage,
    ToolCallMessage,
    SystemMessage,
    ToolUseMessage,
    ToolResultMessage,
)
from alias.agent.utils.constants import DEFAULT_PLANNER_NAME

if os.getenv("TEST_MODE") not in ["local", "runtime-test"]:
    from alias.server.services.session_service import (
        SessionService,
    )
else:
    from alias.agent.mock import MockSessionService as SessionService


_MESSAGE_TYPE_MAPPING = {
    MessageType.RESPONSE: ResponseMessage,
    MessageType.SUB_RESPONSE: SubResponseMessage,
    MessageType.THOUGHT: ThoughtMessage,
    MessageType.SUB_THOUGHT: SubThoughtMessage,
    MessageType.TOOL_CALL: ToolCallMessage,
    MessageType.CLARIFICATION: ClarificationMessage,
    MessageType.FILES: FilesMessage,
    MessageType.SYSTEM: SystemMessage,
    MessageType.TOOL_USE: ToolUseMessage,
    MessageType.TOOL_RESULT: ToolResultMessage,
}


def _create_assistant_message(
    msg_type: MessageType,
    content_to_send: Union[str, Msg],
    last: bool,
    name: Optional[str] = None,
) -> BaseMessage:
    """Create message with appropriate type and content"""
    assistant_msg = _MESSAGE_TYPE_MAPPING[msg_type]()
    assistant_msg.status = MessageState.RUNNING
    if msg_type == MessageType.CLARIFICATION:
        assistant_msg.content = content_to_send.metadata.get(
            "clarification_question",
            "",
        )
        assistant_msg.options = content_to_send.metadata.get(
            "clarification_options",
            [],
        )
    elif msg_type == MessageType.TOOL_USE:
        tool_use_blocks: list[
            ToolUseBlock
        ] = content_to_send.get_content_blocks(
            "tool_use",
        )
        assert len(tool_use_blocks) > 0
        tool_use_block = tool_use_blocks[0]
        assistant_msg.tool_call_id = tool_use_block.get("id")
        assistant_msg.tool_name = tool_use_block.get("name")
        assistant_msg.arguments = tool_use_block.get("input", {})
        assistant_msg.content = json.dumps(tool_use_blocks)

    elif msg_type == MessageType.TOOL_RESULT:
        tool_result_blocks: list[
            ToolResultBlock
        ] = content_to_send.get_content_blocks(
            "tool_result",
        )
        assert len(tool_result_blocks) > 0
        tool_result_block = tool_result_blocks[0]
        assistant_msg.tool_call_id = tool_result_block.get("id")
        assistant_msg.tool_name = tool_result_block.get("name")
        assistant_msg.arguments = {}
        assistant_msg.content = json.dumps(tool_result_blocks)
    else:
        if isinstance(content_to_send, Msg):
            content = content_to_send.get_text_content()
        elif isinstance(content_to_send, str):
            content = content_to_send
        else:
            raise NotImplementedError(
                f"Not support type {type(content_to_send)} as content_to_send",
            )
        assistant_msg.content = content

    if isinstance(content_to_send, Msg):
        assistant_msg.name = content_to_send.name
    else:
        assistant_msg.name = name if name is not None else "system"

    if last:
        assistant_msg.status = MessageState.FINISHED

    return assistant_msg


def _determine_message_type(content_to_send: Union[str, Msg]) -> MessageType:
    """Determine the type of message to send"""
    if isinstance(content_to_send, str):
        return MessageType.RESPONSE
    if (
        isinstance(content_to_send, Msg)
        and content_to_send.metadata
        and content_to_send.metadata.get("require_clarification", False)
    ):
        return MessageType.CLARIFICATION
    elif isinstance(
        content_to_send,
        Msg,
    ) and content_to_send.has_content_blocks("tool_result"):
        return MessageType.TOOL_RESULT
    elif isinstance(
        content_to_send,
        Msg,
    ) and content_to_send.has_content_blocks("tool_use"):
        if content_to_send.name == DEFAULT_PLANNER_NAME:
            return MessageType.TOOL_USE
        else:
            return MessageType.TOOL_USE
    elif isinstance(
        content_to_send,
        Msg,
    ) and content_to_send.has_content_blocks("text"):
        if content_to_send.name == DEFAULT_PLANNER_NAME:
            return MessageType.RESPONSE
        else:
            return MessageType.SUB_RESPONSE

    else:
        raise ValueError(f"Unsupported block type {content_to_send.to_dict()}")


async def send_as_msg(
    session: SessionService,
    content_to_send: Union[
        str,
        Msg,
        None,
    ],
    name: Optional[str] = None,
    db_msg_id: Optional[uuid.UUID] = None,
    last: bool = True,
) -> Optional[uuid.UUID]:
    if content_to_send is None or (
        isinstance(content_to_send, Msg) and len(content_to_send.content) == 0
    ):
        return None
    msg_type = _determine_message_type(content_to_send)
    assistant_msg = _create_assistant_message(
        msg_type,
        content_to_send,
        last,
        name,
    )
    # create a new message
    if db_msg_id is None:
        # if no db_msg_id is provided, create a new message
        sent_msg = await session.create_message(assistant_msg)
        db_msg_id = sent_msg.id
    else:
        await session.create_message(assistant_msg, db_msg_id)

    return db_msg_id
