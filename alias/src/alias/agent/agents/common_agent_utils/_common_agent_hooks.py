# -*- coding: utf-8 -*-
# mypy: disable-error-code="has-type"
# pylint: disable=R1702
import json
from typing import Any, Optional, TYPE_CHECKING
from loguru import logger

from agentscope.message import Msg, TextBlock

from alias.agent.utils import send_as_msg
from .agent_save_state import AliasAgentStates


if TYPE_CHECKING:
    from alias.agent.agents._alias_agent_base import AliasAgentBase
else:
    AliasAgentBase = "alias.agent.agents.AliasAgentBase"


async def _update_and_save_state_with_session(
    self: AliasAgentBase,
) -> None:
    global_state = await self.session_service.get_state()
    if global_state is None:
        global_state = AliasAgentStates()
    else:
        global_state = AliasAgentStates(**global_state)
    # update global state
    global_state.agent_states[self.name] = self.state_dict()
    await self.session_service.create_state(
        content=global_state.model_dump(),
    )


async def agent_load_states_pre_reply_hook(
    self: AliasAgentBase,
    kwargs: dict[str, Any],  # pylint: disable=W0613
) -> None:
    global_state = await self.session_service.get_state()
    if global_state is None or len(global_state) == 0:
        return

    global_state = AliasAgentStates(**global_state)
    if self.name not in global_state.agent_states:
        return

    self.load_state_dict(global_state.agent_states[self.name])
    # load worker states
    if hasattr(self, "worker_manager"):
        for name, (_, worker) in self.worker_manager.worker_pool.items():
            if name in global_state.agent_states:
                worker.load_state_dict(global_state.agent_states[name])


async def get_user_input_to_mem_pre_reply_hook(
    self: AliasAgentBase,
    kwargs: dict[str, Any],
) -> None:
    """Hook for loading user input to planner notebook"""
    msg = kwargs.get("msg", None)
    if isinstance(msg, Msg):
        return
    elif self.session_service is not None:
        messages = await self.session_service.get_messages()
        logger.info(f"Received {len(messages)} messages")
        if messages is None:
            return
        latest_user_msg = None
        for cur_msg in reversed(messages):
            msg_body = cur_msg.message
            if msg_body["role"] == "user" and latest_user_msg is None:
                latest_user_msg = msg_body["content"]
                roadmap = msg_body.get("roadmap", None)
                if roadmap is not None:
                    latest_user_msg += (
                        "**User requests changing the plan:**\n"
                        f"{json.dumps(roadmap, indent=2, ensure_ascii=False)}"
                    )

                if len(msg_body.get("filenames", [])) > 0:
                    latest_user_msg += "User Provided Attached Files:\n"
                    for filename in msg_body.get("filenames", []):
                        if not filename.startswith("/workspace"):
                            filename = "/workspace/" + filename
                        latest_user_msg += f"\t{filename}\n"
                break

        await self.memory.add(
            Msg(
                "user",
                content=[TextBlock(type="text", text=latest_user_msg)],
                role="user",
            ),
        )


async def save_post_reasoning_state(
    self: AliasAgentBase,
    reasoning_input: dict[str, Any],  # pylint: disable=W0613
    reasoning_output: Msg,  # pylint: disable=W0613
) -> None:
    """Hook func for save state after reasoning step"""
    await _update_and_save_state_with_session(self)


async def save_post_action_state(
    self: AliasAgentBase,
    action_input: dict[str, Any],  # pylint: disable=W0613
    tool_output: Optional[dict],  # pylint: disable=W0613
) -> None:
    """Hook func for save state after action step"""
    await _update_and_save_state_with_session(self)


async def generate_response_post_action_hook(
    self: AliasAgentBase,
    action_input: dict[str, Any],  # pylint: disable=W0613
    tool_output: Optional[dict],  # pylint: disable=W0613
) -> None:
    """Hook func for printing clarification"""
    if not (hasattr(self, "session_service") and self.session_service):
        return

    if isinstance(tool_output, dict):
        if tool_output.get(
            "require_clarification",
            False,
        ):
            clarification_dict = {
                "clarification_question": tool_output.get(
                    "clarification_question",
                    "",
                ),
                "clarification_options": tool_output.get(
                    "clarification_options",
                    "",
                ),
            }
            msg = Msg(
                name=self.name,
                content=json.dumps(
                    clarification_dict,
                    ensure_ascii=False,
                    indent=4,
                ),
                role="assistant",
                metadata=tool_output,
            )
            await self.print(msg, last=True)


async def alias_post_print_hook(
    self: AliasAgentBase,
    print_input: dict[str, Any],  # pylint: disable=W0613
    print_output: dict[str, Any],  # pylint: disable=W0613
) -> None:
    if not (hasattr(self, "session_service") and self.session_service):
        return

    msg: Msg = print_input.get(
        "msg",
        Msg(name=self.name, content="", role="assistant"),
    )
    last: bool = print_input.get("last", True)

    # get the db_msg_id
    db_msg_id = self.message_sending_mapping.get(msg.id, None)
    db_msg_id = await send_as_msg(
        self.session_service,
        msg,
        self.name,
        db_msg_id=db_msg_id,
        last=last,
    )
    if last and msg.id in self.message_sending_mapping:
        self.message_sending_mapping.pop(msg.id)
    elif not last:
        self.message_sending_mapping[msg.id] = db_msg_id
