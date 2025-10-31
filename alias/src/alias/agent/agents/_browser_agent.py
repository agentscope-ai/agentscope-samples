# -*- coding: utf-8 -*-
"""Browser Agent"""
# flake8: noqa: E501
# pylint: disable=W0212
# pylint: disable=too-many-lines
# pylint: disable=C0301
import re
import uuid
import os
import json
from typing import Type, Optional, Any
import asyncio
import copy
from loguru import logger
from pydantic import BaseModel

from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase
from agentscope.message import (
    Msg,
    ToolUseBlock,
    TextBlock,
    ToolResultBlock,
    ImageBlock,
)
from agentscope.model import ChatModelBase
from agentscope.tool import (
    ToolResponse,
)
from agentscope.token import TokenCounterBase, OpenAITokenCounter

from alias.agent.agents import AliasAgentBase
from alias.agent.agents._planning_tools._planning_notebook import (
    WorkerResponse,
)
from alias.agent.utils.constants import (
    DEFAULT_BROWSER_WORKER_NAME,
)
from alias.agent.tools import AliasToolkit

# Get the directory of the current file
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(
    os.path.join(
        _CURRENT_DIR,
        "_build_in_prompt_browser/browser_agent_sys_prompt.md",
    ),
    "r",
    encoding="utf-8",
) as f:
    _BROWSER_AGENT_DEFAULT_SYS_PROMPT = f.read()
with open(
    os.path.join(
        _CURRENT_DIR,
        "_build_in_prompt_browser/browser_agent_pure_reasoning_prompt.md",
    ),
    "r",
    encoding="utf-8",
) as f:
    _BROWSER_AGENT_DEFAULT_PURE_REASONING_PROMPT = f.read()
with open(
    os.path.join(
        _CURRENT_DIR,
        "_build_in_prompt_browser/browser_agent_observe_reasoning_prompt.md",
    ),
    "r",
    encoding="utf-8",
) as f:
    _BROWSER_AGENT_DEFAULT_OBSERVE_REASONING_PROMPT = f.read()
with open(
    os.path.join(
        _CURRENT_DIR,
        "_build_in_prompt_browser/browser_agent_task_decomposition_prompt.md",
    ),
    "r",
    encoding="utf-8",
) as f:
    _BROWSER_AGENT_DEFAULT_TASK_DECOMPOSITION_PROMPT = f.read()
with open(
    os.path.join(
        _CURRENT_DIR,
        "_build_in_prompt_browser/browser_agent_summarize_task.md",
    ),
    "r",
    encoding="utf-8",
) as f:
    _BROWSER_AGENT_SUMMARIZE_TASK_PROMPT = f.read()


class BrowserAgent(AliasAgentBase):
    """
    Browser Agent that extends AliasAgentBase with browser-specific capabilities.

    The agent leverages MCP (Model Context Protocol) servers to access browser
    tools with Playwright, enabling sophisticated web automation tasks.

    Example:
        .. code-block:: python

            agent = BrowserAgent(
                name="web_navigator",
                model=my_chat_model,
                formatter=my_formatter,
                memory=my_memory,
                toolkit=browser_toolkit,
                start_url="https://example.com"
            )

            response = await agent.reply("Search for Python tutorials")
    """

    def __init__(
        self,
        model: ChatModelBase,
        formatter: FormatterBase,
        memory: MemoryBase,
        toolkit: AliasToolkit,
        sys_prompt: str = _BROWSER_AGENT_DEFAULT_SYS_PROMPT,
        max_iters: int = 50,
        start_url: Optional[str] = "https://www.google.com",
        pure_reasoning_prompt: str = _BROWSER_AGENT_DEFAULT_PURE_REASONING_PROMPT,
        observe_reasoning_prompt: str = _BROWSER_AGENT_DEFAULT_OBSERVE_REASONING_PROMPT,
        task_decomposition_prompt: str = (
            _BROWSER_AGENT_DEFAULT_TASK_DECOMPOSITION_PROMPT
        ),
        token_counter: TokenCounterBase = OpenAITokenCounter("gpt-4o"),
        max_mem_length: int = 20,
        session_service: Any = None,
        state_saving_dir: Optional[str] = None,
    ) -> None:
        """Initialize the Browser Agent.

        Args:
            model (ChatModelBase):
                The chat model used for generating responses and reasoning.
            formatter (FormatterBase):
                The formatter used to convert messages into the required format
                 for the model API.
            memory (MemoryBase):
                The memory component used to store and retrieve dialogue
                history.
            toolkit (Toolkit):
                A toolkit object containing the browser tool functions and
                utilities.
            sys_prompt (str, optional):
                The system prompt that defines the agent's behavior and
                personality.
                Defaults to _BROWSER_AGENT_DEFAULT_SYS_PROMPT.
            max_iters (int, optional):
                The maximum number of reasoning-acting loop iterations.
                Defaults to 50.
            start_url (Optional[str], optional):
                The initial URL to navigate to when the agent starts.
                Defaults to "https://www.google.com".

        Returns:
            None
        """
        self.start_url = start_url
        self._has_initial_navigated = False
        self.pure_reasoning_prompt = pure_reasoning_prompt
        self.observe_reasoning_prompt = observe_reasoning_prompt
        self.task_decomposition_prompt = task_decomposition_prompt
        self.max_memory_length = max_mem_length
        self.token_estimator = token_counter
        self.snapshot_chunk_id = 0
        self.chunk_continue_status = False
        self.previous_chunkwise_information = ""
        self.snapshot_in_chunk = []
        self.subtasks = []
        self.original_task = ""
        self.current_subtask_idx = 0
        self.current_subtask = None
        self.iter_n = 0
        self.finish_function_name = "browser_generate_final_response"
        self.init_query = ""
        self._required_structured_model: Type[BaseModel] | None = None
        sys_prompt = sys_prompt.format(name=DEFAULT_BROWSER_WORKER_NAME)
        super().__init__(
            name=DEFAULT_BROWSER_WORKER_NAME,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            memory=memory,
            toolkit=toolkit,
            max_iters=max_iters,
            session_service=session_service,
            state_saving_dir=state_saving_dir,
        )

        self.toolkit.register_tool_function(self.browser_subtask_manager)
        self.toolkit.register_tool_function(self.image_understanding)

        self.no_screenshot_tool_list = [
            tool
            for tool in self.toolkit.get_json_schemas()
            if tool.get("function", {}).get("name")
            not in ["browser_take_screenshot"]
        ]

    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
        structured_model: Type[BaseModel] | None = None,
    ) -> Msg:
        """
        Process a message and return a response.

        Args:
            msg (`Msg | list[Msg] | None`, optional):
                The input message(s) to the agent.
            structured_model (`Type[BaseModel] | None`, optional):
                The required structured output model. If provided, the agent
                is expected to generate structured output in the `metadata`
                field of the output message.

        Returns:
            Msg: The response message.
        """
        self.init_query = (
            msg.content
            if isinstance(msg, Msg)
            else msg[0].content
            if isinstance(msg, list)
            else ""
        )

        if self.start_url and not self._has_initial_navigated:
            await self._navigate_to_start_url()
            self._has_initial_navigated = True
        msg = await self._task_decomposition_and_reformat(msg)
        # original reply function
        await self.memory.add(msg)
        self._required_structured_model = structured_model
        # Record structured output model if provided
        if structured_model:
            self.toolkit.set_extended_model(
                self.finish_function_name,
                structured_model,
            )
        # The reasoning-acting loop
        reply_msg = None
        for iter_n in range(self.max_iters):
            self.iter_n = iter_n + 1
            await self._summarize_mem()

            msg_reasoning = await self._pure_reasoning()
            tool_calls = msg_reasoning.get_content_blocks("tool_use")
            if tool_calls and tool_calls[0]["name"] == "browser_snapshot":
                msg_reasoning = await self._reasoning_with_observation()

            futures = [
                self._acting(tool_call)
                for tool_call in msg_reasoning.get_content_blocks(
                    "tool_use",
                )
            ]

            # Parallel tool calls or not
            if self.parallel_tool_calls:
                acting_responses = await asyncio.gather(*futures)

            else:
                # Sequential tool calls
                acting_responses = [await _ for _ in futures]

            # Find the first non-None replying message from the acting
            for acting_msg in acting_responses:
                reply_msg = reply_msg or acting_msg

            if reply_msg:
                break
        # When the maximum iterations are reached
        if not reply_msg:
            await self._summarizing()

        await self.memory.add(reply_msg)
        return reply_msg

    async def _pure_reasoning(
        self,
    ):
        msg = Msg(
            "user",
            content=self.pure_reasoning_prompt.format(
                current_subtask=self.current_subtask,
                init_query=self.original_task,
            ),
            role="user",
        )

        prompt = await self.formatter.format(
            msgs=[
                Msg("system", self.sys_prompt, "system"),
                *await self.memory.get_memory(),
                msg,
            ],
        )

        res = await self.model(
            prompt,
            tools=self.no_screenshot_tool_list,
        )
        # handle output from the model
        interrupted_by_user = False
        msg = None
        try:
            if self.model.stream:
                msg = Msg(self.name, [], "assistant")
                async for content_chunk in res:
                    msg.content = content_chunk.content
                await self.print(msg, False)
            else:
                msg = Msg(self.name, list(res.content), "assistant")
                await self.print(msg)
            return msg

        except asyncio.CancelledError as e:
            interrupted_by_user = True
            raise e from None

        finally:
            await self.memory.add(msg)
            tool_use_blocks: list = (
                msg.get_content_blocks(  # pylint: disable=E1133
                    "tool_use",
                )
            )

            # Post-process for user interruption
            if interrupted_by_user and msg:
                # Fake tool results
                tool_use_blocks: list = (
                    msg.get_content_blocks(  # pylint: disable=E1133
                        "tool_use",
                    )
                )
                for tool_call in tool_use_blocks:  # pylint: disable=E1133
                    msg_res = Msg(
                        "system",
                        [
                            ToolResultBlock(
                                type="tool_result",
                                id=tool_call["id"],
                                name=tool_call["name"],
                                output="The tool call has been interrupted "
                                "by the user.",
                            ),
                        ],
                        "system",
                    )

                    await self.memory.add(msg_res)
                    await self.print(msg_res, True)

    async def _reasoning_with_observation(
        self,
    ) -> Msg:
        """Perform the reasoning process."""
        self.snapshot_chunk_id = 0
        self.chunk_continue_status = False
        self.previous_chunkwise_information = ""
        self.snapshot_in_chunk = []

        mem_len = await self.memory.size()
        await self.memory.delete(mem_len - 1)

        self.snapshot_in_chunk = await self._get_snapshot_in_text()

        for _ in self.snapshot_in_chunk:
            observe_msg = await self._build_observation()
            prompt = await self.formatter.format(
                msgs=[
                    Msg("system", self.sys_prompt, "system"),
                    *await self.memory.get_memory(),
                    observe_msg,
                ],
            )

            res = await self.model(
                prompt,
                # tools=self.toolkit.get_json_schemas(),
                tools=self.no_screenshot_tool_list,
            )
            # handle output from the model
            interrupted_by_user = False
            msg = None
            try:
                if self.model.stream:
                    msg = Msg(self.name, [], "assistant")
                    async for content_chunk in res:
                        msg.content = content_chunk.content
                    await self.print(msg)
                else:
                    msg = Msg(self.name, list(res.content), "assistant")
                    await self.print(msg)

            except asyncio.CancelledError as e:
                interrupted_by_user = True
                raise e from None

            tool_use_blocks: list = (
                msg.get_content_blocks(  # pylint: disable=E1133
                    "tool_use",
                )
            )

            await self._update_chunk_observation_status(
                output_msg=msg,
            )
            # Post-process for user interruption
            if interrupted_by_user and msg:
                # Fake tool results
                for tool_call in tool_use_blocks:  # pylint: disable=E1133
                    msg_res = Msg(
                        "system",
                        [
                            ToolResultBlock(
                                type="tool_result",
                                id=tool_call["id"],
                                name=tool_call["name"],
                                output="The tool call has been interrupted "
                                "by the user.",
                            ),
                        ],
                        "system",
                    )

                    await self.memory.add(msg_res)
                    await self.print(msg_res, True)
            if not self.chunk_continue_status:
                break

        await self.memory.add(msg)
        return msg

    async def _summarize_mem(
        self,
    ) -> None:
        """Summarize memory if too long"""
        mem_len = await self.memory.size()
        if mem_len > self.max_memory_length:
            await self._memory_summarizing()

    async def _build_observation(
        self,
    ) -> Msg:
        """Get a snapshot in text before reasoning"""
        image_data: Optional[str] = None
        if (
            self.model.model_name.startswith("qvq")
            or "-vl" in self.model.model_name
            or "4o" in self.model.model_name
            or "gpt-5" in self.model.model_name
        ):
            # If the model supports multimodal input, take a screenshot
            # and pass it to the observation message as base64
            image_data = await self._get_screenshot()

        observe_msg = self.observe_by_chunk(image_data)
        return observe_msg

    async def _update_chunk_observation_status(
        self,
        output_msg: Msg | None = None,
    ) -> None:
        """Update the chunk observation status after reasoning."""

        for _, b in enumerate(output_msg.content):
            if b["type"] == "text":
                # obtain response content
                raw_response = b["text"]
                # parse the response content to check if
                # it contains "REASONING_FINISHED"
                try:
                    if "```json" in raw_response:
                        raw_response = raw_response.replace(
                            "```json",
                            "",
                        ).replace("```", "")
                    data = json.loads(raw_response)
                    information = data.get("INFORMATION", "")
                    self.chunk_continue_status = data.get("STATUS", "CONTINUE")
                except Exception:
                    information = raw_response
                    if (
                        self.snapshot_chunk_id
                        < len(self.snapshot_in_chunk) - 1
                    ):
                        self.chunk_continue_status = True
                        self.snapshot_chunk_id += 1
                    else:
                        self.chunk_continue_status = False

                if not isinstance(information, str):
                    try:
                        information = json.dumps(
                            information,
                            ensure_ascii=False,
                        )
                    except Exception:
                        information = str(information)

                self.previous_chunkwise_information += (
                    f"Information in chunk {self.snapshot_chunk_id+1} "
                    f"of {len(self.snapshot_in_chunk)}:\n" + information + "\n"
                )

            if b["type"] == "tool_use":
                self.chunk_continue_status = False

    async def _acting(self, tool_call: ToolUseBlock) -> Msg | None:
        """Perform the acting process.

        Args:
            tool_call (`ToolUseBlock`):
                The tool use block to be executed.

        Returns:
            `Union[Msg, None]`:
                Return a message to the user if the `_finish_function` is
                called, otherwise return `None`.
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
        try:
            # Execute the tool call
            tool_res = await self.toolkit.call_tool_function(tool_call)

            response_msg = None
            # Async generator handling
            async for chunk in tool_res:
                # Turn into a tool result block
                tool_res_msg.content[0][  # type: ignore[index]
                    "output"
                ] = chunk.content
                # Return message if generate_response is called successfully
                if tool_call[
                    "name"
                ] == self.finish_function_name and chunk.metadata.get(
                    "success",
                    True,
                ):
                    response_msg = chunk.metadata.get("response_msg")
                elif chunk.is_interrupted:
                    # TODO: monkey patch happens here
                    response_msg = tool_res_msg
                    if response_msg.metadata is None:
                        response_msg.metadata = {"is_interrupted": True}
                    else:
                        response_msg.metadata["is_interrupted"] = True
            return response_msg

        finally:
            # Record the tool result message in the memory
            tool_res_msg = self._clean_tool_excution_content(tool_res_msg)
            if tool_call["name"] == "browser_subtask_manager":
                # remove the last tool call
                mem_len = await self.memory.size()
                if mem_len >= 1:
                    await self.memory.delete(mem_len - 1)
            else:
                await self.memory.add(tool_res_msg)
            await self.print(tool_res_msg, False)

    def _clean_tool_excution_content(
        self,
        output_msg: Msg,
    ) -> Msg:
        """
        Hook func for cleaning the messy return after action.
        Observation will be done before reasoning steps.
        """

        for i, b in enumerate(output_msg.content):
            if b["type"] == "tool_result":
                for j, return_json in enumerate(b.get("output", [])):
                    if isinstance(return_json, dict) and "text" in return_json:
                        output_msg.content[i]["output"][j][
                            "text"
                        ] = self._filter_execution_text(return_json["text"])
        return output_msg

    async def _task_decomposition_and_reformat(  # pylint: disable=too-many-statements
        self,
        original_task: Msg | list[Msg] | None,
    ) -> Msg:
        """
        Decompose the original task into smaller tasks and reformat it, with reflection.
        """
        if isinstance(original_task, list):
            original_task = original_task[0]

        prompt = await self.formatter.format(
            msgs=[
                Msg(
                    name="user",
                    content=self.task_decomposition_prompt.format(
                        start_url=self.start_url,
                        browser_agent_sys_prompt=self.sys_prompt,
                        original_task=original_task.content,
                    ),
                    role="user",
                ),
            ],
        )
        res = await self.model(prompt)
        decompose_text = ""
        print_msg = Msg(name=self.name, content=[], role="assistant")
        if self.model.stream:
            async for content_chunk in res:
                decompose_text = content_chunk.content[0]["text"]
                print_msg.content = content_chunk.content
                await self.print(print_msg, last=False)
        else:
            decompose_text = res.content[0]["text"]
        print_msg.content = [TextBlock(type="text", text=decompose_text)]
        await self.print(print_msg, last=True)

        # Use path relative to this file for robustness
        reflection_prompt_path = os.path.join(
            _CURRENT_DIR,
            "_build_in_prompt_browser/browser_agent_decompose_reflection_prompt.md",
        )
        with open(reflection_prompt_path, "r", encoding="utf-8") as fj:
            decompose_reflection_prompt = fj.read()

        reflection_prompt = await self.formatter.format(
            msgs=[
                Msg(
                    name="user",
                    content=self.task_decomposition_prompt.format(
                        start_url=self.start_url,
                        browser_agent_sys_prompt=self.sys_prompt,
                        original_task=original_task.content,
                    ),
                    role="user",
                ),
                Msg(
                    name="system",
                    content=decompose_text,
                    role="system",
                ),
                Msg(
                    name="user",
                    content=decompose_reflection_prompt.format(
                        original_task=original_task.content,
                        subtasks=decompose_text,
                    ),
                    role="user",
                ),
            ],
        )
        reflection_res = await self.model(reflection_prompt)
        reflection_text = ""
        print_msg = Msg(name=self.name, content=[], role="assistant")
        if self.model.stream:
            async for content_chunk in reflection_res:
                reflection_text = content_chunk.content[0]["text"]
                print_msg.content = content_chunk.content
                await self.print(print_msg, last=False)
        else:
            reflection_text = reflection_res.content[0]["text"]
        print_msg.content = [TextBlock(type="text", text=reflection_text)]
        await self.print(print_msg, last=True)

        subtasks = []
        try:
            if "```json" in reflection_text:
                reflection_text = reflection_text.replace("```json", "")
                reflection_text = reflection_text.replace("```", "")
            subtasks_json = json.loads(reflection_text)
            subtasks = subtasks_json.get("REVISED_SUBTASKS", [])
            if not isinstance(subtasks, list):
                subtasks = []
        except Exception:
            subtasks = [original_task.content]

        self.subtasks = subtasks
        self.current_subtask_idx = 0
        self.current_subtask = self.subtasks[0] if self.subtasks else None
        self.original_task = original_task.content

        formatted_task = "The original task is: " + self.original_task + "\n"
        try:
            formatted_task += (
                "The decomposed subtasks are: "
                + json.dumps(self.subtasks)
                + "\n"
            )
            formatted_task += (
                "use the decomposed subtasks to complete the original task.\n"
            )
        except Exception:
            pass
        formatted_task = Msg(
            name=original_task.name,
            content=formatted_task,
            role=original_task.role,
        )
        logger.info(f"The formatted task is: \n{formatted_task.content}")
        return formatted_task

    async def _navigate_to_start_url(self) -> None:
        """
        Navigate to the specified start URL using the browser_navigate tool.

        This method is automatically called during the first interaction to
        navigate to the configured start URL. It executes the browser
        navigation tool and processes the response to ensure the
        initial page is loaded.

        Returns:
            None
        """

        tool_call = ToolUseBlock(
            id=str(uuid.uuid4()),  # 添加唯一的 ID
            name="browser_tabs",
            input={"action": "list"},
            type="tool_use",
        )
        response = await self.toolkit.call_tool_function(tool_call)
        response_text = ""
        async for chunk in response:
            response_text = chunk.content[0]["text"]

        tab_numbers = re.findall(r"- (\d+):", response_text)
        # Close all tabs except the first one
        for _ in tab_numbers[1:]:
            tool_call = ToolUseBlock(
                id=str(uuid.uuid4()),
                name="browser_tabs",
                input={"action": "close", "index": 0},
                type="tool_use",
            )
            response = await self.toolkit.call_tool_function(tool_call)
            async for chunk in response:
                response_text = chunk.content
        tool_call = ToolUseBlock(
            id=str(uuid.uuid4()),
            type="tool_use",
            name="browser_navigate",
            input={"url": self.start_url},
        )

        # Execute the navigation tool
        await self.toolkit.call_tool_function(tool_call)

    async def _get_snapshot_in_text(self) -> list:
        """Capture a text-based snapshot of the current webpage content.

        This method uses the browser_snapshot tool to retrieve the current
        webpage content in text format, which is used during the reasoning
        phase to provide context about the current browser state.

        Returns:
            list: A list of text chunks representing the current,
            webpage content, including elements, structure,
            and visible text.

        Note:
            This method is called automatically during the reasoning phase and
            provides essential context for decision-making about next actions.
        """
        snapshot_tool_call = ToolUseBlock(
            type="tool_use",
            id=str(uuid.uuid4()),  # Generate a unique ID for the tool call
            name="browser_snapshot",
            input={},  # No parameters required for this tool
        )
        snapshot_response = await self.toolkit.call_tool_function(
            snapshot_tool_call,
        )
        snapshot_str = ""
        async for chunk in snapshot_response:
            snapshot_str = chunk.content[0]["text"]
        snapshot_in_chunk = self._split_snapshot_by_chunk(
            snapshot_str,
        )

        return snapshot_in_chunk

    async def _memory_summarizing(self) -> None:
        """Summarize the current memory content to prevent context overflow.

        This method is called periodically to condense the conversation history
        by generating a summary of progress and maintaining only essential
        information. It preserves the initial user question and creates a
        concise summary of what has been accomplished and what remains to be
        done.

        Returns:
            None

        Note:
            This method is automatically called every 10 iterations to manage
            memory usage and maintain context relevance. The summarization
            helps prevent token limit issues while preserving important task
            context.
        """
        # Extract the initial user question
        initial_question = None
        memory_msgs = await self.memory.get_memory()
        for msg in memory_msgs:
            if msg.role == "user":
                initial_question = msg.content
                break

        # Generate a summary of the current progress
        hint_msg = Msg(
            "user",
            (
                "Summarize the current progress and outline the next steps "
                "for this task. Your summary should include:\n"
                "1. What has been completed so far.\n"
                "2. What key information has been found.\n"
                "3. What remains to be done.\n"
                "Ensure that your summary is clear, concise, and t"
                "hat no tasks are repeated or skipped."
            ),
            role="user",
        )

        # Format the prompt for the model
        prompt = await self.formatter.format(
            msgs=[
                Msg("system", self.sys_prompt, "system"),
                *memory_msgs,
                hint_msg,
            ],
        )

        # Call the model to generate the summary
        res = await self.model(prompt)

        # Handle response
        summary_text = ""
        print_msg = Msg(name=self.name, content=[], role="assistant")
        if self.model.stream:
            async for content_chunk in res:
                summary_text = content_chunk.content[0]["text"]
                print_msg.content = content_chunk.content
                await self.print(print_msg, last=False)
        else:
            summary_text = res.content[0]["text"]
        print_msg.content = [TextBlock(type="text", text=summary_text)]
        await self.print(print_msg, last=True)

        # Update the memory with the summarized content
        summarized_memory = []
        if initial_question:
            summarized_memory.append(
                Msg("user", initial_question, role="user"),
            )
        summarized_memory.append(
            Msg(self.name, summary_text, role="assistant"),
        )

        # Clear and reload memory
        await self.memory.clear()
        for msg in summarized_memory:
            await self.memory.add(msg)

    async def _get_screenshot(self) -> Optional[str]:
        """
        Optionally take a screenshot of the current web page for multimodal prompts.
        Returns base64-encoded PNG data if available, else None.
        """
        try:
            # Prepare tool call for screenshot
            tool_call = ToolUseBlock(
                id=str(uuid.uuid4()),
                name="browser_take_screenshot",
                input={},
                type="tool_use",
            )
            # Execute tool call via service toolkit
            screenshot_response = await self.toolkit.call_tool_function(
                tool_call,
            )
            # Extract image base64 from response
            async for chunk in screenshot_response:
                if (
                    chunk.content
                    and len(chunk.content) > 1
                    and "data" in chunk.content[1]
                ):
                    image_data = chunk.content[1]["data"]
                else:
                    image_data = None

        except Exception:
            image_data = None
        return image_data

    @staticmethod
    def _filter_execution_text(
        text: str,
        keep_page_state: bool = False,
    ) -> str:
        """
        Filter and clean browser tool execution output to remove verbose
        content.

        This utility method removes unnecessary verbose content from browser
        tool responses, including JavaScript code blocks, console messages,
        and YAML content that can overwhelm the context window without
        providing useful information.

        Args:
            text (str):
                The raw execution text from browser tools that
                needs to be filtered.
            keep_page_state (bool, optional):
                Whether to preserve page state information
                including URL and YAML content. Defaults to False.

        Returns:
            str: The filtered execution text.
        """
        if not keep_page_state:
            # Remove Page Snapshot and YAML content
            text = re.sub(r"- Page URL.*", "", text, flags=re.DOTALL)
            text = re.sub(r"```yaml.*?```", "", text, flags=re.DOTALL)
        # # Remove JavaScript code blocks

        # Remove console messages section that can be very verbose
        # (between "### New console messages" and "### Page state")
        text = re.sub(
            r"### New console messages.*?(?=### Page state)",
            "",
            text,
            flags=re.DOTALL,
        )
        # Trim leading/trailing whitespace
        return text.strip()

    def _split_snapshot_by_chunk(
        self,
        snapshot_str: str,
        max_length: int = 80000,
    ) -> list[str]:
        self.snapshot_chunk_id = 0
        return [
            snapshot_str[i : i + max_length]
            for i in range(0, len(snapshot_str), max_length)
        ]

    def observe_by_chunk(self, image_data: str | None = "") -> Msg:
        """Create an observation message for chunk-based reasoning.

        This method formats the current chunk of the webpage snapshot with
        contextual information from previous chunks to create a structured
        observation message for the reasoning phase.

        Returns:
            Msg: A user message containing the formatted reasoning prompt
                with chunk information and context from previous chunks.
        """
        reasoning_prompt = self.observe_reasoning_prompt.format(
            previous_chunkwise_information=self.previous_chunkwise_information,
            current_subtask=self.current_subtask,
            i=self.snapshot_chunk_id + 1,
            total_pages=len(self.snapshot_in_chunk),
            chunk=self.snapshot_in_chunk[self.snapshot_chunk_id],
            init_query=self.original_task,
        )
        content = [
            TextBlock(
                type="text",
                text=reasoning_prompt,
            ),
        ]
        if (
            self.model.model_name.startswith("qvq")
            or "-vl" in self.model.model_name
            or "4o" in self.model.model_name
            or "gpt-5" in self.model.model_name
        ):
            if image_data:
                image_block = ImageBlock(
                    type="image",
                    source={
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                )
                content.append(image_block)

        observe_msg = Msg(
            "user",
            content=content,
            role="user",
        )
        return observe_msg

    async def browser_subtask_manager(  # pylint: disable=too-many-branches,too-many-statements
        self,
    ) -> ToolResponse:
        """
        Determine whether the current subtask is completed.
        This tool should only be used when it is believed that
         the current subtask is done.

        Returns:
            `ToolResponse`:
                If completed, advance current_subtask_idx;
                otherwise, leave it unchanged.
        """
        if (
            not hasattr(self, "subtasks")
            or not self.subtasks
            or self.current_subtask is None
        ):
            self.current_subtask = self.original_task
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            f"Tool call Error. Cannot be executed. "
                            f"Current subtask remains: {self.current_subtask}"
                        ),
                    ),
                ],
            )

        # take memory as context
        memory_content = await self.memory.get_memory()

        # LLM prompt for subtask validation
        sys_prompt = (
            "You are an expert in subtask validation. \n"
            "Given the following subtask and the agent's"
            " recent memory, strictly judge if the subtask "
            "is FULLY completed. \n"
            "If yes, reply ONLY 'SUBTASK_COMPLETED'. "
            "If not, reply ONLY 'SUBTASK_NOT_COMPLETED'."
        )
        if len(self.snapshot_in_chunk) > 0:
            user_prompt = (
                f"Subtask: {self.current_subtask}\n"
                f"Recent memory:\n{[str(m) for m in memory_content[-10:]]}\n"
                f"Current page:\n{self.snapshot_in_chunk[0]}"
            )
        else:
            user_prompt = (
                f"Subtask: {self.current_subtask}\n"
                f"Recent memory:\n{[str(m) for m in memory_content[-10:]]}\n"
            )
        prompt = await self.formatter.format(
            msgs=[
                Msg("system", sys_prompt, role="system"),
                Msg("user", user_prompt, role="user"),
            ],
        )

        response = await self.model(prompt)
        response_text = ""
        print_msg = Msg(name=self.name, content=[], role="assistant")
        if self.model.stream:
            # If the model supports streaming, collect chunks
            async for chunk in response:
                response_text += chunk.content[0]["text"]
                print_msg.content = chunk.content
                await self.print(print_msg, last=False)
        else:
            # If not streaming, get the full response at once
            response_text = response.content[0]["text"]

        print_msg.content = [TextBlock(type="text", text=response_text)]
        await self.print(print_msg, last=True)

        if "SUBTASK_COMPLETED" in response_text.strip().upper():
            self.current_subtask_idx += 1
            if self.current_subtask_idx < len(self.subtasks):
                self.current_subtask = str(
                    self.subtasks[self.current_subtask_idx],
                )
            else:
                self.current_subtask = None
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "Tool call SUCCESS."
                            " Current subtask updates to: "
                            f"{self.current_subtask}"
                        ),
                    ),
                ],
            )
        else:
            revise_prompt_path = os.path.join(
                _CURRENT_DIR,
                "_build_in_prompt_browser/browser_agent_subtask_revise_prompt.md",
            )
            with open(revise_prompt_path, "r", encoding="utf-8") as fr:
                revise_prompt = fr.read()
            memory_content = await self.memory.get_memory()
            user_prompt = revise_prompt.format(
                memory=[str(m) for m in memory_content[-10:]],
                subtasks=json.dumps(self.subtasks, ensure_ascii=False),
                current_subtask=str(self.current_subtask),
                original_task=str(self.original_task),
            )
            prompt = await self.formatter.format(
                msgs=[
                    Msg("user", user_prompt, role="user"),
                ],
            )
            response = await self.model(prompt)
            if self.model.stream:
                async for chunk in response:
                    revise_text = chunk.content[0]["text"]
            else:
                revise_text = response.content[0]["text"]
            try:
                if "```json" in revise_text:
                    revise_text = revise_text.replace("```json", "").replace(
                        "```",
                        "",
                    )
                revise_json = json.loads(revise_text)
                if_revised = revise_json.get("IF_REVISED")
                if if_revised:
                    revised_subtasks = revise_json.get("REVISED_SUBTASKS", [])
                    if isinstance(revised_subtasks, list) and revised_subtasks:
                        self.subtasks = revised_subtasks
                        self.current_subtask_idx = 0
                        self.current_subtask = self.subtasks[0]
                        logger.info(
                            f"Subtasks revised: {self.subtasks}, reason: {revise_json.get('REASON', '')}",
                        )
            except Exception as e:
                logger.warning(f"Failed to revise subtasks: {e}")
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Tool call SUCCESS."
                        f" Current subtask remains: {self.current_subtask}"
                    ),
                ),
            ],
        )

    async def browser_generate_final_response(
        self,  # pylint: disable=W0613
        **kwargs: Any,  # pylint: disable=W0613
    ) -> ToolResponse:
        """Generate a response when the agent has completed all subtasks."""
        hint_msg = Msg(
            "user",
            _BROWSER_AGENT_SUMMARIZE_TASK_PROMPT,
            role="user",
        )
        memory_msgs = await self.memory.get_memory()
        memory_msgs_copy = copy.deepcopy(memory_msgs)
        last_msg = memory_msgs_copy[-1]
        # check if the last message has tool call, if so clean the content

        last_msg.content = last_msg.get_content_blocks("text")
        memory_msgs_copy[-1] = last_msg

        # Generate a reply by summarizing the current situation
        prompt = await self.formatter.format(
            msgs=[
                Msg("system", self.sys_prompt, "system"),
                *memory_msgs_copy,
                hint_msg,
            ],
        )
        try:
            res = await self.model(prompt)
            res_msg = Msg(
                "assistant",
                [],
                "assistant",
            )
            if self.model.stream:
                async for content_chunk in res:
                    summary_text = content_chunk.content[0]["text"]
            else:
                summary_text = res.content[0]["text"]

            res_msg.content = summary_text
            await self.print(res_msg, False)
            # Validate finish status
            finish_status = await self._validate_finish_status(summary_text)
            logger.info(f"Finish status: {finish_status}")

            if "BROWSER_AGENT_TASK_FINISHED" in finish_status:
                structure_response = WorkerResponse(
                    task_done=True,
                    subtask_progress_summary=summary_text,
                    generated_files={},
                )

                response_msg = Msg(
                    self.name,
                    content=[
                        TextBlock(type="text", text=summary_text),
                    ],
                    role="assistant",
                    metadata=structure_response.model_dump(),
                )
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="Successfully generated response.",
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
                            text=f"Here is a summary of current status:\n{summary_text}\nPlease continue.\n Following steps \n {finish_status}",
                        ),
                    ],
                    metadata={"success": False, "response_msg": None},
                    is_last=True,
                )
        except Exception as e:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Tool call Error. Cannot be executed. {e}",
                    ),
                ],
                metadata={"success": False},
                is_last=True,
            )

    async def image_understanding(
        self,
        object_description: str,
        task: str,
    ) -> ToolResponse:
        """
        Find the object on the website that satisfies the description,
        take screenshot with regard to the object, and return the solution to the task.
        For example, solve OCR problems, identify small objects, etc.
        Args:
            object_description (str): Human-readable description of the target element (e.g., 'captcha').
            task (str): The specific task to solve (e.g., 'find the text to fill in the captcha').
        Returns:
            ToolResponse: Contains screenshot and solution to the task.
        """
        # Step 1: Query the model to locate the element and its reference
        sys_prompt = (
            "You are a web page analysis expert. Given the following page snapshot and object description, "
            "identify the exact element and its reference string (ref) that matches the description. "
            'Return ONLY a JSON object: {"element": <element description>, "ref": <ref string>}'
        )
        # Get current page snapshot
        snapshot_chunks = await self._get_snapshot_in_text()
        page_snapshot = snapshot_chunks[0] if snapshot_chunks else ""
        user_prompt = (
            f"Object description: {object_description}\n"
            f"Page snapshot:\n{page_snapshot}"
        )
        prompt = await self.formatter.format(
            msgs=[
                Msg("system", sys_prompt, role="system"),
                Msg("user", user_prompt, role="user"),
            ],
        )
        res = await self.model(prompt)
        if self.model.stream:
            async for chunk in res:
                model_text = chunk.content[0]["text"]
        else:
            model_text = res.content[0]["text"]
        # Parse model output for element/ref
        try:
            if "```json" in model_text:
                model_text = model_text.replace("```json", "").replace(
                    "```",
                    "",
                )
            element_info = json.loads(model_text)
            element = element_info.get("element", "")
            ref = element_info.get("ref", "")
        except Exception:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Failed to parse element/ref from model output.",
                    ),
                ],
                metadata={"success": False},
            )

        # Step 2: Take screenshot of the element
        screenshot_tool_call = ToolUseBlock(
            id=str(uuid.uuid4()),
            name="browser_take_screenshot",
            input={"element": element, "ref": ref},
            type="tool_use",
        )
        screenshot_response = await self.toolkit.call_tool_function(
            screenshot_tool_call,
        )
        image_data = None
        async for chunk in screenshot_response:
            if (
                chunk.content
                and len(chunk.content) > 1
                and "data" in chunk.content[1]
            ):
                image_data = chunk.content[1]["data"]

        # Step 3: Query the model to solve the task using the screenshot and context
        sys_prompt_task = (
            "You are a web automation expert. Given the object description, screenshot, and page context, "
            "solve the following task. Return ONLY the answer as plain text."
        )
        # Prepare content blocks for multimodal input
        content_blocks = [
            TextBlock(
                type="text",
                text=f"Object description: {object_description}\nTask: {task}\nPage snapshot:\n{page_snapshot}",
            ),
        ]
        # Attach screenshot if available

        if image_data:
            image_block = ImageBlock(
                type="image",
                source={
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data,
                },
            )
            content_blocks.append(image_block)

        prompt_task = await self.formatter.format(
            msgs=[
                Msg("system", sys_prompt_task, role="system"),
                Msg("user", content_blocks, role="user"),
            ],
        )
        res_task = await self.model(prompt_task)
        if self.model.stream:
            async for chunk in res_task:
                answer_text = chunk.content[0]["text"]
        else:
            answer_text = res_task.content[0]["text"]

        # Step 4: Return ToolResponse with screenshot and answer
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        f"Screenshot taken for element: {element}\nref: {ref}\n"
                        f"Task solution: {answer_text}"
                    ),
                ),
            ],
        )

    async def _validate_finish_status(self, summary: str) -> str:
        """Validate if the agent has completed its task based on the summary."""
        sys_prompt = (
            "You are an expert in task validation. "
            "Your job is to determine if the agent has completed its task"
            " based on the provided summary. If finished, strictly reply "
            '"BROWSER_AGENT_TASK_FINISHED", otherwise return the remaining '
            "tasks or next steps."
        )
        # Extract user question from memory
        initial_question = None
        memory_msgs = await self.memory.get_memory()
        for msg in memory_msgs:
            if msg.role == "user":
                initial_question = msg.content
                break

        prompt = await self.formatter.format(
            msgs=[
                Msg(
                    "system",
                    sys_prompt,
                    role="system",
                ),
                Msg(
                    "user",
                    content=(
                        "The initial task is to solve the following question: "
                        f"{initial_question} \n "
                        f"Here is a summary of current task "
                        f"completion process, please evaluate the task finish "
                        f"status.\n" + summary
                    ),
                    role="user",
                ),
            ],
        )
        res = await self.model(prompt)
        response_text = ""
        if self.model.stream:
            async for content_chunk in res:
                response_text = content_chunk.content[0]["text"]
        else:
            response_text = res.content[0]["text"]
        return response_text
