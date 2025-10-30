# -*- coding: utf-8 -*-
# mypy: disable-error-code="has-type"
import json
from typing import Literal, Any, Optional, TYPE_CHECKING, Union

from agentscope.message import Msg
from agentscope import logger

from alias.agent.utils import AliasAgentStates
from alias.agent.utils.constants import DEFAULT_PLANNER_NAME

if TYPE_CHECKING:
    from alias.agent.agents import MetaPlanner
    from alias.agent.agents._alias_agent_base import (
        AliasAgentBase,
    )
else:
    AliasAgentBase = "alias.agent.agents.AliasAgentBase"
    MetaPlanner = "alias.agent.agents.MetaPlanner"


PlannerStage = Literal["post_reasoning", "post_action", "pre_reasoning"]


def _infer_planner_stage_with_msg(
    cur_msg: Msg,
) -> tuple[PlannerStage, list[str]]:
    """
    Infer the planner stage and extract tool names from a message.

    Analyzes a message to determine the current stage of the planner workflow
    and extracts any tool names if tool calls are present in the message.

    Args:
        cur_msg (Msg): The message to analyze for stage inference.

    Returns:
        tuple[PlannerStage, list[str]]: A tuple containing:
            - PlannerStage: One of "pre_reasoning", "post_reasoning", or
                "post_action"
            - list[str]: List of tool names found in tool_use or
                tool_result blocks

    Note:
        - "pre_reasoning": System role messages with string content
        - "post_reasoning": Messages with tool_use blocks or plain text content
        - "post_action": Messages with tool_result blocks
        - Tool names are extracted from both tool_use and tool_result blocks
    """
    blocks = cur_msg.content
    if isinstance(blocks, str) and cur_msg.role in ["system", "user"]:
        return "pre_reasoning", []

    cur_tool_names = [
        str(b.get("name", "no_name_tool"))
        for b in blocks
        if b["type"] in ["tool_use", "tool_result"]
    ]
    if cur_msg.has_content_blocks("tool_result"):
        return "post_action", cur_tool_names
    elif cur_msg.has_content_blocks("tool_use"):
        return "post_reasoning", cur_tool_names
    else:
        return "post_reasoning", cur_tool_names


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


async def _update_and_save_plan_with_session(
    self: MetaPlanner,
) -> None:
    content = self.planner_notebook.model_dump(
        exclude="full_tool_list",
    )
    await self.session_service.create_plan(
        content=content,
    )


async def planner_load_states_pre_reply_hook(
    self: MetaPlanner,
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
    for name, (_, worker) in self.worker_manager.worker_pool.items():
        if name in global_state.agent_states:
            worker.load_state_dict(global_state.agent_states[name])


async def update_user_input_pre_reply_hook(
    self: MetaPlanner,
    kwargs: dict[str, Any],
) -> None:
    """Hook for loading user input to planner notebook"""
    msg = kwargs.get("msg", None)
    if isinstance(msg, Msg):
        msg = [msg]
    elif self.session_service is not None:
        messages = await self.session_service.get_messages()
        logger.info(f"Received {len(messages)} messages")
        if messages is None:
            return
        latest_user_msg = None
        msg = []
        for cur_msg in reversed(messages):
            msg_body = cur_msg.message
            if msg_body["role"] == "user" and latest_user_msg is None:
                latest_user_msg = msg_body["content"]
            input_content = msg_body["content"]
            if len(msg_body.get("filenames", [])) > 0:
                input_content += "User Provided Attached Files:\n"
                for filename in msg_body.get("filenames", []):
                    if not filename.startswith("/workspace"):
                        filename = "/workspace/" + filename
                    input_content += f"\t{filename}\n"
            if msg_body["role"] == "user":
                msg.append(input_content)
    if isinstance(msg, list):
        self.planner_notebook.user_input = [str(m) for m in msg]
        for m in msg:
            await self.memory.add(
                Msg(
                    "user",
                    m,
                    "user",
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
    self: Union[AliasAgentBase, MetaPlanner],
    action_input: dict[str, Any],  # pylint: disable=W0613
    tool_output: Optional[Msg],  # pylint: disable=W0613
) -> None:
    """Hook func for save state after action step"""
    await _update_and_save_state_with_session(self)
    if self.name == DEFAULT_PLANNER_NAME:
        await _update_and_save_plan_with_session(self)


async def planner_compose_reasoning_msg_pre_reasoning_hook(
    self: "MetaPlanner",  # pylint: disable=W0613
    *args: Any,
    **kwargs: Any,
) -> None:
    """Hook func for composing msg for reasoning step"""
    reasoning_info = (
        "## All User Input\n{all_user_input}\n\n"
        "## Session Context\n"
        "```json\n{notebook_string}\n```\n\n"
    ).format_map(
        {
            "notebook_string": self.planner_notebook.model_dump_json(
                exclude={"user_input", "full_tool_list"},
                indent=2,
            ),
            "all_user_input": self.planner_notebook.user_input,
        },
    )
    if self.work_pattern == "simplest":
        tool_info = json.dumps(
            self.planner_notebook.full_tool_list,
            indent=2,
            ensure_ascii=False,
        )
        reasoning_info += (
            "## Additional Tool information\n"
            "The following tools can be enable in your toolkit either if you"
            "enter easy task mode (by calling `enter_easy_task_mode`) or "
            "create worker in planning-execution mode (after calling "
            "`enter_planning_execution_mode`).\n"
            "NOTICE: THE FOLLOWING TOOL IS ONLY FOR REFERENCE! "
            "DO NOT USE THEM BEFORE CALLING `enter_easy_task_mode`!\n"
            f"```json\n{tool_info}\n```\n"
        )
    reasoning_msg = Msg(
        "user",
        content=reasoning_info,
        role="user",
    )
    await self.memory.add(reasoning_msg)


async def planner_remove_reasoning_msg_post_reasoning_hook(
    self: "MetaPlanner",  # pylint: disable=W0613
    *args: Any,
    **kwargs: Any,
) -> None:
    """Hook func for removing msg for reasoning step"""
    num_msgs = await self.memory.size()
    if num_msgs > 1:
        # remove the msg added by planner_compose_reasoning_pre_reasoning_hook
        await self.memory.delete(num_msgs - 2)


async def generate_response_post_action_hook(
    self: AliasAgentBase,
    action_input: dict[str, Any],  # pylint: disable=W0613
    tool_output: Optional[Msg],  # pylint: disable=W0613
) -> None:
    """Hook func for printing clarification"""
    if not (hasattr(self, "session_service") and self.session_service):
        return

    if isinstance(tool_output, Msg):
        if tool_output.metadata and tool_output.metadata.get(
            "require_clarification",
            False,
        ):
            clarification_dict = {
                "clarification_question": tool_output.metadata.get(
                    "clarification_question",
                    "",
                ),
                "clarification_options": tool_output.metadata.get(
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
                metadata=tool_output.metadata,
            )
            await self.print(msg, last=True)
