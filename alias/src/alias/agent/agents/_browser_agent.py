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
import inspect
from functools import wraps
from typing import Type, Optional, Any, Literal
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
    Base64Source,
)
from agentscope.model import ChatModelBase
from agentscope.tool import (
    ToolResponse,
)
from agentscope.token import TokenCounterBase, OpenAITokenCounter

from alias.agent.agents import AliasAgentBase
from alias.agent.agents.common_agent_utils import (
    WorkerResponse,
    get_user_input_to_mem_pre_reply_hook,
    agent_load_states_pre_reply_hook,
    save_post_reasoning_state,
    save_post_action_state,
)
from alias.agent.agents._build_in_helper_browser._image_understanding import (
    image_understanding,
)
from alias.agent.agents._build_in_helper_browser._video_understanding import (
    video_understanding,
)
from alias.agent.agents._build_in_helper_browser._file_download import (
    file_download,
)
from alias.agent.agents._build_in_helper_browser._form_filling import (
    form_filling,
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


class EmptyModel(BaseModel):
    pass


async def browser_pre_reply_hook(
    self,
    kwargs: dict[str, Any],
):
    """Pre-reply hook: initial navigation and task decomposition.

    Expects kwargs["msg"] to be a Msg. Returns updated kwargs with possibly
    rewritten "msg".
    """
    msg = kwargs.get("msg")
    # for the case directly using session service
    if msg is None:
        msg = (await self.memory.get_memory())[-1]
    if self.start_url and not self._has_initial_navigated:
        await self._navigate_to_start_url()
        self._has_initial_navigated = True
    msg = await self._task_decomposition_and_reformat(msg)
    await self.memory.add(msg)


async def browser_post_acting_hook(
    self,
    kwargs: dict[str, Any],  # pylint: disable=W0613
    output: Any,  # pylint: disable=W0613
):
    """
    Hook func for cleaning the messy return after action.
    Observation will be done before reasoning steps.
    """
    tool_call = kwargs.get("tool_call")
    if tool_call is None:
        return
    mem_msgs = await self.memory.get_memory()
    mem_length = await self.memory.size()
    if len(mem_msgs) == 0:
        return
    tool_res_msg = mem_msgs[-1]
    for i, b in enumerate(tool_res_msg.content):
        if b["type"] == "tool_result":
            for j, return_json in enumerate(b.get("output", [])):
                if isinstance(return_json, dict) and "text" in return_json:
                    tool_res_msg.content[i]["output"][j][
                        "text"
                    ] = self._filter_execution_text(return_json["text"])
    if tool_call["name"] != self.finish_function_name or (
        tool_call["name"] == self.finish_function_name
        and tool_res_msg.metadata
        and not tool_res_msg.metadata.get("success")
    ):
        await self.print(tool_res_msg)
    await self.memory.delete(mem_length - 1)
    await self.memory.add(tool_res_msg)


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
        if self._supports_multimodal():
            self._register_skill_tool(image_understanding)
            self._register_skill_tool(video_understanding)

        self._register_skill_tool(file_download)
        self._register_skill_tool(form_filling)

        self.no_screenshot_tool_list = [
            tool
            for tool in self.toolkit.get_json_schemas()
            if tool.get("function", {}).get("name")
            not in ["browser_take_screenshot"]
        ]

        # Register hooks (kwargs-only signature)
        # compatible with directly using session service,
        # add input msg to memory
        self.register_instance_hook(
            "pre_reply",
            "agent_load_states_pre_reply_hook",
            agent_load_states_pre_reply_hook,
        )
        self.register_instance_hook(
            "pre_reply",
            "get_user_input_to_mem_pre_reply_hook",
            get_user_input_to_mem_pre_reply_hook,
        )
        self.register_instance_hook(
            "pre_reply",
            "browser_pre_reply_hook",
            browser_pre_reply_hook,
        )
        self.register_instance_hook(
            "post_reasoning",
            "save_post_reasoning_state",
            save_post_reasoning_state,
        )
        self.register_instance_hook(
            "post_acting",
            "browser_post_acting_hook",
            browser_post_acting_hook,
        )
        self.register_instance_hook(
            "post_acting",
            "save_post_action_state",
            save_post_action_state,
        )

    def _register_skill_tool(
        self,
        skill_func: Any,
    ) -> None:
        """Bind the browser agent to a skill function and register it as a tool."""

        if asyncio.iscoroutinefunction(skill_func):

            @wraps(skill_func)
            async def tool(*args, **kwargs):
                return await skill_func(
                    browser_agent=self,
                    *args,
                    **kwargs,
                )

        else:

            @wraps(skill_func)
            async def tool(*args, **kwargs):
                return skill_func(
                    browser_agent=self,
                    *args,
                    **kwargs,
                )

        original_signature = inspect.signature(skill_func)
        parameters = list(original_signature.parameters.values())
        if parameters and parameters[0].name == "browser_agent":
            parameters = parameters[1:]
        try:
            tool.__signature__ = original_signature.replace(
                parameters=parameters,
            )
        except ValueError:
            pass
        self.toolkit.register_tool_function(tool)

    def _supports_multimodal(self) -> bool:
        """Check if the model supports multimodal input (images/videos).

        Returns:
            bool: True if the model supports multimodal input, False otherwise.
        """
        return (
            self.model.model_name.startswith("qvq")
            or "-vl" in self.model.model_name
            or "4o" in self.model.model_name
            or "gpt-5" in self.model.model_name
        )

    # pylint: disable=R0912,R0915
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

        if structured_model is None:
            structured_model = EmptyModel

        tool_choice: Literal["auto", "none", "required"] | None = None

        self._required_structured_model = structured_model
        # Record structured output model if provided
        if structured_model:
            # Register generate_response tool only when structured output
            # is required
            if self.finish_function_name not in self.toolkit.tools:
                self.toolkit.register_tool_function(
                    getattr(self, self.finish_function_name),
                )

            self.toolkit.set_extended_model(
                self.finish_function_name,
                structured_model,
            )
            tool_choice = "required"
        else:
            # Remove generate_response tool if no structured output is required
            self.toolkit.remove_tool_function(self.finish_function_name)

        # The reasoning-acting loop
        structured_output = None
        reply_msg = None
        for iter_n in range(self.max_iters):
            self.iter_n = iter_n + 1
            await self._summarize_mem()

            msg_reasoning = await self._pure_reasoning(tool_choice)
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
                structured_outputs = await asyncio.gather(*futures)

            else:
                # Sequential tool calls
                structured_outputs = [await _ for _ in futures]

            # -------------- Check for exit condition --------------
            # If structured output is still not satisfied
            if self._required_structured_model:
                # Remove None results
                structured_outputs = [_ for _ in structured_outputs if _]

                msg_hint = None
                # If the acting step generates structured outputs
                if structured_outputs:
                    # Cache the structured output data
                    structured_output = structured_outputs[-1]

                    reply_msg = Msg(
                        self.name,
                        structured_output.get("subtask_progress_summary", ""),
                        "assistant",
                        metadata=structured_output,
                    )
                    break

                if not msg_reasoning.has_content_blocks("tool_use"):
                    # If structured output is required but no tool call is
                    # made, remind the llm to go on the task
                    msg_hint = Msg(
                        "user",
                        "<system-hint>Structured output is "
                        f"required, go on to finish your task or call "
                        f"'{self.finish_function_name}' to generate the "
                        f"required structured output.</system-hint>",
                        "user",
                    )
                    await self._reasoning_hint_msgs.add(msg_hint)
                    # Require tool call in the next reasoning step
                    tool_choice = "required"

                if msg_hint and self.print_hint_msg:
                    await self.print(msg_hint)

            elif not msg_reasoning.has_content_blocks("tool_use"):
                # Exit the loop when no structured output is required (or
                # already satisfied) and only text response is generated
                msg_reasoning.metadata = structured_output
                reply_msg = msg_reasoning
                break

        # When the maximum iterations are reached
        # and no reply message is generated
        if reply_msg is None:
            reply_msg = await self._summarizing()
            reply_msg.metadata = structured_output
            await self.memory.add(reply_msg)

        return reply_msg

    async def _pure_reasoning(
        self,
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ) -> Msg:
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
                # The hint messages to guide the agent's behavior, maybe empty
                *await self._reasoning_hint_msgs.get_memory(),
            ],
        )

        # Clear the hint messages after use
        await self._reasoning_hint_msgs.clear()

        res = await self.model(
            prompt,
            tools=self.no_screenshot_tool_list,
            tool_choice=tool_choice,
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
                    await self.print(msg_res)

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
                    # await self.print(msg)

                else:
                    msg = Msg(self.name, list(res.content), "assistant")
                    # await self.print(msg)
                logger.info(msg.content)

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
                    await self.print(msg_res)
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
        if self._supports_multimodal():
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
                    self.chunk_continue_status = (
                        data.get("STATUS") != "REASONING_FINISHED"
                    )
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
                # await self.print(print_msg, False)
        else:
            decompose_text = res.content[0]["text"]
        print_msg.content = [TextBlock(type="text", text=decompose_text)]

        # await self.print(print_msg, True)
        logger.info(decompose_text)

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
                # await self.print(print_msg, last=False)
        else:
            reflection_text = reflection_res.content[0]["text"]
        print_msg.content = [TextBlock(type="text", text=reflection_text)]
        # await self.print(print_msg, last=True)
        logger.info(reflection_text)

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
        self.original_task = original_task.get_text_content()

        formatted_task = "The original task is: " + self.original_task + "\n"
        try:
            formatted_task += (
                "The decomposed subtasks are: "
                + json.dumps(self.subtasks, ensure_ascii=False)
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
            id=str(uuid.uuid4()),  # Add the unique ID
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
            await self.toolkit.call_tool_function(tool_call)

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
                "Ensure that your summary is clear, concise, and "
                "that no tasks are repeated or skipped."
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
        if self._supports_multimodal():
            if image_data:
                image_block = ImageBlock(
                    type="image",
                    source=Base64Source(
                        type="base64",
                        media_type="image/png",
                        data=image_data,
                    ),
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
                response_text = chunk.content[0]["text"]
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
                summary_text = ""
                async for content_chunk in res:
                    res_msg.content = content_chunk.content
                    summary_text = content_chunk.content[0]["text"]
                    await self.print(res_msg, False)
                await self.print(res_msg, True)
            else:
                summary_text = res.content[0]["text"]
                res_msg.content = summary_text
                await self.print(res_msg, True)
            # logger.info(summary_text)
            # Validate finish status
            finish_status = await self._validate_finish_status(summary_text)
            logger.info(f"Finish status: {finish_status}")

            if "BROWSER_AGENT_TASK_FINISHED" in finish_status:
                structure_response = WorkerResponse(
                    task_done=True,
                    subtask_progress_summary=summary_text,
                    generated_files={},
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
                        "structured_output": structure_response.model_dump(),
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
                    metadata={"success": False, "structured_output": None},
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

    async def _validate_finish_status(self, summary: str) -> str:
        """Validate if the agent has completed its task based on the summary."""
        sys_prompt = (
            "You are an expert in task validation. "
            "Your job is to determine if the agent has completed its task"
            " based on the provided summary. If the summary is `NO_ANSWER`, this task "
            "is not over unless the task is determined as definitely not completed. "
            "If finished, strictly reply "
            '"BROWSER_AGENT_TASK_FINISHED" and your reason, otherwise return the remaining '
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
