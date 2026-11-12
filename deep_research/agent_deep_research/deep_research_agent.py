# -*- coding: utf-8 -*-
"""Deep Research Agent"""
# pylint: disable=too-many-lines, no-name-in-module
import os
import json

from typing import Type, Optional, Any, Tuple
from datetime import datetime
import shortuuid
from pydantic import BaseModel

from built_in_prompt.promptmodule import (
    SubtasksDecomposition,
    WebExtraction,
    FollowupJudge,
    ReflectFailure,
)
from utils import (
    truncate_search_result,
    load_prompt_dict,
)

from agentscope import logger, setup_logger
from agentscope.mcp import MCPClient
from agentscope.model import ChatModelBase, ChatResponse
from agentscope.tool import (
    ToolResponse,
    ToolChunk,
    Toolkit,
    FunctionTool,
    Read,
    Write,
)
from agentscope.message import (
    Msg,
    UserMsg,
    AssistantMsg,
    SystemMsg,
    ToolCallBlock,
    TextBlock,
    ToolResultBlock,
)
from agentscope.state import AgentState
from agentscope.permission import PermissionMode


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


class DeepResearchAgent:
    """
    Deep Research Agent for sophisticated research tasks.

    Example:
        .. code-block:: python

        agent = DeepResearchAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=my_chat_model,
            search_mcp_client=my_tavily_search_client,
            tmp_file_storage_dir=agent_working_dir,
        )
        response = await agent(
            UserMsg(
                "user",
                "Please give me a survey of the LLM-empowered agent.",
            )
        )
    """

    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        search_mcp_client: MCPClient,
        sys_prompt: str = _DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT,
        max_iters: int = 30,
        max_depth: int = 3,
        tmp_file_storage_dir: str = "tmp",
    ) -> None:
        """Initialize the Deep Research Agent.

        Args:
            name (str):
                The unique identifier name for the agent instance.
            model (ChatModelBase):
                The chat model used for generating responses and reasoning.
            search_mcp_client (MCPClient):
                The stateful MCP client (already connected) used to provide
                the tools for deep search.
            sys_prompt (str, optional):
                The system prompt that defines the agent's behavior
                and personality.
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
        self.finish_function_name = "generate_response"

        # Enhance the system prompt for deep research agent
        add_note = self.prompt_dict["add_note"].format_map(
            {"finish_function_name": f"`{self.finish_function_name}`"},
        )
        tool_use_rule = self.prompt_dict["tool_use_rule"].format_map(
            {"tmp_file_storage_dir": tmp_file_storage_dir},
        )
        self.sys_prompt = f"{sys_prompt}\n{add_note}\n{tool_use_rule}"

        self.name = name
        self.model = model
        self.max_iters = max_iters
        self.max_depth = max_depth
        self.tmp_file_storage_dir = tmp_file_storage_dir
        self.current_subtask: list[SubTaskItem] = []

        # Agent state for tool calls (Read/Write need state injection)
        self.state = AgentState()
        self.state.permission_context.mode = PermissionMode.BYPASS

        # Register all necessary tools for deep research agent
        self.toolkit = Toolkit(
            tools=[
                Read(),
                Write(),
                FunctionTool(
                    self.reflect_failure,
                    name="reflect_failure",
                ),
                FunctionTool(
                    self.summarize_intermediate_results,
                    name="summarize_intermediate_results",
                ),
                FunctionTool(
                    self.generate_response,
                    name=self.finish_function_name,
                ),
            ],
            mcps=[search_mcp_client],
        )

        self.search_function = "tavily-search"
        self.extract_function = "tavily-extract"
        self.read_file_function = "Read"
        self.write_file_function = "Write"
        self.summarize_function = "summarize_intermediate_results"

        self.intermediate_memory: list[Msg] = []
        self.memory: list[Msg] = []
        self.report_path_based = self.name + datetime.now().strftime(
            "%y%m%d%H%M%S",
        )
        self.report_index = 1
        self.user_query: Optional[str] = None

    async def __call__(
        self,
        msg: Msg | list[Msg] | None = None,
    ) -> Msg:
        """Call the agent to get a reply."""
        return await self.reply(msg)

    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
    ) -> Msg:
        """The reply method of the agent."""
        if msg is None:
            raise ValueError("The input message cannot be None.")
        if isinstance(msg, list):
            msg = msg[0]

        # Maintain the subtask list
        self.user_query = msg.get_text_content()
        self.current_subtask.append(
            SubTaskItem(objective=self.user_query),
        )

        # Identify the expected output and generate a plan
        await self.decompose_and_expand_subtask()
        msg.content.append(
            TextBlock(
                text=f"\nExpected Output:\n"
                f"{self.current_subtask[0].knowledge_gaps}",
            ),
        )

        # Add user query message to memory
        self.memory.append(msg)

        for _ in range(self.max_iters):
            # Generate the working plan first
            if not self.current_subtask[-1].working_plan:
                await self.decompose_and_expand_subtask()

            # Write the instruction for reasoning
            cur_plan = self.current_subtask[-1].working_plan
            cur_know_gap = self.current_subtask[-1].knowledge_gaps
            reasoning_prompt = self.prompt_dict["reasoning_prompt"].format_map(
                {
                    "objective": self.current_subtask[-1].objective,
                    "plan": cur_plan
                    if cur_plan
                    else "There is no working plan now.",
                    "knowledge_gap": f"## Knowledge Gaps:\n {cur_know_gap}"
                    if cur_know_gap
                    else "",
                    "depth": len(self.current_subtask),
                },
            )
            reasoning_prompt_msg = UserMsg(
                "user",
                [TextBlock(text=reasoning_prompt)],
            )
            self.intermediate_memory.append(reasoning_prompt_msg)

            # Reasoning to generate tool calls
            msg_reasoning = await self._reasoning()

            # Calling the tools
            for tool_call in msg_reasoning.get_content_blocks("tool_call"):
                self.intermediate_memory.append(
                    AssistantMsg(self.name, [tool_call]),
                )  # add tool_call memory
                msg_response = await self._acting(tool_call)
                if msg_response:
                    self.memory.append(msg_response)
                    self.current_subtask = []
                    return msg_response

        # When the maximum iterations are reached, summarize all the findings
        return await self._summarizing()

    async def _collect_content(
        self,
        res: ChatResponse | Any,
    ) -> list:
        """Collect the content from a model response, accumulating streaming
        chunks if necessary.

        Args:
            res: The return value of ``model.__call__`` — either a
                ``ChatResponse`` (non-streaming) or an async generator of
                ``ChatResponse`` deltas (streaming).
        """
        if isinstance(res, ChatResponse):
            return res.content

        final_content: list = []
        async for chunk in res:
            if chunk.is_last:
                final_content = list(chunk.content)
        return final_content

    async def _reasoning(self) -> Msg:
        """Reasoning to generate tool calls by calling the model with the
        available tool schemas."""
        messages = self.memory + self.intermediate_memory
        tools = await self.toolkit.get_tool_schemas()
        res = await self.model(messages=messages, tools=tools)
        content = await self._collect_content(res)
        return AssistantMsg(self.name, content)

    async def _acting(self, tool_call: ToolCallBlock) -> Msg | None:
        """
        Execute a tool call and process its response.

        Args:
            tool_call (ToolCallBlock):
                The tool call block containing the tool name, parameters,
                and unique identifier for execution.
        Returns:
            Msg | None:
                Returns a response message if the finish function is called
                successfully, otherwise returns None to continue the
                reasoning-acting loop.
        """

        tool_res_msg = AssistantMsg(
            name=self.name,
            content=[
                ToolResultBlock(
                    id=tool_call.id,
                    name=tool_call.name,
                    output=[],
                ),
            ],
        )
        update_memory = False
        intermediate_report = ""
        last_chunk_content: list = []
        try:
            # Execute the tool call
            async for item in self.toolkit.call_tool(
                tool_call,
                self.state,
            ):
                if isinstance(item, ToolResponse):
                    # Final accumulated response — content already captured
                    continue

                # item is a ToolChunk
                last_chunk_content = item.content
                tool_res_msg.content[0].output = item.content

                # Return message if generate_response is called successfully
                if (
                    tool_call.name == self.finish_function_name
                    and item.metadata.get("success")
                ):
                    if len(self.current_subtask) == 0:
                        return item.metadata.get("response_msg")

                # Summarize intermediate results into a draft report
                elif tool_call.name == self.summarize_function:
                    self.intermediate_memory = []
                    if item.content:
                        self.memory.append(
                            AssistantMsg(
                                self.name,
                                [TextBlock(text=item.content[0].text)],
                            ),
                        )

                # Truncate the web extract results that exceeds max length
                elif tool_call.name in [
                    self.search_function,
                    self.extract_function,
                ]:
                    tool_res_msg.content[0].output = truncate_search_result(
                        tool_res_msg.content[0].output,
                    )

                # Update memory when an intermediate report is generated
                if isinstance(item.metadata, dict) and item.metadata.get(
                    "update_memory",
                ):
                    update_memory = True
                    intermediate_report = item.metadata.get(
                        "intermediate_report",
                    )
            return None

        finally:
            # Record the tool result message in the intermediate memory
            if tool_call.name != self.summarize_function:
                self.intermediate_memory.append(tool_res_msg)

            # Read more information from the web page if necessary
            if tool_call.name == self.search_function:
                extract_res = await self._follow_up(
                    last_chunk_content,
                    tool_call,
                )
                if (
                    isinstance(extract_res, ToolChunk)
                    and extract_res.metadata.get("update_memory")
                ):
                    self.intermediate_memory = []
                    self.memory.append(
                        AssistantMsg(
                            self.name,
                            [
                                TextBlock(
                                    text=extract_res.metadata.get(
                                        "intermediate_report",
                                    ),
                                ),
                            ],
                        ),
                    )

            # Update memory with the intermediate report
            if update_memory:
                self.intermediate_memory = []
                self.memory.append(
                    AssistantMsg(
                        self.name,
                        [TextBlock(text=intermediate_report)],
                    ),
                )

    async def get_model_output(
        self,
        msgs: list,
        format_template: Type[BaseModel] = None,
    ) -> Any:
        """
        Call the model and get output with or without a structured format.

        Args:
            msgs (list): A list of messages.
            format_template (Type[BaseModel]): structured format pydantic
                model.
        """
        if format_template:
            res = await self.model.generate_structured_output(
                messages=msgs,
                structured_model=format_template,
            )
            return res.content
        else:
            res = await self.model(messages=msgs)
            return await self._collect_content(res)

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
        tool_call = ToolCallBlock(
            id=shortuuid.uuid(),
            name=func_name,
            input=json.dumps(params or {}),
        )
        tool_call_msg = AssistantMsg(self.name, [tool_call])

        final_response: Optional[ToolResponse] = None
        async for item in self.toolkit.call_tool(tool_call, self.state):
            if isinstance(item, ToolResponse):
                final_response = item

        output = final_response.content if final_response else []
        tool_res_msg = AssistantMsg(
            self.name,
            [
                ToolResultBlock(
                    id=tool_call.id,
                    name=tool_call.name,
                    output=output,
                ),
            ],
        )
        return tool_call_msg, tool_res_msg

    async def decompose_and_expand_subtask(self) -> ToolChunk:
        """Identify the knowledge gaps of the current subtask and generate a
        working plan by subtask decomposition. The working plan includes
        necessary steps for task completion and expanded steps.

        Returns:
            ToolChunk:
                The knowledge gaps and working plan of the current subtask
                in text format.
        """
        if len(self.current_subtask) <= self.max_depth:
            decompose_sys_prompt = self.prompt_dict["decompose_sys_prompt"]

            previous_plan = ""
            for i, subtask in enumerate(self.current_subtask):
                previous_plan += f"The {i}-th plan: {subtask.working_plan}\n"
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
                        SystemMsg("system", decompose_sys_prompt),
                        UserMsg("user", previous_plan_inst),
                    ],
                    format_template=SubtasksDecomposition,
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
            return ToolChunk(
                content=[
                    TextBlock(text=response),
                ],
            )
        return ToolChunk(
            content=[
                TextBlock(text=self.prompt_dict["max_depth_hint"]),
            ],
        )

    async def _follow_up(
        self,
        search_results: list | str,
        tool_call: ToolCallBlock,
    ) -> ToolChunk:
        """Read the website more intensively to mine more information for
        the task. And generate a follow-up subtask if necessary to perform
        deep search.
        """

        if len(self.current_subtask) < self.max_depth:
            # Step#1: query expansion
            expansion_sys_prompt = self.prompt_dict["expansion_sys_prompt"]

            # Extract query from tool_call.input (JSON string in 2.x)
            try:
                tool_input = json.loads(tool_call.input)
            except (json.JSONDecodeError, TypeError):
                tool_input = {}
            query = tool_input.get("query", "")

            # Extract text from search results for prompt formatting
            search_results_text = ""
            for block in search_results:
                if hasattr(block, "text"):
                    search_results_text += block.text + "\n"
                else:
                    search_results_text += str(block) + "\n"

            expansion_inst = self.prompt_dict["expansion_inst"].format_map(
                {
                    "objective": query,
                    "checklist": self.current_subtask[0].knowledge_gaps,
                    "knowledge_gaps": self.current_subtask[-1].working_plan,
                    "search_results": search_results_text,
                },
            )

            try:
                follow_up_subtask = await self.get_model_output(
                    msgs=[
                        SystemMsg("system", expansion_sys_prompt),
                        UserMsg("user", expansion_inst),
                    ],
                    format_template=WebExtraction,
                )
            except Exception:  # noqa: F841
                follow_up_subtask = {}

            #  Step #2: extract the url
            if follow_up_subtask.get("need_more_information", False):
                expansion_response_msg = AssistantMsg(
                    "assistant",
                    follow_up_subtask.get(
                        "reasoning",
                        "I need more information.",
                    ),
                )
                urls = follow_up_subtask.get("url", None)
                logger.info("Reading %s", urls)

                # call the extract_function
                params = {
                    "urls": urls,
                    "extract_depth": "basic",
                }
                (
                    extract_tool_use_msg,
                    extract_tool_res_msg,
                ) = await self.call_specific_tool(
                    func_name=self.extract_function,
                    params=params,
                )
                self.intermediate_memory.append(extract_tool_use_msg)

                extract_tool_res_msg.content[0].output = truncate_search_result(
                    extract_tool_res_msg.content[0].output,
                )
                self.intermediate_memory.append(extract_tool_res_msg)

                # Step #4: follow up judge
                try:
                    follow_up_response = await self.get_model_output(
                        msgs=[
                            UserMsg("user", expansion_inst),
                            expansion_response_msg,
                            extract_tool_use_msg,
                            extract_tool_res_msg,
                            UserMsg(
                                "user",
                                self.prompt_dict["follow_up_judge_sys_prompt"],
                            ),
                        ],
                        format_template=FollowupJudge,
                    )
                except Exception:  # noqa: F841
                    follow_up_response = {}
                if not follow_up_response.get("is_sufficient", True):
                    subtasks = follow_up_subtask.get("subtask", None)
                    logger.info("Figuring out %s", subtasks)
                    intermediate_report_chunk = (
                        await self.summarize_intermediate_results()
                    )
                    intermediate_report_text = ""
                    if intermediate_report_chunk.content:
                        intermediate_report_text = (
                            intermediate_report_chunk.content[0].text
                        )
                    self.current_subtask.append(
                        SubTaskItem(objective=subtasks),
                    )
                    return ToolChunk(
                        content=[
                            TextBlock(
                                text=follow_up_response.get(
                                    "reasoning",
                                    self.prompt_dict["need_deeper_hint"],
                                ),
                            ),
                        ],
                        metadata={
                            "update_memory": True,
                            "intermediate_report": intermediate_report_text,
                        },
                    )
                else:
                    return ToolChunk(
                        content=[
                            TextBlock(
                                text=follow_up_response.get(
                                    "reasoning",
                                    self.prompt_dict["sufficient_hint"],
                                ),
                            ),
                        ],
                    )
            else:
                return ToolChunk(
                    content=[
                        TextBlock(
                            text=follow_up_subtask.get(
                                "reasoning",
                                self.prompt_dict["sufficient_hint"],
                            ),
                        ),
                    ],
                )
        else:
            return ToolChunk(
                content=[
                    TextBlock(text=self.prompt_dict["max_depth_hint"]),
                ],
            )

    async def summarize_intermediate_results(self) -> ToolChunk:
        """Summarize the intermediate results into a report when a step
        in working plan is completed.

        Returns:
            ToolChunk:
                The summarized draft report.
        """
        if len(self.intermediate_memory) == 0:
            return ToolChunk(
                content=[
                    TextBlock(text=self.prompt_dict["no_result_hint"]),
                ],
            )
        # agent actively call this tool
        if self.intermediate_memory[-1].name == self.summarize_function:
            blocks = await self.get_model_output(
                msgs=self.intermediate_memory
                + [
                    UserMsg(
                        "user",
                        self.prompt_dict["summarize_hint"].format_map(
                            {
                                "plan": self.current_subtask[-1].working_plan,
                            },
                        ),
                    ),
                ],
            )
            self.current_subtask[-1].working_plan = blocks[0].text
        report_prefix = "#" * len(self.current_subtask)
        summarize_sys_prompt = self.prompt_dict[
            "summarize_sys_prompt"
        ].format_map(
            {"report_prefix": report_prefix},
        )
        # get all tool result
        tool_result = ""
        for item in self.intermediate_memory:
            for block in item.content:
                if isinstance(block, ToolResultBlock):
                    tool_result += str(block) + "\n"
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
                SystemMsg("system", summarize_sys_prompt),
                UserMsg("user", summarize_instruction),
            ],
        )
        intermediate_report = blocks[0].text

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
            self.intermediate_memory[-1].has_content_blocks("tool_call")
            and self.intermediate_memory[-1].get_content_blocks(
                "tool_call",
            )[0].name
            == self.summarize_function
        ):
            return ToolChunk(
                content=[
                    TextBlock(
                        text=self.prompt_dict[
                            "update_report_hint"
                        ].format_map(
                            {
                                "intermediate_report": intermediate_report,
                                "report_path": intermediate_report_path,
                            },
                        ),
                    ),
                ],
            )
        else:
            return ToolChunk(
                content=[
                    TextBlock(
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
    ) -> Tuple[Msg, str, str]:
        """Collect and polish all draft reports into a final report.

        Args:
            checklist (`str`):
                The expected output items of the original task.

        Returns:
            Tuple[Msg, str, str]:
                The write tool result message, the detailed report file
                path, and the final report content text.
        """
        reporting_sys_prompt = self.prompt_dict["reporting_sys_prompt"]
        reporting_sys_prompt = reporting_sys_prompt.format_map(
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
                output = read_draft_tool_res_msg.content[0].output
                if isinstance(output, list) and output:
                    inprocess_report += output[0].text + "\n"
                elif isinstance(output, str):
                    inprocess_report += output + "\n"

            msgs = [
                SystemMsg("system", reporting_sys_prompt),
                UserMsg("user", f"Draft report:\n{inprocess_report}"),
            ]
        else:  # Use only intermediate memory to generate report
            msgs = [
                SystemMsg("system", reporting_sys_prompt),
            ] + self.intermediate_memory

        blocks = await self.get_model_output(msgs=msgs)
        final_report_content = blocks[0].text
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
        write_report_tool_res_msg, _ = await self.call_specific_tool(
            func_name=self.write_file_function,
            params=params,
        )

        return write_report_tool_res_msg, detailed_report_path, final_report_content

    async def _summarizing(self) -> Msg:
        """Generate a report based on the existing findings when the
        agent fails to solve the problem in the maximum iterations."""

        _, _, final_report = await self._generate_deepresearch_report(
            checklist=self.current_subtask[0].knowledge_gaps,
        )
        return AssistantMsg(self.name, final_report)

    async def reflect_failure(self) -> ToolChunk:
        """Reflect on the failure of the action and determine to rephrase
        the plan or deeper decompose the current step.

        Returns:
            ToolChunk:
                The reflection about plan rephrasing and subtask decomposition.
        """
        reflect_sys_prompt = self.prompt_dict["reflect_sys_prompt"]
        conversation_history = ""
        for msg in self.intermediate_memory:
            conversation_history += (
                json.dumps(
                    {"role": msg.role, "content": str(msg.content)},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        reflect_inst = self.prompt_dict["reflect_instruction"].format_map(
            {
                "conversation_history": conversation_history,
                "plan": self.current_subtask[-1].working_plan,
            },
        )
        try:
            reflection = await self.get_model_output(
                msgs=[
                    SystemMsg("system", reflect_sys_prompt),
                    UserMsg("user", reflect_inst),
                ],
                format_template=ReflectFailure,
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
        ):
            self.current_subtask[-1].working_plan = reflection[
                "rephrase_subtask"
            ][
                "rephrased_plan"
            ]
        elif reflection.get("decompose_subtask", False) and reflection[
            "decompose_subtask"
        ].get(
            "need_decompose",
            False,
        ):
            if len(self.current_subtask) <= self.max_depth:
                intermediate_report_chunk = (
                    await self.summarize_intermediate_results()
                )
                intermediate_report_text = ""
                if intermediate_report_chunk.content:
                    intermediate_report_text = (
                        intermediate_report_chunk.content[0].text
                    )
                self.current_subtask.append(
                    SubTaskItem(
                        objective=reflection[
                            "decompose_subtask"
                        ].get(
                            "failed_subtask",
                            None,
                        ),
                    ),
                )
                return ToolChunk(
                    content=[
                        TextBlock(text=response),
                    ],
                    metadata={
                        "update_memory": True,
                        "intermediate_report": intermediate_report_text,
                    },
                )
            else:
                return ToolChunk(
                    content=[
                        TextBlock(text=self.prompt_dict["max_depth_hint"]),
                    ],
                )
        else:
            pass
        return ToolChunk(
            content=[
                TextBlock(text=response),
            ],
        )

    async def generate_response(
        self,
        response: str,
    ) -> ToolChunk:
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
            _, _, final_report = await self._generate_deepresearch_report(
                checklist=checklist,
            )
            response_msg = AssistantMsg(self.name, final_report)
            return ToolChunk(
                content=[
                    TextBlock(
                        text="Successfully generated detailed report.",
                    ),
                ],
                metadata={
                    "success": True,
                    "response_msg": response_msg,
                },
            )
        else:
            return ToolChunk(
                content=[
                    TextBlock(
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
            )
