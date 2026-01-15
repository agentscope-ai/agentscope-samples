# -*- coding: utf-8 -*-
# mypy: disable-error-code="has-type"
import json
from typing import Any, TYPE_CHECKING, Optional
from loguru import logger

from agentscope.message import Msg
from alias.agent.agents.common_agent_utils._common_agent_hooks import (
    _update_and_save_state_with_session,
)
from alias.agent.mock.mock_message_models import PlanToPrint, SubTaskToPrint

if TYPE_CHECKING:
    from alias.agent.agents._meta_planner import MetaPlanner
else:
    MetaPlanner = "alias.agent.agents.MetaPlanner"


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
            f"## Current time\n{self.planner_notebook.time}\n\n"
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
    await self._reasoning_hint_msgs.add(  # pylint: disable=protected-access
        reasoning_msg,
    )


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
                latest_user_msg = msg_body.get("content", "")
                roadmap = msg_body.get("roadmap", None)
                if roadmap is not None:
                    latest_user_msg += (
                        "**User requests changing the plan:**\n"
                        f"{json.dumps(roadmap, indent=2, ensure_ascii=False)}"
                    )

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


async def _planner_save_plan_with_session(
    self: MetaPlanner,
) -> None:
    list_of_tasks = []
    for subtask in self.planner_notebook.roadmap.decomposed_tasks:
        list_of_tasks.append(
            SubTaskToPrint(
                description=subtask.subtask_specification.description,
                state=subtask.state,
            ),
        )
    await self.session_service.create_plan(
        content=PlanToPrint(subtasks=list_of_tasks).model_dump(),
    )


async def planner_save_post_action_state(
    self: MetaPlanner,
    action_input: dict[str, Any],  # pylint: disable=W0613
    tool_output: Optional[dict],  # pylint: disable=W0613
) -> None:
    """Hook func for save state after action step"""
    await _update_and_save_state_with_session(self)
    tool_call = action_input.get("tool_call", None)
    if isinstance(tool_call, dict) and "roadmap" in tool_call.get("name", ""):
        await _planner_save_plan_with_session(self)
