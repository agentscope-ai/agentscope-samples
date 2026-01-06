# -*- coding: utf-8 -*-
"""
Meta Planner agent class that can handle complicated tasks with
planning-execution pattern.
"""
# pylint: disable=W0613
import json
import os
import traceback
import uuid
from functools import partial
from pathlib import Path
from typing import Any, Callable, Literal, Optional
from loguru import logger

from pydantic import BaseModel, Field

from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase, LongTermMemoryBase
from agentscope.message import Msg, TextBlock, ToolResultBlock, ToolUseBlock
from agentscope.model import ChatModelBase
from agentscope.tool import ToolResponse

from alias.agent.agents import AliasAgentBase
from alias.agent.tools import AliasToolkit, share_tools
from alias.agent.tools.add_qa_tools import add_qa_tools
from .meta_planner_utils import (  # pylint: disable=C0411
    PlannerNoteBook,
    RoadmapManager,
    WorkerManager,
)
from alias.agent.agents.ds_agent_utils import set_run_ipython_cell
from .common_agent_utils import (
    save_post_reasoning_state,
    generate_response_post_action_hook,
    agent_load_states_pre_reply_hook,
)
from .meta_planner_utils import (
    planner_compose_reasoning_msg_pre_reasoning_hook,
    update_user_input_pre_reply_hook,
    planner_save_post_action_state,
)
from ..utils.constants import (
    PLANNER_MAX_ITER,
    DEFAULT_PLANNER_NAME,
    DEFAULT_DEEP_RESEARCH_AGENT_NAME,
    DEFAULT_DS_AGENT_NAME,
)


class MetaPlannerResponseWithClarification(BaseModel):
    require_clarification: bool = Field(
        ...,
        description=(
            "Check if the provide task description is unclear, too general or "
            "lack necessary information."
        ),
    )
    clarification_analysis: str = Field(
        default="",
        description=(
            "Identify the missing information "
            "so that if the user provides clarification or more details, "
            "you can have clearer goal and can better handle the task."
        ),
    )
    clarification_question: str = Field(
        default="",
        description=(
            "If the provide task description is unclear, too general or "
            "lack necessary information, generate the `clarification` field. "
            "Otherwise, leave it empty."
        ),
    )
    clarification_options: list[str] = Field(
        default=[],
        description=(
            "Provide two to three possible candidate answers to the "
            "clarification_question as hints for the user."
        ),
    )
    task_conclusion: str = Field(
        ...,
        description=(
            "If the task has been done, generate a conclusion."
            "The conclusion should contain"
            "1) what you have done,"
            "2) whether the task have been complete completely or "
            "just partially,"
            "3) what are the key deliverables (files/webpages/images, etc) "
            "you have generated."
        ),
    )


MetaPlannerResponseWithClarificationPrompt = (
    "The `{func_name}` should be called when either you want to request "
    "additional information from user to clarify the task, or you believe "
    "the task has been done and you want to give a final description. "
    "The `response` field needs to be a string that briefly summarize your "
    "thought in ONE sentence."
)


class MetaPlannerResponseNoClarification(BaseModel):
    task_conclusion: str = Field(
        ...,
        description=(
            "If the task has been done, generate a conclusion."
            "The conclusion should contain"
            "1) what you have done,"
            "2) whether the task have been complete completely or "
            "just partially,"
            "3) what are the key deliverables (files/webpages/images, etc) "
            "you have generated."
        ),
    )


MetaPlannerResponseNoClarificationPrompt = (
    "The `{func_name}` should be called when you believe "
    "the task has been done and you want to give a final description. "
    "The `task_conclusion` field needs to be a string that "
    "briefly covers all required key points."
)


class MetaPlanner(AliasAgentBase):
    """
    A meta-planning agent that extends ReActAgent with enhanced planning
    capabilities. The MetaPlanner is designed to handle complex multistep
    planning tasks by leveraging a combination of reasoning and action
    capabilities. The subtasks will be solved by dynamically create ReAct
    worker agent and provide it with necessary tools.
    """

    def __init__(
        self,
        model: ChatModelBase,
        worker_full_toolkit: AliasToolkit,
        formatter: FormatterBase,
        memory: MemoryBase,
        toolkit: AliasToolkit,
        browser_toolkit: AliasToolkit,
        agent_working_dir: str,
        sys_prompt: Optional[str] = None,
        max_iters: int = 10,
        state_saving_dir: Optional[str] = None,
        planner_mode: Literal["disable", "dynamic", "enforced"] = "dynamic",
        session_service: Any = None,
        enable_clarification: bool = True,
        long_term_memory: Optional[LongTermMemoryBase] = None,
        long_term_memory_mode: Literal[
            "agent_control",
            "static_control",
            "both",
        ] = "both",
    ) -> None:
        """
        Initialize the MetaPlanner with the given parameters.

        Args:
            model (ChatModelBase):
                The primary chat model used for reasoning and response
                generation.
            worker_full_toolkit (AliasToolkit):
                Complete set of tools available to the worker agent.
            formatter (FormatterBase):
                Formatter for formatting messages to the model API provider's
                format.
            memory (MemoryBase):
                Memory system for storing conversation history and context.
            toolkit (AliasToolkit):
                Toolkit for managing tools available to the agent.
            agent_working_dir (str):
                Directory for agent's file operations.
            sys_prompt (str, optional):
                Meta planner's system prompt
            max_iters (int, optional):
                Maximum number of planning iterations. Defaults to 10.
            state_saving_dir (Optional[str], optional):
                Directory to save the agent's state. Defaults to None.
            planner_mode (bool, optional):
                Enable planner mode for solving tasks. Defaults to True.
            long_term_memory (Optional[LongTermMemoryBase]):
                Long-term memory instance, if None, long-term memory features
                will be disabled. Only works when memory service is available
                and healthy. If provided, the tool memory will be retrieved
                and added to the worker system prompt.
            long_term_memory_mode (
                Literal["agent_control", "static_control", "both"]
            ):
                Mode for long-term memory control. Defaults to "both".
                - "agent_control": Agent can control when to retrieve and
                  record memory
                - "static_control": Memory is automatically retrieved/recorded
                  at the beginning and end of each reply respectively.
                - "both": Both modes are available
        """
        if sys_prompt is None:
            self.base_sys_prompt = (
                f"You are a helpful assistant named {DEFAULT_PLANNER_NAME}."
                "If a given task can not be done easily, then you may need "
                "to use the tool `enter_planning_execution_mode` to "
                "change yourself to a more long-term planning mode."
                "If you need tool supplement for easier task, you can call "
                "`enter_easy_task_mode` to ask for more tools."
                "If the user asks a question related to AgentScope "
                "(e.g., about its usage or architecture), you can call "
                "`enter_qa_mode` to ask for RAG and GitHub MCP tools "
                "to answer the question."
            )
        else:
            self.base_sys_prompt = sys_prompt

        # Call super().__init__() early to initialize StateModule attributes
        super().__init__(
            name=DEFAULT_PLANNER_NAME,
            sys_prompt=self.base_sys_prompt,
            model=model,
            formatter=formatter,
            memory=memory,
            toolkit=toolkit,
            max_iters=max_iters,
            session_service=session_service,
            state_saving_dir=state_saving_dir,
            long_term_memory=long_term_memory,
            long_term_memory_mode=long_term_memory_mode,
        )
        self.browser_toolkit = browser_toolkit

        self.agent_working_dir_root = agent_working_dir
        self.task_dir = self.agent_working_dir_root
        self.worker_full_toolkit = worker_full_toolkit

        self.register_state("task_dir")
        self.register_state("agent_working_dir_root")

        # register tool_memory_retrieve tool
        # if long_term_memory is provided. Notice that
        # retrieve_from_memory tool is registered
        # in the toolkit by default.
        if long_term_memory:
            self.toolkit.register_tool_function(
                long_term_memory.tool_memory_retrieve,
            )

        # register finish_function_name
        if not self.toolkit.tools.get(self.finish_function_name):
            self.toolkit.register_tool_function(
                self.finish_function_name,
            )

        response_func = self.toolkit.tools.get(self.finish_function_name)

        # adjust ReActAgent parameters
        if enable_clarification:
            self._required_structured_model = (
                MetaPlannerResponseWithClarification
            )
            response_func.json_schema["function"][
                "description"
            ] = response_func.json_schema["function"].get(
                "description",
                "",
            ) + MetaPlannerResponseWithClarificationPrompt.format_map(
                {
                    "func_name": self.finish_function_name,
                },
            )
        else:
            self._required_structured_model = (
                MetaPlannerResponseNoClarification
            )
            response_func.json_schema["function"][
                "description"
            ] = response_func.json_schema["function"].get(
                "description",
                "",
            ) + MetaPlannerResponseNoClarificationPrompt.format_map(
                {
                    "func_name": self.finish_function_name,
                },
            )
            self._sys_prompt += "Notice: NEVER ask for clarification!"
        self.reply: Callable = partial(
            self.reply,
            structured_model=self._required_structured_model,
        )
        self.max_iters: int = max(self.max_iters, PLANNER_MAX_ITER)

        # for debugging and state resume, we need a flag to indicate
        self.planner_mode = planner_mode
        self.work_pattern: Literal[
            "simplest",
            "worker",
            "planner",
        ] = "simplest"
        self.register_state("planner_mode")
        self.register_state("work_pattern")

        self.planner_notebook = None
        self.roadmap_manager, self.worker_manager = None, None
        if planner_mode in ["dynamic", "enforced"]:
            self.planner_notebook = PlannerNoteBook()
            self.planner_notebook.full_tool_list = (
                self._get_full_worker_tool_list()
            )
            self.prepare_planner_tools(planner_mode)

            def reload_planner_notebook(state_dict: dict) -> PlannerNoteBook:
                # Create new notebook from state
                notebook = PlannerNoteBook.model_validate(state_dict)
                # Update managers to use the same reference
                if self.roadmap_manager:
                    self.roadmap_manager.planner_notebook = notebook
                if self.worker_manager:
                    self.worker_manager.planner_notebook = notebook
                return notebook

            self.register_state(
                "planner_notebook",
                custom_to_json=lambda x: x.model_dump(),
                custom_from_json=reload_planner_notebook,
            )

        # pre-reply hook
        self.register_instance_hook(
            "pre_reply",
            "agent_load_states_pre_reply_hook",
            agent_load_states_pre_reply_hook,
        )
        self.register_instance_hook(
            "pre_reply",
            "update_user_input_to_notebook_pre_reply_hook",
            update_user_input_pre_reply_hook,
        )
        # pre-reasoning hook
        self.register_instance_hook(
            "pre_reasoning",
            "planner_compose_reasoning_msg_pre_reasoning_hook",
            planner_compose_reasoning_msg_pre_reasoning_hook,
        )
        # post_reasoning hook
        self.register_instance_hook(
            "post_reasoning",
            "save_state_post_reasoning_hook",
            save_post_reasoning_state,
        )
        # post_action_hook
        self.register_instance_hook(
            "post_acting",
            "planner_save_post_action_state",
            planner_save_post_action_state,
        )

        self.register_instance_hook(
            "post_acting",
            "generate_response_post_action_hook",
            generate_response_post_action_hook,
        )

    def prepare_planner_tools(
        self,
        planner_mode: Literal["disable", "enforced", "dynamic"],
    ) -> None:
        """
        Prepare tool to planning depending on the selected mode.
        """
        assert self.planner_notebook
        self.roadmap_manager = RoadmapManager(
            planner_notebook=self.planner_notebook,
        )

        if self.worker_manager is None:
            self.worker_manager = WorkerManager(
                worker_model=self.model,
                worker_formatter=self.formatter,
                planner_notebook=self.planner_notebook,
                agent_working_dir=self.task_dir,
                worker_full_toolkit=self.worker_full_toolkit,
                session_service=self.session_service,
                sandbox=self.toolkit.sandbox,
                long_term_memory=self.long_term_memory,
            )
        else:
            self.worker_manager.planner_notebook = self.planner_notebook

        # clean
        self.toolkit.remove_tool_groups("planning")
        self.toolkit.create_tool_group(
            "planning",
            "Tool group for planning capability",
        )
        # re-register planning tool to enable loading the correct info
        self.toolkit.register_tool_function(
            self.roadmap_manager.decompose_task_and_build_roadmap,
            group_name="planning",
        )
        self.toolkit.register_tool_function(
            self.roadmap_manager.revise_roadmap,
            group_name="planning",
        )
        self.toolkit.register_tool_function(
            self.roadmap_manager.get_next_unfinished_subtask_from_roadmap,
            group_name="planning",
        )
        self.toolkit.register_tool_function(
            self.worker_manager.show_current_worker_pool,
            group_name="planning",
        )
        self.toolkit.register_tool_function(
            self.worker_manager.create_worker,
            group_name="planning",
        )
        self.toolkit.register_tool_function(
            self.worker_manager.execute_worker,
            group_name="planning",
        )

        if planner_mode == "dynamic":
            if "enter_planning_execution_mode" not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    self.enter_planning_execution_mode,
                )
            if "enter_easy_task_mode" not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    self.enter_easy_task_mode,
                )
            if "enter_qa_mode" not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    self.enter_qa_mode,
                )
            if "enter_data_analysis_mode" not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    self.enter_data_analysis_mode,
                )
            if "enter_deep_research_mode" not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    self.enter_deep_research_mode,
                )
            # Only activate after agent decides to enter the
            # planning-execution mode
            self.toolkit.update_tool_groups(["planning"], False)
        elif planner_mode == "enforced":
            self.toolkit.update_tool_groups(["planning"], True)
            # use the self.agent_working_dir as working dir
            self._update_toolkit_and_sys_prompt_for_planning()

    def _ensure_file_system_functions(self) -> None:
        required_tool_list = [
            "read_file",
            "write_file",
            "edit_file",
            "create_directory",
            "list_directory",
            "directory_tree",
            "list_allowed_directories",
            "run_shell_command",
        ]
        # Traditional AliasToolkit mode
        for tool_name in required_tool_list:
            if tool_name not in self.worker_full_toolkit.tools:
                raise ValueError(
                    f"{tool_name} must be in the worker toolkit and "
                    "its tool group must be active for complicated.",
                )
        share_tools(
            self.worker_full_toolkit,
            self.toolkit,
            required_tool_list,
        )

    async def _create_task_directory(
        self,
    ) -> None:
        create_task_dir = ToolUseBlock(
            type="tool_use",
            id=str(uuid.uuid4()),
            name="create_directory",
            input={
                "path": self.task_dir,
            },
        )
        tool_res = await self.toolkit.call_tool_function(create_task_dir)
        tool_res_msg = Msg(
            "system",
            content=[
                ToolResultBlock(
                    type="tool_result",
                    output=[],
                    name="create_directory",
                    id=create_task_dir["id"],
                ),
            ],
            role="system",
        )
        async for chunk in tool_res:
            # Turn into a tool result block
            tool_res_msg.content[0]["output"] = chunk.content
        await self.print(tool_res_msg)

    async def enter_planning_execution_mode(
        self,
        task_name: str,
    ) -> ToolResponse:
        """
        When the user task meets any of the following conditions, enter the
        solving complicated task mode by using this tool.
        1. the task cannot be done within 15 reasoning-acting iterations;
        2. the task cannot be done by the current tools you can see;
        3. the task is related to comprehensive research or information
            gathering
        4. some step requires browser operations (browsing webpages like
            Github & Arxiv, or need operations like book tickets)

        Args:
            task_name (`str`):
                Given a name to the current task as an indicator. Because
                this name will be used to create a directory, so try to
                use "_" instead of space between words, e.g. "A_NEW_TASK".
        """
        # build directory for the task
        self._ensure_file_system_functions()
        self.task_dir = os.path.join(
            self.agent_working_dir_root,
            task_name,
        )
        await self._create_task_directory()
        self.worker_manager.agent_working_dir = self.task_dir
        self._update_toolkit_and_sys_prompt_for_planning()

        return ToolResponse(
            metadata={"success": True},
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Successfully enter the planning-execution mode to "
                        "solve complicated task. "
                        "All the file operations, including "
                        "read/write/modification, should be done in directory "
                        f"{self.task_dir}"
                    ),
                ),
            ],
        )

    async def enter_easy_task_mode(
        self,
        task_name: str,
        additional_task_tools: list[str],
    ) -> ToolResponse:
        """
        When the user request meet all following conditions, enter the
        solving easy task mode by using this tool.
        1. the task can be done within 15 reasoning-acting iterations;
        2. the task requires only 3-5 additional tools to finish;
        3. NO NEED to use browser operations


        Args:
            task_name (`str`):
                Given a name to the current task as an indicator. Because
                this name will be used to create a directory, so try to
                use "_" instead of space between words, e.g. "A_NEW_TASK".
            additional_task_tools (List[`str`]):
                Given three to five (3 - 5) additional tools that are
                necessary for solving this easy task.
        """
        self._ensure_file_system_functions()
        self._sys_prompt = self.base_sys_prompt
        share_tools(
            self.worker_full_toolkit,
            self.toolkit,
            additional_task_tools,
        )
        self.task_dir = os.path.join(
            self.agent_working_dir_root,
            task_name,
        )
        await self._create_task_directory()
        self.work_pattern = "worker"
        available_tool_names = [
            item.get("function", {}).get("name")
            for item in list(self.toolkit.get_json_schemas())
        ]

        return ToolResponse(
            metadata={"success": True},
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Successfully enter the easy task mode to "
                        "solve task. "
                        "All the file operations, including "
                        "read/write/modification, should be done in directory "
                        f"{self.task_dir}"
                        f"Current available tools: {available_tool_names}"
                    ),
                ),
            ],
        )

    def _update_toolkit_and_sys_prompt_for_planning(self) -> None:
        # change agent settings for solving complicated task
        with open(
            Path(__file__).parent
            / "_built_in_long_sys_prompt"
            / "meta_planner_sys_prompt.md",
            "r",
            encoding="utf-8",
        ) as f:
            sys_prompt = f.read()
        sys_prompt = sys_prompt.format_map(
            {
                "tool_list": json.dumps(
                    self._get_full_worker_tool_list(),
                    ensure_ascii=False,
                ),
            },
        )
        self._sys_prompt = sys_prompt  # pylint: disable=W0201
        self.toolkit.update_tool_groups(["planning"], True)
        self.work_pattern = "planner"

        # add active interrupt function
        self.add_interrupt_function_name(
            "decompose_task_and_build_roadmap",
        )

    def resume_planner_tools(self) -> None:
        """Resume the planner notebook for tools"""
        self.prepare_planner_tools(self.planner_mode)
        if self.work_pattern == "planner":
            self._update_toolkit_and_sys_prompt_for_planning()

    def _get_full_worker_tool_list(self) -> list[dict]:
        full_worker_tool_list = [
            {
                "tool_name": func_dict.get("function", {}).get("name", ""),
                "description": func_dict.get("function", {}).get(
                    "description",
                    "",
                ),
            }
            for func_dict in self.worker_full_toolkit.get_json_schemas()
        ]
        return full_worker_tool_list

    async def enter_deep_research_mode(
        self,
        user_query: str,
    ):
        """
        Directly entering the deep research mode.
        Use this when the user provides some research or information gathering
        tasks, and require a comprehensive report.

        Args:
            user_query (`str`):
                digested user query for a deep research agent to start.
                If the conversation is recovered from an interruption,
                also carry the interruption in the context. For example,
                "User requests to continue the task...."
        """
        try:
            _, dr_agent = self.worker_manager.worker_pool.get(
                DEFAULT_DEEP_RESEARCH_AGENT_NAME,
            )
            msg = await dr_agent(
                Msg(
                    "user",
                    content=[TextBlock(type="text", text=user_query)],
                    role="user",
                ),
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            return ToolResponse(
                metadata={"success": False},
                content=[
                    TextBlock(
                        type="text",
                        text=(f"{e}\n" "Fail to execute deep research agent."),
                    ),
                ],
            )
        return ToolResponse(
            metadata={"success": True, "return_msg": msg},
            content=[TextBlock(type="text", text=msg.get_text_content())],
        )

    async def enter_data_analysis_mode(
        self,
        user_query: str,
    ):
        """
        Directly enter the data science mode.
        Use this when the user provides some data files and ask for processing.

        Args:
            user_query (`str`):
                digested user query for a data analysis agent to start.
                If the conversation is recovered from an interruption,
                also carry the interruption in the context. For example,
                "User requests to continue the task...."
        """
        try:
            _, ds_agent = self.worker_manager.worker_pool.get(
                DEFAULT_DS_AGENT_NAME,
            )
            set_run_ipython_cell(self.toolkit.sandbox)
            await ds_agent.memory.add(
                Msg(
                    "user",
                    content=[TextBlock(type="text", text=user_query)],
                    role="user",
                ),
            )
            msg = await ds_agent()
        except Exception as e:
            logger.error(traceback.format_exc())
            return ToolResponse(
                metadata={"success": False},
                content=[
                    TextBlock(
                        type="text",
                        text=(f"{e}\n" "Fail to execute data analysis agent."),
                    ),
                ],
            )
        return ToolResponse(
            metadata={"success": True, "return_msg": msg},
            content=[TextBlock(type="text", text=msg.get_text_content())],
        )

    async def enter_qa_mode(
        self,
        task_name: str,
    ) -> ToolResponse:
        """
        When the user request meet all following conditions, enter the
        QA mode by using this tool.
        1. The user asks a question related to AgentScope (e.g., about
        its usage or architecture).
        2. the task can be done within 15 reasoning-acting iterations;
        3. the task requires only 3-5 additional tools to finish;
        4. NO NEED to use browser operations

        Args:
            task_name (`str`):
                Given a name to the current task as an indicator. Because
                this name will be used to create a directory, so try to
                use "_" instead of space between words, e.g. "A_NEW_TASK".
        """
        self._ensure_file_system_functions()
        qa_prompt_path = (
            Path(__file__).resolve().parent
            / "qa_agent_utils"
            / "build_in_prompt"
            / "qaagent_base_sys_prompt.md"
        )
        self._sys_prompt = qa_prompt_path.read_text(encoding="utf-8").format(
            name=self.name,
        )
        available_tool_names = [
            item.get("function", {}).get("name")
            for item in list(self.toolkit.get_json_schemas())
        ]
        if "retrieve_knowledge" not in available_tool_names:
            await add_qa_tools(self.toolkit)
        github_error_message = None
        if not os.getenv("GITHUB_TOKEN"):
            github_error_message = (
                "⚠️ EnvironmentSetupError: Missing GITHUB_TOKEN; "
                "GitHub MCP tools cannot be used. "
                "Please export GITHUB_TOKEN in "
                "your environment before proceeding."
            )

        # self.toolkit.update_tool_groups("qa_mode", active=True)
        self.task_dir = os.path.join(
            self.agent_working_dir_root,
            task_name,
        )
        await self._create_task_directory()
        self.work_pattern = "worker"
        available_tool_names = [
            item.get("function", {}).get("name")
            for item in list(self.toolkit.get_json_schemas())
        ]
        # self.toolkit.update_tool_groups("qa_mode", active=False)
        content_blocks = [
            TextBlock(
                type="text",
                text=(
                    "Successfully enter the qa agent mode to "
                    "answer the user's question. "
                    "All the file operations, including "
                    "read/write/modification, should be done in directory "
                    f"{self.task_dir}"
                    f"Current available tools: {available_tool_names}"
                ),
            ),
        ]
        if github_error_message:
            content_blocks.append(
                TextBlock(
                    type="text",
                    text=github_error_message,
                ),
            )
        return ToolResponse(
            metadata={"success": True},
            content=content_blocks,
        )
