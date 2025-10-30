# -*- coding: utf-8 -*-
"""Deep Research Agent"""
# pylint: disable=too-many-lines, no-name-in-module
import os
import json
import traceback
import uuid

from typing import Type, Optional, Any, Tuple
from datetime import datetime
# from copy import deepcopy
import shortuuid
from pydantic import BaseModel

from alias.agent.agents import AliasAgentBase
from alias.agent.tools import AliasToolkit
from alias.agent.agents._planning_tools._planning_notebook import (
    WorkerResponse,
)

from alias.agent.agents._dragent_utils.built_in_prompt.promptmodule import (
    SubtasksDecomposition,
    WebExtraction,
    FollowupJudge,
    ReflectFailure,
)
from alias.agent.agents._dragent_utils.utils import (
    load_prompt_dict,
    get_dynamic_tool_call_json,
    get_structure_output,
)

from agentscope import logger, setup_logger
# from agentscope.mcp import StatefulClientBase
# from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase
from agentscope.tool import (
    ToolResponse,
    Toolkit,
)
from agentscope.message import (
    Msg,
    ToolUseBlock,
    TextBlock,
    ToolResultBlock,
)


_DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT = "You're a helpful assistant."


class SubTaskItem(BaseModel):
    """Subtask item of deep research agent."""

    objective: str
    working_plan: Optional[str] = None
    knowledge_gaps: Optional[str] = None


async def deep_research_pre_reply_hook(
    self: "DeepResearchAgent",
    kwargs: dict[str, Any],  # pylint: disable=W0613
):
    # Maintain the subtask list
    msg: Msg = kwargs.get("msg")
    if msg is None:
        raise ValueError("Deep research agent gets no msg.")

    self.user_query = msg.get_text_content()
    self.current_subtask.append(
        SubTaskItem(objective=self.user_query),
    )

    # Identify the expected output and generate a plan
    await self.decompose_and_expand_subtask()
    msg.content += (
        f"\nExpected Output:\n{self.current_subtask[0].knowledge_gaps}"
    )


async def deep_research_post_reply_hook(
    self: "DeepResearchAgent",
    kwargs: Any,
    output: Any,
):
    self.current_subtask = []

def _dump_json(
    save_info: list[Msg] | dict,
    dir: str = "./dr_execution_trac"
):
    if not os.path.isdir(dir):
        os.makedirs(dir, exist_ok=True)
    if isinstance(save_info, list) and len(save_info) > 0 and isinstance(save_info[0], Msg):
        save_info = [msg.to_dict() for msg in save_info]
        file_path = os.path.join(dir, "memory-" + str(uuid.uuid4().hex) + ".json")
    else:
        file_path = os.path.join(dir, "plane-" + str(uuid.uuid4().hex) + ".json")
    with open(file_path, "w") as f:
        json.dump(save_info, f, ensure_ascii=False, indent=4)


async def deep_research_pre_reasoning_hook(
    self: "DeepResearchAgent",
    kwargs: Any,
):
    memory = await self.memory.get_memory()
    _dump_json(memory)

    # check if the previous search action solve the subtasks
    if len(self.search_call_buffer) > 0:
        search_queries = [
            tool_call.get("input", {}).get("query")
            for tool_call in self.search_call_buffer
        ]
        research_results = []
        for tool_call in self.search_call_buffer:
            msg = await self._get_research_result(tool_call.get("id"))
            if msg is not None:
                research_results.append(
                    json.dumps(
                        msg.get_content_blocks("tool_result"),
                        ensure_ascii=False,
                    )
                )
        await self._follow_up(
            search_results="\n".join(research_results),
            search_queries="\n".join(search_queries),
        )
    self.search_call_buffer = []

    if not self.current_subtask[-1].working_plan:
        await self.decompose_and_expand_subtask()

    _dump_json([subtask.model_dump() for subtask in self.current_subtask])

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
    await self.memory.add(reasoning_prompt_msg)


async def deep_research_post_reasoning_hook(
    self: "DeepResearchAgent",  # pylint: disable=W0613
    kwargs: Any,
    output_msg: Msg,
):
    num_msgs = await self.memory.size()
    if num_msgs > 1:
        # remove the msg added by planner_compose_reasoning_pre_reasoning_hook
        await self.memory.delete(num_msgs - 2)


async def deep_research_post_action_hook(
    self: "DeepResearchAgent",
    kwargs: Any,
    output_msg: Msg,
):
    tool_call = kwargs.get("tool_call", {})
    if tool_call and tool_call.get("name") == self.search_function:
        self.search_call_buffer.append(tool_call)


class DeepResearchAgent(AliasAgentBase):
    """
    Deep Research Agent for sophisticated research tasks.

    Example:
        .. code-block:: python

        agent = DeepResearchAgent(
            name="Friday",
            sys_prompt="You are a helpful assistant named Friday.",
            model=my_chat_model,
            formatter=my_chat_formatter,
            memory=InMemoryMemory(),
            search_mcp_client=my_tavily_search_client,
            tmp_file_storage_dir=agent_working_dir,
        )
        response = await agent(
            Msg(
                name=“user”,
                content="Please give me a survey of the LLM-empowered agent.",
                role=“user”
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
        toolkit: AliasToolkit,
        sys_prompt: str = _DEEP_RESEARCH_AGENT_DEFAULT_SYS_PROMPT,
        max_iters: int = 30,
        max_depth: int = 3,
        tmp_file_storage_dir: str = "/workspace",
        state_saving_dir: Optional[str] = None,
        session_service: Any = None,
    ) -> None:
        """Initialize the Deep Research Agent.

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
            toolkit (Toolkit):
                The toolkit object that contains the tool functions.
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

        self.search_function = "tavily_search"
        self.extract_function = "tavily_extract"
        self.read_file_function = "read_file"
        self.write_file_function = "write_file"
        self.summarize_function = "summarize_intermediate_results"

        # Enhance the system prompt for deep research agent
        add_note = self.prompt_dict["add_note"].format_map(
            {
                "search_tool": self.search_function,
                "extract_tool": self.extract_function,
                "intermediate_summarize": self.summarize_function,
                "reflect_failure": "reflect_failure",
                "subtask_finish": "finish_current_subtask",
                "finish_function_name": self.finish_function_name
            },
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
            toolkit=toolkit,
            max_iters=max_iters,
            session_service=session_service,
            state_saving_dir=state_saving_dir,
        )
        self.max_depth = max_depth
        self.memory = memory
        self.tmp_file_storage_dir = tmp_file_storage_dir
        self.current_subtask = []

        self.report_path_based = self.name + datetime.now().strftime(
            "%y%m%d%H%M%S",
        )
        self.report_index = 1
        self._required_structured_model = None
        self.user_query = None

        # add functions into toolkit
        self.toolkit.register_tool_function(self.reflect_failure)
        self.toolkit.register_tool_function(
            self.summarize_intermediate_results,
        )
        self.toolkit.register_tool_function(
            self.finish_current_subtask
        )

        # add hooks
        self.register_instance_hook(
            "pre_reply",
            "deep_research_pre_reply_hook",
            deep_research_pre_reply_hook
        )
        self.register_instance_hook(
            "post_reply",
            "deep_research_post_reply_hook",
            deep_research_post_reply_hook
        )
        self.register_instance_hook(
            "pre_reasoning",
            "deep_research_pre_reasoning_hook",
            deep_research_pre_reasoning_hook
        )
        self.register_instance_hook(
            "post_reasoning",
            "deep_research_post_reasoning_hook",
            deep_research_post_reasoning_hook
        )
        self.register_instance_hook(
            "post_acting",
            "deep_research_post_action_hook",
            deep_research_post_action_hook
        )
        self.search_call_buffer = []

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
        print_msg = Msg(self.name, [], "assistant")
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
                    print_msg.content = blocks
                    await self.print(print_msg, last=False)
                await self.print(print_msg, last=True)
            else:
                blocks = res.content
                print_msg.content = blocks
                await self.print(print_msg, last=True)

            return get_structure_output(blocks)
        else:
            res = await self.model(
                await self.formatter.format(msgs=msgs),
            )

            if stream:
                async for content_chunk in res:
                    blocks = content_chunk.content
                    print_msg.content = blocks
                    await self.print(print_msg, last=False)
                await self.print(print_msg, last=True)
            else:
                blocks = res.content
                print_msg.content = blocks
                await self.print(print_msg, last=True)
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
        working plan by subtask decomposition. The working plan includes
        necessary steps for task completion and expanded steps.

        Returns:
            ToolResponse:
                The knowledge gaps and working plan of the current subtask
                in JSON format.
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

            await self.print(
                Msg(
                    self.name,
                    "Identify the knowledge gaps of the current "
                    "subtask and generate a working plan by subtask "
                    "decomposition",
                    "assistant"
                ),
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
        search_queries: str,
    ) -> ToolResponse:
        """Read the website more intensively to mine more information for
        the task. And generate a follow-up subtask if necessary to perform
        deep search.
        """
        # Step#1: query expansion
        expansion_sys_prompt = self.prompt_dict["expansion_sys_prompt"]
        expansion_inst = self.prompt_dict["expansion_inst"].format_map(
            {
                "checklist": self.current_subtask[0].knowledge_gaps,
                "knowledge_gaps": (
                    self.current_subtask[-1].knowledge_gaps
                    if self.current_subtask[-1].knowledge_gaps
                    else self.current_subtask[-1].objective
                ),
                "search_query": search_queries,
                "search_results": search_results,
            },
        )
        await self.print(
            Msg(
                self.name,
                "(Follow-up by extraction)"
                "Read the website more intensively to mine more "
                "information.",
                "assistant"
            ),
        )
        try:
            extraction_check = await self.get_model_output(
                msgs=[
                    Msg("system", expansion_sys_prompt, "system"),
                    Msg("user", expansion_inst, "user"),
                ],
                format_template=WebExtraction,
                stream=self.model.stream,
            )
            follow_up_msg = Msg(
                self.name,
                [
                    TextBlock(
                        type="text",
                        text=json.dumps(
                            extraction_check,
                            ensure_ascii=False,
                            indent=2
                        )
                    )
                ],
                role="assistant",
            )
            await self.memory.add(follow_up_msg)

        except Exception as e:  # noqa: F841
            logger.warning(
                f"Error when checking subtask finish status {e}"
                f"{traceback.format_exc()}"
            )
            extraction_check = {}

        expansion_response_msg = Msg(
            "assistant",
            extraction_check.get(
                "reasoning",
                "I need more information.",
            ),
            role="assistant",
        )
        #  Step #2: extract the url
        extract_tool_use_msg, extract_tool_res_msg = None, None
        if extraction_check.get("need_extraction", False):
            urls = extraction_check.get("url", None)
            await self.print(
                Msg(
                    self.name,
                    [TextBlock(type="text", text=f"Reading {urls}")],
                    "assistant"
                ),
                last=True
            )

            # call the extract_function
            params = {
                "urls": urls if isinstance(urls, list) else [urls],
                "extract_depth": "basic",
            }
            (
                extract_tool_use_msg,
                extract_tool_res_msg,
            ) = await self.call_specific_tool(
                func_name=self.extract_function,
                params=params,
            )
            await self.print(extract_tool_use_msg, True)
            await self.memory.add(extract_tool_use_msg)

            await self.print(extract_tool_res_msg, True)
            await self.memory.add(extract_tool_res_msg)

        # Step #4: follow-up judge
        try:
            await self.print(
                Msg(
                    self.name,
                    "(Follow-up to explore)"
                    "Check if current subtask knowledge gaps are fulfilled",
                    "assistant"
                ),
            )
            msgs = [
                Msg("user", expansion_inst, "user"),
                expansion_response_msg,
            ]
            if extract_tool_use_msg and extract_tool_res_msg:
                msgs += [
                    extract_tool_use_msg,
                    extract_tool_res_msg,
                ]
            msgs += [
                Msg(
                    "user",
                    self.prompt_dict["follow_up_judge_sys_prompt"],
                    role="user",
                )
            ]
            follow_up_judge = await self.get_model_output(
                msgs=msgs,
                format_template=FollowupJudge,
                stream=self.model.stream,
            )
            follow_up_msg = Msg(
                self.name,
                content=[
                    TextBlock(
                        type="text",
                        text=json.dumps(
                            follow_up_judge,
                            ensure_ascii=False, indent=2
                        )
                    )
                ],
                role="assistant",
            )
            await self.memory.add(follow_up_msg)
        except Exception as e:  # noqa: F841
            logger.warning(
                f"Error when checking subtask finish status {e}"
            )
            logger.error(traceback.format_exc())
            follow_up_judge = {}

        if follow_up_judge.get("knowledge_gap_revision", ""):
            self.current_subtask[-1].knowledge_gaps = \
                follow_up_judge.get("knowledge_gap_revision", "")

        if (
            follow_up_judge.get("to_further_explore", False)
            and len(self.current_subtask) < self.max_depth
        ):
            subtask = follow_up_judge.get("subtask", None)
            await self.print(
                Msg(
                    name=self.name,
                    content=[
                        TextBlock(
                            type="text",
                            text="Still need to do more research "
                                 f"to figure out {subtask}",
                        )
                    ],
                    role="assistant"
                )
            )
            intermediate_report = (
                await self.summarize_intermediate_results()
            )
            self.current_subtask.append(
                SubTaskItem(objective=subtask),
            )
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=follow_up_judge.get(
                            "reasoning",
                            self.prompt_dict["need_deeper_hint"],
                        ),
                    ),
                ],
                metadata={
                    "update_memory": True,
                    "intermediate_report": intermediate_report,
                },
            )
        elif not follow_up_judge.get("to_further_explore", False):
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=follow_up_judge.get(
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

    async def _get_intermediate_memory(
        self,
        remove_last_tool_use: bool = False,
    ) -> list[Msg]:
        memory_msgs = await self.memory.get_memory()
        intermediate_memory = []
        for msg in reversed(memory_msgs):
            if msg.metadata and msg.metadata.get("is_report_msg"):
                break
            else:
                intermediate_memory.append(msg)
        intermediate_memory.reverse()
        if remove_last_tool_use:
            while (
                len(intermediate_memory) > 0 and
                intermediate_memory[-1].has_content_blocks("tool_use")
            ):
                intermediate_memory.pop(-1)
        return intermediate_memory

    async def _replace_intermediate_memory(self):
        memory_msgs = await self.memory.get_memory()
        remove_num = 0
        for msg in reversed(memory_msgs):
            if msg.metadata and msg.metadata.get("is_report_msg"):
                break
            elif msg.role == "user":
                break
            elif msg.has_content_blocks("tool_use"):
                stop = False
                for block in msg.get_content_blocks("tool_use"):
                    if block.get("name") == self.summarize_function:
                        stop = True
                if stop:
                    break
                else:
                    remove_num += 1
            else:
                remove_num += 1
        start_index = len(memory_msgs) - remove_num
        logger.info(
            "---> delete messages: "
            f"{list(range(start_index, len(memory_msgs)))}"
        )
        await self.memory.delete(list(range(start_index, len(memory_msgs))))

    async def _get_research_result(
        self,
        tool_call_id: str
    ) -> Msg | None:
        memory_msgs = await self.memory.get_memory()
        for msg in reversed(memory_msgs):
            if msg.has_content_blocks("tool_result"):
                for block in msg.get_content_blocks('tool_result'):
                    if block.get("id") == tool_call_id:
                        return msg
        return None

    async def summarize_intermediate_results(self) -> ToolResponse:
        """Summarize the intermediate results into a report when a step
        in working plan is completed.

        Returns:
            ToolResponse:
                The summarized draft report.
        """
        intermediate_memory = await self._get_intermediate_memory()
        if len(intermediate_memory) == 0:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=self.prompt_dict["no_result_hint"],
                    ),
                ],
            )
        # agent actively call this tool
        if intermediate_memory[-1].name == self.summarize_function:
            await self.print(
                Msg(
                    self.name,
                    "[summarize_intermediate_results]"
                    "Examine whether the knowledge gaps or objective"
                    "have been fulfill",
                    "assistant"
                ),
            )

            blocks = await self.get_model_output(
                msgs=intermediate_memory
                + [
                    Msg(
                        "user",
                        self.prompt_dict["summarize_hint"].format_map(
                            {
                                "knowledge_gaps": (
                                    self.current_subtask[-1].knowledge_gaps
                                    if self.current_subtask[-1].knowledge_gaps
                                    else self.current_subtask[-1].objective
                                ),
                            },
                        ),
                        role="user",
                    ),
                ],
                stream=self.model.stream,
            )
            self.current_subtask[-1].knowledge_gaps = blocks[0][
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
        for item in intermediate_memory:
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
                "root_gaps": self.current_subtask[0].knowledge_gaps,
                "cur_gaps": self.current_subtask[-1].working_plan,
                "tool_result": tool_result,
            },
        )

        await self.print(
            Msg(
                self.name,
                "Summarize the intermediate results into a report",
                "assistant"
            ),
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
            "path": intermediate_report_path,
            "content": intermediate_report,
        }
        _, tool_result = await self.call_specific_tool(
            func_name=self.write_file_function,
            params=params,
        )
        await self.print(tool_result, last=True)

        # clean unnecessary memory
        await self._replace_intermediate_memory()
        if (
            intermediate_memory[-1].has_content_blocks("tool_use")
            and intermediate_memory[-1].get_content_blocks("tool_use")[0][
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
                metadata={"is_report_msg": True,}
            )
        else:
            # add to memory for the follow-up case
            await self.memory.add(
                Msg(
                    "assistant",
                    content=[
                        TextBlock(
                            type="text",
                            text=intermediate_report,
                        ),
                    ],
                    role="assistant",
                    metadata={"is_report_msg": True}
                ),
            )
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
                tmp_report_path = os.path.join(
                    self.tmp_file_storage_dir,
                    f"{self.report_path_based}_"
                    f"inprocess_report_{index + 1}.md"
                )
                params = {
                    "file_path": tmp_report_path,
                    "limit": None,
                }
                _, read_draft_tool_res_msg = await self.call_specific_tool(
                    func_name=self.read_file_function,
                    params=params,
                )
                inprocess_report += (
                    read_draft_tool_res_msg.content[0]["output"][0]["text"]
                    + "\n"
                )
                await self.print(
                    Msg(
                        self.name,
                        [
                            TextBlock(
                                type="text",
                                text="Reading progress report: "
                                     f"{tmp_report_path}"
                            )
                        ],
                        "assistant"
                    )
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
            intermediate_memory = await self._get_intermediate_memory(
                remove_last_tool_use=True
            )
            msgs = [
                Msg(
                    "system",
                    content=reporting_sys_prompt,
                    role="system",
                ),
            ] + intermediate_memory

        await self.print(
            Msg(
                self.name,
                "Collect and polish all draft reports into a final report",
                "assistant"
            ),
        )
        try:
            blocks = await self.get_model_output(
                msgs=msgs,
                stream=self.model.stream,
            )
            final_report_content = blocks[0]["text"]  # type: ignore[index]
            logger.info(
                "The final Report is generated: %s",
                final_report_content,
            )
        except Exception as e:
            logger.error(str(e))
            logger.error(traceback.format_exc())
            raise e from None

        # Write the final report into a file
        detailed_report_path = os.path.join(
            self.tmp_file_storage_dir,
            f"{self.report_path_based}_detailed_report.md",
        )

        params = {
            "path": detailed_report_path,
            "content": final_report_content,
        }
        _, write_report_tool_res_msg = await self.call_specific_tool(
            func_name=self.write_file_function,
            params=params,
        )

        return write_report_tool_res_msg, detailed_report_path

    async def _summarizing(self) -> Msg:
        """Generate a report based on the existing findings when the
        agent fails to solve the problem in the maximum iterations."""

        (
            summarized_content,
            detailed_report_path,
        ) = await self._generate_deepresearch_report(
            checklist=self.current_subtask[0].knowledge_gaps,
        )
        subtask_progress_summary = json.dumps(
            summarized_content.content[0]["output"][0],
            indent=2,
            ensure_ascii=False,
        )
        structure_response = WorkerResponse(
            task_done=False,
            subtask_progress_summary=subtask_progress_summary,
            generated_files=detailed_report_path,
        )
        response_msg = Msg(
            name=self.name,
            role="assistant",
            content=[
                TextBlock(type="text",
                          text=subtask_progress_summary, )
            ],
            metadata=structure_response.model_dump(),
        )
        return response_msg

    async def reflect_failure(
        self,
    ) -> ToolResponse:
        """Reflect on the failure of the action and determine to rephrase
        the plan or deeper decompose the current step.

        Returns:
            ToolResponse:
                The reflection about plan rephrasing and subtask decomposition.
        """
        intermediate_memory = await self._get_intermediate_memory(
            remove_last_tool_use=True
        )
        reflect_sys_prompt = self.prompt_dict["reflect_sys_prompt"]
        conversation_history = ""
        for msg in intermediate_memory:
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
                "objective": self.current_subtask[-1].objective,
                "plan": self.current_subtask[-1].working_plan,
                "knowledge_gaps": self.current_subtask[-1].knowledge_gaps,
            },
        )
        try:
            await self.print(
                Msg(
                    self.name,
                    "Reflect on the failure of the action",
                    "assistant"
                ),
            )
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
                # save the current reflect msg
                msgs = await self.memory.get_memory()
                save_msg = None
                for msg in reversed(msgs):
                    for i, block in enumerate(
                        msg.get_content_blocks("tool_use")
                    ):
                        if block.get("name") == "reflect_failure":
                            save_msg = msg
                            # ensure only one tool call
                            save_msg.content = [msg.content[i]]
                            break
                    if save_msg is not None:
                        break

                intermediate_report = (
                    await self.summarize_intermediate_results()
                )

                # add the tool call back to memory
                await self.memory.add(save_msg)

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

    async def finish_current_subtask(
        self,
    ):
        """
        When all items of the current subtask are marked as done,
        use this tool to remove the subtask and proceed to the next one.
        """
        if len(self.current_subtask) > 1:
            completed_subtask = self.current_subtask.pop()
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
                    "success": False,  # do not allow to exit
                },
                is_last=True,
            )
        else:
            ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="All subtasks are done. "
                             "Consider using generate_response to"
                             "generate final report",
                    ),
                ],
                metadata={
                    "success": False,  # do not allow to exit
                },
                is_last=True,
            )


    # pylint: disable=invalid-overridden-method, unused-argument
    async def generate_response(  #
        self,
        response: str,
        **_kwargs: Any,
    ) -> ToolResponse:
        """Use this function when there is no existing subtasks.
         generate_response will also generate a detailed report
         as a final deep research report.


        Args:
            response (str): A brief summary of the current situation.
        """
        checklist = self.current_subtask[0].knowledge_gaps
        completed_subtask = self.current_subtask.pop()

        if len(self.current_subtask) == 0:
            (
                summarized_content,
                detailed_report_path,
            ) = await self._generate_deepresearch_report(
                checklist=checklist,
            )
            subtask_progress_summary = json.dumps(
                summarized_content.content[0]["output"][0],
                indent=2,
                ensure_ascii=False,
            )
            structure_response = WorkerResponse(
                task_done=True,
                subtask_progress_summary=subtask_progress_summary,
                generated_files={
                    detailed_report_path: (
                        f"Final detailed report generated by {self.name}"
                        f"for '{str(self.user_query)}'"
                    )
                },
            )
            response_msg = Msg(
                name=self.name,
                role="assistant",
                content=[
                    TextBlock(type="text",
                              text=subtask_progress_summary,)
                ],
                metadata=structure_response.model_dump(),
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
                    "success": False,  # do not allow to exit
                },
                is_last=True,
            )