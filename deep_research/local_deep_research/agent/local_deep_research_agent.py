# -*- coding: utf-8 -*-
"""Deep Research Agent"""
# pylint: disable=too-many-lines, no-name-in-module
import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional, Tuple, Type

import shortuuid
from agentscope import logger, setup_logger
from agentscope.agent import ReActAgent
from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase
from agentscope.message import Msg, TextBlock, ToolResultBlock, ToolUseBlock
from agentscope.model import ChatModelBase
from agentscope.tool import ToolResponse, view_text_file, write_text_file
from pydantic import BaseModel

from local_deep_research.embedding.base import BaseEmbedding
from local_deep_research.tools import (
    create_list_collections_tool,
    create_vector_search_tool,
)
from local_deep_research.utils.utils import (
    get_dynamic_tool_call_json,
    get_structure_output,
    load_prompt_dict,
    truncate_search_result,
)
from local_deep_research.vector_db.base import BaseVectorDB
from local_deep_research.built_in_prompt.promptmodule import (
    FollowupJudge,
    ReflectFailure,
    SubtasksDecomposition,
)

_DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT = "You're a helpful assistant."

_LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
_LOG_PATH = os.path.join(
    _LOG_DIR,
    f"log_{datetime.now().strftime('%y%m%d%H%M%S')}.md",
)
os.makedirs(_LOG_DIR, exist_ok=True)
setup_logger(level="INFO", filepath=_LOG_PATH)


class SubTaskItem(BaseModel):
    """Subtask item of deep research agent."""

    objective: str
    working_plan: Optional[str] = None
    knowledge_gaps: Optional[str] = None


class LocalDeepResearchAgent(ReActAgent):
    """
    Local Deep Research Agent for sophisticated research tasks using local vector database.

    This agent uses vector database for knowledge retrieval instead of web search,
    making it suitable for local/offline research scenarios.

    Example:
        .. code-block:: python

        from local_deep_research.embedding import SiliconflowEmbedding
        from local_deep_research.vector_db import Milvus

        embedding_model = SiliconflowEmbedding(model="BAAI/bge-m3")
        vector_db = Milvus(uri="http://localhost:19530")

        agent = LocalDeepResearchAgent(
            name="LocalResearcher",
            sys_prompt="You are a helpful research assistant.",
            model=my_chat_model,
            formatter=my_chat_formatter,
            memory=InMemoryMemory(),
            embedding_model=embedding_model,
            vector_db=vector_db,
            tmp_file_storage_dir=agent_working_dir,
        )
        response = await agent(
            Msg(
                name="user",
                content="Please give me a survey of the LLM-empowered agent.",
                role="user"
            )
        )
        ```
    """

    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        memory: MemoryBase,
        embedding_model: BaseEmbedding,
        vector_db: BaseVectorDB,
        sys_prompt: str = _DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT,
        max_iters: int = 30,
        max_depth: int = 3,
        tmp_file_storage_dir: str = "tmp",
    ) -> None:
        """Initialize the Local Deep Research Agent.

        Args:
            name (str):
                The unique identifier name for the agent instance.
            model (ChatModelBase):
                The chat model used for generating responses and reasoning.
            formatter (FormatterBase):
                The formatter used to convert messages into the required
                format for the model API.
            memory (MemoryBase):
                The memory component used to store and retrieve dialogue
                history.
            embedding_model (BaseEmbedding):
                The embedding model for converting text to vectors.
            vector_db (BaseVectorDB):
                The vector database instance for knowledge retrieval.
            sys_prompt (str, optional):
                The system prompt that defines the agent's behavior
                and personality.
                Defaults to _DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT.
            max_iters (int, optional):
                The maximum number of reasoning-acting loop iterations.
                Defaults to 30.
            max_depth (int, optional):
                The maximum depth of query expansion during deep searching.
                Defaults to 3.
            tmp_file_storage_dir (str, optional):
                The storage dir for generated files.
                Default to 'tmp'
        Returns:
            None
        """

        # initialization of prompts
        self.prompt_dict = load_prompt_dict()

        # Enhance the system prompt for deep research agent
        add_note = self.prompt_dict["add_note"].format_map(
            {"finish_function_name": f"`{self.finish_function_name}`"},
        )
        tool_use_rule = self.prompt_dict["tool_use_rule"].format_map(
            {"tmp_file_storage_dir": tmp_file_storage_dir},
        )
        sys_prompt = f"{sys_prompt}\n{add_note}\n{tool_use_rule}"

        super().__init__(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            memory=memory,
            max_iters=max_iters,
        )
        self.max_depth = max_depth
        self.memory = memory
        self.tmp_file_storage_dir = tmp_file_storage_dir
        self.current_subtask = []

        # Store embedding model and vector db for later use
        self.embedding_model = embedding_model
        self.vector_db = vector_db

        # Register all necessary tools for local deep research agent
        self.toolkit.register_tool_function(view_text_file)
        self.toolkit.register_tool_function(write_text_file)

        # Create and register vector search tool
        vector_search_tool = create_vector_search_tool(
            embedding_model=embedding_model,
            vector_db=vector_db,
        )
        self.toolkit.register_tool_function(vector_search_tool)

        # Create and register list collections tool
        list_collections_tool = create_list_collections_tool(
            vector_db=vector_db,
        )
        self.toolkit.register_tool_function(list_collections_tool)

        # Tool function names
        self.search_function = "search_vector_database"
        self.list_collections_function = "list_collections"
        self.read_file_function = "view_text_file"
        self.write_file_function = "write_text_file"
        self.summarize_function = "summarize_intermediate_results"

        self.intermediate_memory = []
        self.report_path_based = self.name + datetime.now().strftime(
            "%y%m%d%H%M%S",
        )
        self.report_index = 1
        self._required_structured_model = None
        self.user_query = None

        # Add agent methods as tools into toolkit
        self.toolkit.register_tool_function(self.reflect_failure)
        self.toolkit.register_tool_function(
            self.summarize_intermediate_results,
        )

    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
        structured_model: Type[BaseModel] | None = None,
    ) -> Msg:
        """The reply method of the agent."""
        # Maintain the subtask list
        self.user_query = msg.get_text_content()
        self.current_subtask.append(
            SubTaskItem(objective=self.user_query),
        )

        # Identify the expected output and generate a meta_planner_agent
        await self.decompose_and_expand_subtask()
        msg.content += (
            f"\nExpected Output:\n{self.current_subtask[0].knowledge_gaps}"
        )

        # Add user query message to memory
        await self.memory.add(msg)  # type: ignore

        # Record structured output model if provided
        if structured_model:
            self._required_structured_model = structured_model
            self.toolkit.set_extended_model(
                self.finish_function_name,
                structured_model,
            )

        for _ in range(self.max_iters):
            # Generate the working meta_planner_agent first
            if not self.current_subtask[-1].working_plan:
                await self.decompose_and_expand_subtask()

            # Write the instruction for reasoning
            cur_plan = self.current_subtask[-1].working_plan
            cur_know_gap = self.current_subtask[-1].knowledge_gaps
            reasoning_prompt = self.prompt_dict["reasoning_prompt"].format_map(
                {
                    "objective": self.current_subtask[-1].objective,
                    "meta_planner_agent": (
                        cur_plan
                        if cur_plan
                        else "There is no working meta_planner_agent now."
                    ),
                    "knowledge_gap": (
                        f"## Knowledge Gaps:\n {cur_know_gap}"
                        if cur_know_gap
                        else ""
                    ),
                    "depth": len(self.current_subtask),
                },
            )
            reasoning_prompt_msg = Msg(
                "user",
                content=[
                    TextBlock(
                        type="text",
                        text=reasoning_prompt,
                    ),
                ],
                role="user",
            )
            self.intermediate_memory.append(reasoning_prompt_msg)

            # Reasoning to generate tool calls
            backup_memory = deepcopy(self.memory)  # type: ignore
            await self.memory.add(self.intermediate_memory)  # type: ignore
            msg_reasoning = await self._reasoning()
            self.memory = backup_memory

            # Calling the tools
            for tool_call in msg_reasoning.get_content_blocks("tool_use"):
                self.intermediate_memory.append(
                    Msg(
                        self.name,
                        content=[tool_call],
                        role="assistant",
                    ),
                )  # add tool_use memory
                msg_response = await self._acting(tool_call)
                if msg_response:
                    await self.memory.add(msg_response)
                    self.current_subtask = []
                    return msg_response

        # When the maximum iterations are reached, summarize all the findings
        return await self._summarizing()

    async def _acting(self, tool_call: ToolUseBlock) -> Msg | None:
        """
        Execute a tool call and process its response with browser-specific
        handling.

        Args:
            tool_call (ToolUseBlock):
                The tool use block containing the tool name, parameters,
                and unique identifier for execution.
        Returns:
            Msg | None:
                Returns a response message if the finish function is called
                successfully, otherwise returns None to continue the
                reasoning-acting loop.
        """

        tool_res_msg = Msg(
            "system",
            [
                ToolResultBlock(
                    type="tool_result",
                    id=tool_call["id"],
                    name=tool_call["name"],
                    output=[],
                ),
            ],
            "system",
        )
        update_memory = False
        intermediate_report = ""
        chunk = ""
        try:
            # Execute the tool call
            tool_res = await self.toolkit.call_tool_function(tool_call)

            # Async generator handling
            async for chunk in tool_res:
                # Turn into a tool result block
                tool_res_msg.content[0]["output"] = chunk.content  # type: ignore[index]

                # Skip the printing of the finish function call
                if (
                    tool_call["name"] != self.finish_function_name
                    or tool_call["name"] == self.finish_function_name
                    and not chunk.metadata.get("success")
                ):
                    await self.print(tool_res_msg, chunk.is_last)

                # Return message if generate_response is called successfully
                if tool_call[
                    "name"
                ] == self.finish_function_name and chunk.metadata.get(
                    "success",
                    True,
                ):
                    if len(self.current_subtask) == 0:
                        return chunk.metadata.get("response_msg")

                # Summarize intermediate results into a draft report
                elif tool_call["name"] == self.summarize_function:
                    self.intermediate_memory = []
                    await self.memory.add(
                        Msg(
                            "assistant",
                            [
                                TextBlock(
                                    type="text",
                                    text=chunk.content[0]["text"],
                                ),
                            ],
                            "assistant",
                        ),
                    )

                # Truncate the vector search results that exceeds max length
                elif tool_call["name"] == self.search_function:
                    tool_res_msg.content[0]["output"] = truncate_search_result(
                        tool_res_msg.content[0]["output"],
                    )

                # Update memory when an intermediate report is generated
                if isinstance(chunk.metadata, dict) and chunk.metadata.get(
                    "update_memory",
                ):
                    update_memory = True
                    intermediate_report = chunk.metadata.get(
                        "intermediate_report",
                    )
            return None

        finally:
            # Record the tool result message in the intermediate memory
            if tool_call["name"] != self.summarize_function:
                self.intermediate_memory.append(tool_res_msg)

            # Read more information from the web page if necessary
            if tool_call["name"] == self.search_function:
                extract_res = await self._follow_up(chunk.content, tool_call)
                if isinstance(
                    extract_res.metadata,
                    dict,
                ) and extract_res.metadata.get("update_memory"):
                    self.intermediate_memory = []
                    await self.memory.add(
                        Msg(
                            "assistant",
                            content=[
                                TextBlock(
                                    type="text",
                                    text=extract_res.metadata.get(
                                        "intermediate_report",
                                    ).content[0]["text"],
                                ),
                            ],
                            role="assistant",
                        ),
                    )

            # Update memory with the intermediate report
            if update_memory:
                self.intermediate_memory = []
                await self.memory.add(
                    Msg(
                        "assistant",
                        content=[
                            TextBlock(
                                type="text",
                                text=intermediate_report.content[0]["text"],
                            ),
                        ],
                        role="assistant",
                    ),
                )

    async def get_model_output(
        self,
        msgs: list,
        format_template: Type[BaseModel] = None,
        stream: bool = True,
    ) -> Any:
        """
        Call the model and get output with or without a structured format.

        Args:
            msgs (list): A list of messages.
            format_template (BaseModel): structured format.
            stream (bool): stream-style output.
        """
        blocks = None
        if format_template:
            res = await self.model(
                await self.formatter.format(msgs=msgs),
                tools=get_dynamic_tool_call_json(
                    format_template,
                ),
            )

            if stream:
                async for content_chunk in res:
                    blocks = content_chunk.content
            else:
                blocks = res.content

            return get_structure_output(blocks)
        else:
            res = await self.model(
                await self.formatter.format(msgs=msgs),
            )

            if stream:
                async for content_chunk in res:
                    blocks = content_chunk.content
            else:
                blocks = res.content
            return blocks

    async def call_specific_tool(
        self,
        func_name: str,
        params: dict = None,
    ) -> Tuple[Msg, Msg]:
        """
        Call the specific tool in toolkit.

        Args:
            func_name (str): name of the tool.
            params (dict): input parameters of the tool.
        """
        tool_call = ToolUseBlock(
            id=shortuuid.uuid(),
            type="tool_use",
            name=func_name,
            input=params,
        )
        tool_call_msg = Msg(
            "assistant",
            [tool_call],
            role="assistant",
        )

        # get tool acting res
        tool_res_msg = Msg(
            "system",
            [
                ToolResultBlock(
                    type="tool_result",
                    id=tool_call["id"],
                    name=tool_call["name"],
                    output=[],
                ),
            ],
            "system",
        )
        tool_res = await self.toolkit.call_tool_function(
            tool_call,
        )
        async for chunk in tool_res:
            tool_res_msg.content[0]["output"] = chunk.content

        return tool_call_msg, tool_res_msg

    async def decompose_and_expand_subtask(self) -> ToolResponse:
        """Identify the knowledge gaps of the current subtask and generate a
        working meta_planner_agent by subtask decomposition. The working meta_planner_agent includes
        necessary steps for task completion and expanded steps.

        Returns:
            ToolResponse:
                The knowledge gaps and working meta_planner_agent of the current subtask
                in JSON format.
        """
        if len(self.current_subtask) <= self.max_depth:
            decompose_sys_prompt = self.prompt_dict["decompose_sys_prompt"]

            previous_plan = ""
            for i, subtask in enumerate(self.current_subtask):
                previous_plan += (
                    f"The {i}-th meta_planner_agent: {subtask.working_plan}\n"
                )
            previous_plan_inst = self.prompt_dict[
                "previous_plan_inst"
            ].format_map(
                {
                    "previous_plan": previous_plan,
                    "objective": self.current_subtask[-1].objective,
                },
            )

            try:
                gaps_and_plan = await self.get_model_output(
                    msgs=[
                        Msg("system", decompose_sys_prompt, "system"),
                        Msg("user", previous_plan_inst, "user"),
                    ],
                    format_template=SubtasksDecomposition,
                    stream=self.model.stream,
                )
                response = json.dumps(
                    gaps_and_plan,
                    indent=2,
                    ensure_ascii=False,
                )
            except Exception:  # noqa: F841
                gaps_and_plan = {}
                response = self.prompt_dict["retry_hint"].format_map(
                    {"state": "decomposing the subtask"},
                )
            self.current_subtask[-1].knowledge_gaps = gaps_and_plan.get(
                "knowledge_gaps",
                None,
            )
            self.current_subtask[-1].working_plan = gaps_and_plan.get(
                "working_plan",
                None,
            )
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=response,
                    ),
                ],
            )
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=self.prompt_dict["max_depth_hint"],
                ),
            ],
        )

    async def _follow_up(
        self,
        search_results: list | str,
        tool_call: ToolUseBlock,
    ) -> ToolResponse:
        """Analyze vector search results and determine if deeper search is needed.

        For local vector database search, we evaluate the quality and completeness
        of results, and may trigger follow-up searches with refined queries.
        """

        if len(self.current_subtask) < self.max_depth:
            # Step#1: Evaluate search results quality
            expansion_sys_prompt = self.prompt_dict["expansion_sys_prompt"]
            expansion_inst = self.prompt_dict["expansion_inst"].format_map(
                {
                    "objective": tool_call["input"].get("query_text", ""),
                    "checklist": self.current_subtask[0].knowledge_gaps,
                    "knowledge_gaps": self.current_subtask[-1].working_plan,
                    "search_results": search_results,
                },
            )

            try:
                follow_up_decision = await self.get_model_output(
                    msgs=[
                        Msg("system", expansion_sys_prompt, "system"),
                        Msg("user", expansion_inst, "user"),
                    ],
                    format_template=FollowupJudge,
                    stream=self.model.stream,
                )
            except Exception:  # noqa: F841
                follow_up_decision = {}

            # Step #2: Decide if we need deeper search
            if not follow_up_decision.get("is_sufficient", True):
                # Generate refined query for follow-up search
                refined_query = follow_up_decision.get(
                    "reasoning",
                    "Need more detailed information",
                )
                logger.info(f"Performing follow-up search: {refined_query}")

                intermediate_report = await self.summarize_intermediate_results()

                # Create a new subtask for deeper search
                self.current_subtask.append(
                    SubTaskItem(objective=refined_query),
                )

                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=self.prompt_dict["need_deeper_hint"],
                        ),
                    ],
                    metadata={
                        "update_memory": True,
                        "intermediate_report": intermediate_report,
                    },
                )
            else:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=follow_up_decision.get(
                                "reasoning",
                                self.prompt_dict["sufficient_hint"],
                            ),
                        ),
                    ],
                )
        else:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict["max_depth_hint"],
                    ),
                ],
            )

    async def summarize_intermediate_results(self) -> ToolResponse:
        """Summarize the intermediate results into a report when a step
        in working meta_planner_agent is completed.

        Returns:
            ToolResponse:
                The summarized draft report.
        """
        if len(self.intermediate_memory) == 0:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict["no_result_hint"],
                    ),
                ],
            )
        # agent actively call this tool
        if self.intermediate_memory[-1].name == self.summarize_function:
            blocks = await self.get_model_output(
                msgs=self.intermediate_memory
                + [
                    Msg(
                        "user",
                        self.prompt_dict["summarize_hint"].format_map(
                            {
                                "meta_planner_agent": self.current_subtask[
                                    -1
                                ].working_plan,
                            },
                        ),
                        role="user",
                    ),
                ],
                stream=self.model.stream,
            )
            self.current_subtask[-1].working_plan = blocks[0][
                "text"
            ]  # type: ignore[index]
        report_prefix = "#" * len(self.current_subtask)
        summarize_sys_prompt = self.prompt_dict[
            "summarize_sys_prompt"
        ].format_map(
            {"report_prefix": report_prefix},
        )
        # get all tool result
        tool_result = ""
        for item in self.intermediate_memory:
            if isinstance(item.content, str):
                tool_result += item.content + "\n"
            elif isinstance(item.content, list):
                for each in item.content:
                    if each["type"] == "tool_result":
                        tool_result += str(each) + "\n"
            else:
                logger.warning(
                    "Unknown content type: %s!",
                    type(item.content),
                )
                continue
        summarize_instruction = self.prompt_dict["summarize_inst"].format_map(
            {
                "objective": self.current_subtask[0].objective,
                "knowledge_gaps": self.current_subtask[0].knowledge_gaps,
                "working_plan": self.current_subtask[-1].working_plan,
                "tool_result": tool_result,
            },
        )

        blocks = await self.get_model_output(
            msgs=[
                Msg("system", summarize_sys_prompt, "system"),
                Msg("user", summarize_instruction, "user"),
            ],
            stream=self.model.stream,
        )
        intermediate_report = blocks[0]["text"]  # type: ignore[index]

        # Write the intermediate report
        intermediate_report_path = os.path.join(
            self.tmp_file_storage_dir,
            f"{self.report_path_based}_"
            f"inprocess_report_{self.report_index}.md",
        )
        self.report_index += 1
        params = {
            "file_path": intermediate_report_path,
            "content": intermediate_report,
        }
        await self.call_specific_tool(
            func_name=self.write_file_function,
            params=params,
        )
        logger.info(
            "Storing the intermediate findings: %s",
            intermediate_report,
        )
        if (
            self.intermediate_memory[-1].has_content_blocks("tool_use")
            and self.intermediate_memory[-1].get_content_blocks("tool_use")[0][
                "name"
            ]
            == self.summarize_function
        ):
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict["update_report_hint"].format_map(
                            {
                                "intermediate_report": intermediate_report,
                                "report_path": intermediate_report_path,
                            },
                        ),
                    ),
                ],
            )
        else:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict["save_report_hint"].format_map(
                            {
                                "intermediate_report": intermediate_report,
                            },
                        ),
                    ),
                ],
            )

    async def _generate_deepresearch_report(
        self,
        checklist: str,
    ) -> Tuple[Msg, str]:
        """Collect and polish all draft reports into a final report.

        Args:
            checklist (`str`):
                The expected output items of the original task.
        """
        reporting_sys_prompt = self.prompt_dict["reporting_sys_prompt"]
        reporting_sys_prompt.format_map(
            {
                "original_task": self.user_query,
                "checklist": checklist,
            },
        )

        # Collect all intermediate reports
        if self.report_index > 1:
            inprocess_report = ""
            for index in range(self.report_index):
                params = {
                    "file_path": os.path.join(
                        self.tmp_file_storage_dir,
                        f"{self.report_path_based}_"
                        f"inprocess_report_{index + 1}.md",
                    ),
                }
                _, read_draft_tool_res_msg = await self.call_specific_tool(
                    func_name=self.read_file_function,
                    params=params,
                )
                inprocess_report += (
                    read_draft_tool_res_msg.content[0]["output"][0]["text"]
                    + "\n"
                )

            msgs = [
                Msg(
                    "system",
                    content=reporting_sys_prompt,
                    role="system",
                ),
                Msg(
                    "user",
                    content=f"Draft report:\n{inprocess_report}",
                    role="user",
                ),
            ]
        else:  # Use only intermediate memory to generate report
            msgs = [
                Msg(
                    "system",
                    content=reporting_sys_prompt,
                    role="system",
                ),
            ] + self.intermediate_memory

        blocks = await self.get_model_output(
            msgs=msgs,
            stream=self.model.stream,
        )
        final_report_content = blocks[0]["text"]  # type: ignore[index]
        logger.info(
            "The final Report is generated: %s",
            final_report_content,
        )

        # Write the final report into a file
        detailed_report_path = os.path.join(
            self.tmp_file_storage_dir,
            f"{self.report_path_based}_detailed_report.md",
        )

        params = {
            "file_path": detailed_report_path,
            "content": final_report_content,
        }
        _, write_report_tool_res_msg = await self.call_specific_tool(
            func_name=self.write_file_function,
            params=params,
        )

        return write_report_tool_res_msg, detailed_report_path

    async def _summarizing(self) -> Msg:
        """Generate a report based on the exsisting findings when the
        agent fails to solve the problem in the maximum iterations."""

        (
            summarized_content,
            _,
        ) = await self._generate_deepresearch_report(
            checklist=self.current_subtask[0].knowledge_gaps,
        )
        return Msg(
            name=self.name,
            role="assistant",
            content=json.dumps(
                summarized_content.content[0]["output"][0],
                indent=2,
                ensure_ascii=False,
            ),
        )

    async def reflect_failure(self) -> ToolResponse:
        """Reflect on the failure of the action and determine to rephrase
        the meta_planner_agent or deeper decompose the current step.

        Returns:
            ToolResponse:
                The reflection about meta_planner_agent rephrasing and subtask decomposition.
        """
        reflect_sys_prompt = self.prompt_dict["reflect_sys_prompt"]
        conversation_history = ""
        for msg in self.intermediate_memory:
            conversation_history += (
                json.dumps(
                    {"role": "user", "content": msg.content},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        reflect_inst = self.prompt_dict["reflect_instruction"].format_map(
            {
                "conversation_history": conversation_history,
                "meta_planner_agent": self.current_subtask[-1].working_plan,
            },
        )
        try:
            reflection = await self.get_model_output(
                msgs=[
                    Msg("system", reflect_sys_prompt, "system"),
                    Msg("user", reflect_inst, "user"),
                ],
                format_template=ReflectFailure,
                stream=self.model.stream,
            )
            response = json.dumps(
                reflection,
                indent=2,
                ensure_ascii=False,
            )
        except Exception:  # noqa: F841
            reflection = {}
            response = self.prompt_dict["retry_hint"].format_map(
                {"state": "making the reflection"},
            )

        if reflection.get("rephrase_subtask", False) and reflection[
            "rephrase_subtask"
        ].get(
            "need_rephrase",
            False,
        ):  # type: ignore[index]
            self.current_subtask[-1].working_plan = reflection[
                "rephrase_subtask"
            ][
                "rephrased_plan"
            ]  # type: ignore[index]
        elif reflection.get("decompose_subtask", False) and reflection[
            "decompose_subtask"
        ].get(
            "need_decompose",
            False,
        ):  # type: ignore[index]
            if len(self.current_subtask) <= self.max_depth:
                intermediate_report = (
                    await self.summarize_intermediate_results()
                )
                self.current_subtask.append(
                    SubTaskItem(
                        objective=reflection[
                            "decompose_subtask"
                        ].get(  # type: ignore[index]
                            "failed_subtask",
                            None,
                        ),
                    ),
                )
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=response,
                        ),
                    ],
                    metadata={
                        "update_memory": True,
                        "intermediate_report": intermediate_report,
                    },
                )
            else:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=self.prompt_dict["max_depth_hint"],
                        ),
                    ],
                )
        else:
            pass
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=response,
                ),
            ],
        )

    # pylint: disable=invalid-overridden-method, unused-argument
    async def generate_response(  #
        self,
        response: str,
        **_kwargs: Any,
    ) -> ToolResponse:
        """Generate a detailed report as a response.

        Besides, when calling this function, the reasoning-acting memory will
        be cleared, so your response should contain a brief summary of what
        you have done so far.

        Args:
            response (`str`):
                Your response to the user.
        """
        checklist = self.current_subtask[0].knowledge_gaps
        completed_subtask = self.current_subtask.pop()

        if len(self.current_subtask) == 0:
            (
                summarized_content,
                _,
            ) = await self._generate_deepresearch_report(
                checklist=checklist,
            )
            response_msg = Msg(
                name=self.name,
                role="assistant",
                content=json.dumps(
                    summarized_content.content[0]["output"][0],
                    indent=2,
                    ensure_ascii=False,
                ),
            )
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Successfully generated detailed report.",
                    ),
                ],
                metadata={
                    "success": True,
                    "response_msg": response_msg,
                },
                is_last=True,
            )
        else:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict[
                            "subtask_complete_hint"
                        ].format_map(
                            {
                                "cur_obj": completed_subtask.objective,
                                "next_obj": self.current_subtask[-1].objective,
                            },
                        ),
                    ),
                ],
                metadata={
                    "success": True,
                },
                is_last=True,
            )
