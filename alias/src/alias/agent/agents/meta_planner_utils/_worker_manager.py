# -*- coding: utf-8 -*-
"""
Coordination handler module for meta planner
"""
import os
from pathlib import Path
import json
from typing import Optional, Literal, List, Any
import asyncio
from agentscope import logger

from agentscope.module import StateModule
from agentscope.memory import InMemoryMemory, MemoryBase, LongTermMemoryBase
from agentscope.tool import ToolResponse
from agentscope.message import Msg, TextBlock, ToolUseBlock, ToolResultBlock
from agentscope.model import ChatModelBase, DashScopeChatModel
from agentscope.formatter import FormatterBase, DashScopeChatFormatter

from alias.runtime.alias_sandbox import AliasSandbox
from alias.agent.tools import AliasToolkit, share_tools
from alias.agent.agents._react_worker import ReActWorker
from alias.agent.utils.constants import (
    WORKER_MAX_ITER,
    DEFAULT_BROWSER_WORKER_NAME,
    DEFAULT_DS_AGENT_NAME,
    DEFAULT_DEEP_RESEARCH_AGENT_NAME,
)
from alias.agent.agents.common_agent_utils import WorkerResponse

from ._planning_notebook import WorkerInfo
from ._planning_notebook import PlannerNoteBook


def rebuild_reactworker(
    worker_info: WorkerInfo,
    old_toolkit: AliasToolkit,
    new_toolkit: AliasToolkit,
    memory: Optional[MemoryBase] = None,
    model: Optional[ChatModelBase] = None,
    formatter: Optional[FormatterBase] = None,
    exclude_tools: Optional[list[str]] = None,
) -> ReActWorker:
    """
    Rebuild a ReActAgent worker with specified configuration and tools.

    Creates a new ReActAgent using worker information and toolkit
    configuration. Tools are shared from the old toolkit to the new one,
    excluding any specified tools.

    Args:
        worker_info (WorkerInfo): Information about the worker including name,
            system prompt, and tool lists.
        old_toolkit (Toolkit): Source toolkit containing available tools.
        new_toolkit (Toolkit): Destination toolkit to receive shared tools.
        memory (Optional[MemoryBase], optional): Memory instance for the agent.
            Defaults to InMemoryMemory() if None.
        model (Optional[ChatModelBase], optional): Chat model instance.
        formatter (Optional[FormatterBase], optional): Message formatter.
            Defaults to DashScopeChatFormatter() if None.
        exclude_tools (Optional[list[str]], optional): List of tool names to
            exclude from sharing. Defaults to empty list if None.

    Returns:
        ReActAgent: A configured ReActAgent instance ready for use.

    Note:
        - The default model uses the DASHSCOPE_API_KEY environment variable
        - Tools are shared based on worker_info.tool_lists minus excluded tools
        - The agent is configured with thinking enabled and streaming support
    """
    if exclude_tools is None:
        exclude_tools = []
    tool_list = [
        tool_name
        for tool_name in worker_info.tool_lists
        if tool_name not in exclude_tools
    ]
    share_tools(old_toolkit, new_toolkit, tool_list)
    model = (
        model
        if model
        else DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen3-max-preview",
            stream=True,
        )
    )
    return ReActWorker(
        name=worker_info.worker_name,
        sys_prompt=worker_info.sys_prompt,
        model=model,
        formatter=formatter if formatter else DashScopeChatFormatter(),
        toolkit=new_toolkit,
        memory=InMemoryMemory() if memory is None else memory,
        max_iters=WORKER_MAX_ITER,
    )


async def check_file_existence(file_path: str, toolkit: AliasToolkit) -> bool:
    """
    Check if a file exists using the read_file tool from the provided toolkit.

    This function attempts to verify file existence by calling the read_file
    tool and checking the response for error indicators. It requires the
    toolkit to have a 'read_file' tool available.

    Args:
        file_path (str): The path to the file to check for existence.
        toolkit (Toolkit): The toolkit containing the read_file tool.

    Returns:
        bool: True if the file exists and is readable, False otherwise.

    Note:
        - Returns False if the 'read_file' tool is not available in the toolkit
        - Returns False if any exception occurs during the file read attempt
        - Uses error message detection ("no such file or directory") to
            determine existence
    """
    # Get read_file tool from AliasToolkit
    if "read_file" in toolkit.tools:
        read_toolkit = toolkit
    else:
        logger.warning(
            "No read_file tool available for file "
            f"existence check: {file_path}",
        )
        return False

    params = {
        "path": file_path,
    }
    read_file_block = ToolUseBlock(
        type="tool_use",
        id="manual_check_file_existence",
        name="read_file",
        input=params,
    )

    try:
        tool_res = await read_toolkit.call_tool_function(read_file_block)
        tool_res_msg = Msg(
            "system",
            [
                ToolResultBlock(
                    type="tool_result",
                    id="",
                    name="read_file",
                    output=[],
                ),
            ],
            "system",
        )
        async for chunk in tool_res:
            # Turn into a tool result block
            tool_res_msg.content[0][  # type: ignore[index]
                "output"
            ] = chunk.content
        if "no such file or directory" in str(tool_res_msg.content):
            return False
        else:
            return True
    except Exception as _:  # noqa: F841
        return False


class WorkerManager(StateModule):
    """
    Handles coordination between meta planner and worker agents.

    This class manages the creation, selection, and execution of worker agents
    to accomplish subtasks in a roadmap. It provides functionality for dynamic
    worker creation, worker selection based on task requirements, and
    processing worker responses to update the overall task progress.
    """

    def __init__(
        self,
        worker_model: ChatModelBase,
        worker_formatter: FormatterBase,
        planner_notebook: PlannerNoteBook,
        worker_full_toolkit: AliasToolkit,
        agent_working_dir: str,
        sandbox: AliasSandbox,
        worker_pool: Optional[
            dict[str, tuple[WorkerInfo, ReActWorker]]
        ] = None,
        session_service: Any = None,
        long_term_memory: Optional[LongTermMemoryBase] = None,
    ):
        """Initialize the CoordinationHandler.
        Args:
            worker_model (ChatModelBase):
                Main language model for coordination decisions
            worker_formatter (FormatterBase):
                Message formatter for model communication
            planner_notebook (PlannerNoteBook):
                Notebook containing roadmap and file information
            worker_full_toolkit (Toolkit):
                Complete toolkit available to workers
            agent_working_dir (str):
                Working directory for the agent operations
            worker_pool: dict[str, tuple[WorkerInfo, ReActAgent]]:
                workers that has already been created
            session_service (Any):
                Session service instance
            long_term_memory (Optional[LongTermMemoryBase]):
                Long-term memory instance, if None, long-term memory features
                will be disabled. Only works when memory service is available
                and healthy. If provided, the tool memory will be retrieved
                and added to the worker system prompt.
        """
        super().__init__()
        self.planner_notebook = planner_notebook
        self.worker_model = worker_model
        self.worker_formatter = worker_formatter
        self.worker_pool: dict[str, tuple[WorkerInfo, ReActWorker]] = (
            worker_pool if worker_pool else {}
        )
        self.agent_working_dir = agent_working_dir
        self.worker_full_toolkit = worker_full_toolkit
        self.base_sandbox = sandbox
        self.session_service = session_service
        self.long_term_memory = long_term_memory

        def reconstruct_workerpool(worker_pool_dict: dict) -> dict:
            rebuild_worker_pool = self.worker_pool
            for k, v in worker_pool_dict.items():
                worker_info = WorkerInfo(**v)
                # build-in agents
                if k in [
                    DEFAULT_DEEP_RESEARCH_AGENT_NAME,
                    DEFAULT_DS_AGENT_NAME,
                    DEFAULT_BROWSER_WORKER_NAME,
                ]:
                    continue
                # Handle regular worker reconstruction
                new_toolkit = AliasToolkit(sandbox=self.base_sandbox)

                rebuild_worker_pool[k] = (
                    worker_info,
                    rebuild_reactworker(
                        worker_info=worker_info,
                        old_toolkit=self.worker_full_toolkit,
                        new_toolkit=new_toolkit,
                        model=self.worker_model,
                        formatter=self.worker_formatter,
                        exclude_tools=["generate_response"],
                    ),
                )

            return rebuild_worker_pool

        self.register_state(
            "worker_pool",
            lambda x: {k: v[0].model_dump() for k, v in x.items()},
            custom_from_json=reconstruct_workerpool,
        )
        self.register_state("agent_working_dir")

    def register_worker(
        self,
        agent: ReActWorker,
        description: Optional[str] = None,
        worker_type: Literal["built-in", "dynamic-built"] = "dynamic",
    ) -> None:
        """
        Register a worker agent in the worker pool.

        Adds a worker agent to the available pool with appropriate metadata.
        Handles name conflicts by appending version numbers when necessary.

        Args:
            agent (ReActAgent):
                The worker agent to register
            description (Optional[str]):
                Description of the worker's capabilities
            worker_type (Literal["built-in", "dynamic-built"]):
                Type of worker agent
        """
        worker_info = WorkerInfo(
            worker_name=agent.name,
            description=description,
            worker_type=worker_type,
            status="ready-to-work",
        )
        if worker_type == "dynamic-built":
            worker_info.sys_prompt = agent.sys_prompt
            worker_info.tool_lists = list(agent.toolkit.tools.keys())

        if agent.name in self.worker_pool:
            name = agent.name
            version = 1
            while name in self.worker_pool:
                name = agent.name + f"_v{version}"
                version += 1
            agent.name, worker_info.worker_name = name, name
            self.worker_pool[name] = (worker_info, agent)
        else:
            self.worker_pool[agent.name] = (worker_info, agent)

    @staticmethod
    def _no_more_subtask_return() -> ToolResponse:
        """
        Return response when no more unfinished subtasks exist.

        Returns:
            ToolResponse: Response indicating no more subtasks are available
        """
        return ToolResponse(
            metadata={"success": False},
            content=[
                TextBlock(
                    type="text",
                    text="No more subtask exists. "
                    "Check whether the task is "
                    "completed solved.",
                ),
            ],
        )

    async def create_worker(
        self,
        worker_name: str,
        worker_system_prompt: str,
        tool_names: Optional[List[str]] = None,
        agent_description: str = "",
    ) -> ToolResponse:
        """
        Create a worker agent for the next unfinished subtask.

        Dynamically creates a specialized worker agent based on the
        requirements of the next unfinished subtask in the roadmap.
        The worker is configured with appropriate tools and system prompts
        based on the task needs.

        Each worker agent will be provided the following tools by default,
        so that you don't need to specify those again. Only specify the
        necessary tools that are not in the list
        [
            "read_file",
            "write_file",
            "edit_file",
            "create_directory",
            "list_directory",
            "directory_tree",
            "list_allowed_directories",
            "run_shell_command",
        ]

        Args:
            worker_name (str): The name of the worker agent.
            worker_system_prompt (str): The system prompt for the worker agent.
            tool_names (Optional[List[str]], optional):
                List of tools that should be assigned to the worker agent so
                that it can finish the subtask. MUST be from the
                `Available Tools for workers`
            agent_description (str, optional):
                A brief description of the worker's capabilities.

        Returns:
            ToolResponse: Response containing the creation result and worker
                details
        """
        if tool_names is None:
            tool_names = []

        # Traditional AliasToolkit mode
        suffix = ""
        worker_toolkit = AliasToolkit(sandbox=self.base_sandbox)
        share_tools(
            self.worker_full_toolkit,
            worker_toolkit,
            tool_names
            + [
                "read_file",
                "write_file",
                "edit_file",
                "search_files",
                "list_directory",
                "run_shell_command",
            ],
        )

        with open(
            Path(__file__).parent.parent
            / f"_built_in_long_sys_prompt{suffix}"
            / f"_worker_additional_sys_prompt{suffix}.md",
            "r",
            encoding="utf-8",
        ) as f:
            additional_worker_prompt = f.read()
        with open(
            Path(__file__).parent.parent
            / f"_built_in_long_sys_prompt{suffix}"
            / f"_tool_usage_rules{suffix}.md",
            "r",
            encoding="utf-8",
        ) as f:
            additional_worker_prompt += str(f.read()).format_map(
                {"agent_working_dir": self.agent_working_dir},
            )

        # Retrieve tool memory if long-term memory is available
        if self.long_term_memory is not None:
            try:
                from alias.server.clients.memory_client import MemoryClient

                # Check if memory service is available
                if not await MemoryClient.is_available():
                    logger.debug(
                        "Long-term memory service is enabled but not "
                        "available. Skipping tool memory retrieval.",
                    )
                elif not (
                    hasattr(self, "session_service") and self.session_service
                ):
                    logger.debug(
                        "Session service not available. "
                        "Skipping tool memory retrieval.",
                    )
                else:
                    # Get user ID from session
                    user_id = str(
                        self.session_service.session_entity.user_id,
                    )
                    # Use tool names as query for retrieving relevant
                    # tool memory
                    query = ",".join(tool_names) if tool_names else ""
                    try:
                        memory_client = MemoryClient()
                        retrieve_result = (
                            await memory_client.retrieve_tool_memory(
                                uid=user_id,
                                query=query,
                            )
                        )
                        if (
                            retrieve_result
                            and "No matching tool memories found"
                            not in retrieve_result
                            and isinstance(retrieve_result, str)
                            and retrieve_result.strip()
                        ):
                            tool_memory_context = (
                                "\n\n=== Below is some information "
                                "about tool usage from past experiences "
                                "===\n" + retrieve_result + "\n"
                                "==========================================\n"
                            )
                            additional_worker_prompt += tool_memory_context
                            logger.info(
                                f"Retrieved tool memory for worker "
                                f"{worker_name}",
                            )
                        else:
                            logger.warning(
                                f"No matching tool memories found for "
                                f"worker {worker_name}. Continuing without "
                                f"tool memory context.",
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to retrieve tool memory: {e}. "
                            f"Continuing without tool memory context.",
                        )
            except ImportError:
                logger.debug(
                    "MemoryClient not available. "
                    "Skipping tool memory retrieval.",
                )

        worker = ReActWorker(
            name=worker_name,
            sys_prompt=(worker_system_prompt + additional_worker_prompt),
            model=self.worker_model,
            formatter=self.worker_formatter,
            memory=InMemoryMemory(),
            toolkit=worker_toolkit,
            max_iters=WORKER_MAX_ITER,
            session_service=self.session_service,
        )

        self.register_worker(
            worker,
            description=agent_description,
            worker_type="dynamic-built",
        )

        return ToolResponse(
            metadata={"success": True},
            content=[
                TextBlock(
                    type="text",
                    text=(
                        f"Successfully created a worker agent:\n"
                        f"Worker name: {worker_name}\n"
                        f"Worker tools: {tool_names}\n"
                        f"Worker system prompt: {worker.sys_prompt}"
                    ),
                ),
            ],
        )

    async def show_current_worker_pool(self) -> ToolResponse:
        """
        List all currently available worker agents with
        their system prompts and tools.
        """
        worker_info: dict[str, dict] = {
            name: info.model_dump()
            for name, (info, _) in self.worker_pool.items()
        }
        return ToolResponse(
            metadata={"success": True},
            content=[
                TextBlock(
                    type="text",
                    text=json.dumps(worker_info, ensure_ascii=False, indent=2),
                ),
            ],
        )

    async def execute_worker(
        self,
        subtask_idx: int,
        selected_worker_name: str,
        detailed_instruction: str,
        reset_worker_memory: bool = False,
    ) -> ToolResponse:
        """
        Execute a worker agent for the next unfinished subtask.

        Args:
            subtask_idx (int):
                Index of the subtask to execute.
            selected_worker_name (str):
                Select a worker agent to execute by its name. If you are unsure
                what are the available agents, call `show_current_worker_pool`
                before using this function.
            detailed_instruction (str):
                Generate detailed instruction for the worker based on the
                next unfinished subtask in the roadmap. If you are unsure
                what is the next unavailable subtask, check with
                `get_next_unfinished_subtask_from_roadmap` to get more info.
            reset_worker_memory (bool):
                Whether to ensure the worker memory is empty before starting
                the task. For example, 1) if the same worker encounter errors,
                a safer way is to reset his memory to avoid error propagation;
                2) if a new subtask is assign to an existing worker, the worker
                memory can also be reset for better performance (but require
                providing sufficient context information in
                `detailed_instruction`); 3) if a worker is stopped just because
                hitting the maximum round constraint in the previous execution
                and it's going to work on the sam task, DO NOT reset the
                memory.

        """
        if selected_worker_name not in self.worker_pool:
            worker_info: dict[str, WorkerInfo] = {
                name: info for name, (info, _) in self.worker_pool.items()
            }
            current_agent_pool = json.dumps(
                worker_info,
                ensure_ascii=False,
                indent=2,
            )
            return ToolResponse(
                metadata={"success": False},
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            f"There is no {selected_worker_name} in current "
                            "agent pool.\n"
                            "Current agent pool:\n```json\n"
                            f"{current_agent_pool}\n"
                            "```"
                        ),
                    ),
                ],
            )

        worker = self.worker_pool[selected_worker_name][1]
        if reset_worker_memory:
            await worker.memory.clear()
        question_msg = Msg(
            role="user",
            name="user",
            content=detailed_instruction,
        )
        try:
            worker_response_msg = await worker(
                question_msg,
                # structured_model=WorkerResponse,
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise asyncio.CancelledError() from None

        if worker_response_msg.metadata is not None:
            worker_response = WorkerResponse(
                **worker_response_msg.metadata,
            )
            self.planner_notebook.roadmap.decomposed_tasks[
                subtask_idx
            ].workers.append(
                self.worker_pool[selected_worker_name][0],
            )
            # double-check to ensure the generated files exists
            for filepath, desc in worker_response.generated_files.items():
                if await check_file_existence(
                    filepath,
                    self.worker_full_toolkit,
                ):
                    self.planner_notebook.files[filepath] = desc
                else:
                    worker_response.generated_files.pop(filepath)

            return ToolResponse(
                metadata={
                    "success": True,
                    "worker_response": worker_response.model_dump_json(),
                },
                content=[
                    TextBlock(
                        type="text",
                        text=worker_response.model_dump_json(),
                    ),
                ],
            )
        else:
            return ToolResponse(
                metadata={
                    "success": False,
                    "worker_response": worker_response_msg.content,
                },
                content=[
                    TextBlock(
                        type="text",
                        text=str(worker_response_msg.content),
                    ),
                ],
            )
