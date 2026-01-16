# -*- coding: utf-8 -*-
"""Data Science Agent"""
import asyncio
import json
import os
from functools import partial
from typing import List, Dict, Optional, Any, Type, cast, Literal
import uuid

from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase
from agentscope.message import Msg, TextBlock, ToolUseBlock, ToolResultBlock
from agentscope.model import ChatModelBase
from agentscope.tool import ToolResponse
from agentscope.tracing import trace_reply
from loguru import logger
from pydantic import BaseModel, ValidationError, Field
from tenacity import retry, stop_after_attempt, wait_fixed

from alias.agent.agents import AliasAgentBase

from alias.agent.tools import AliasToolkit, share_tools
from alias.agent.agents.common_agent_utils import (
    get_user_input_to_mem_pre_reply_hook,
)
from .ds_agent_utils import (
    ReportGenerator,
    LLMPromptSelector,
    todo_write,
    get_prompt_from_file,
    files_filter_pre_reply_hook,
    add_ds_specific_tool,
    set_run_ipython_cell,
)
from .ds_agent_utils.ds_config import PROMPT_DS_BASE_PATH


class DefaultStructuredResponse(BaseModel):
    response: str = Field(
        description="Just a placeholder. "
        "Enter any character to trigger report generation",
    )


class DataScienceAgent(AliasAgentBase):
    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        memory: MemoryBase,
        toolkit: AliasToolkit,
        sys_prompt: str = None,
        max_iters: int = 30,
        tmp_file_storage_dir: str = "/workspace",
        state_saving_dir: Optional[str] = None,
        session_service: Any = None,
    ) -> None:
        self.think_function_name = "think"
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

        set_run_ipython_cell(self.toolkit.sandbox)

        self.uploaded_files: List[str] = []

        self.todo_list: List[Dict[str, Any]] = []

        self.infer_trajectories: List[List[Msg]] = []

        self.detailed_report_path = os.path.join(
            tmp_file_storage_dir,
            "detailed_report.html",
        )
        self.tmp_file_storage_dir = tmp_file_storage_dir

        self.todo_list_prompt = get_prompt_from_file(
            os.path.join(
                PROMPT_DS_BASE_PATH,
                "_agent_todo_reminder_prompt.md",
            ),
            False,
        )

        self._sys_prompt = get_prompt_from_file(
            os.path.join(
                PROMPT_DS_BASE_PATH,
                "_agent_system_workflow_prompt.md",
            ),
            False,
        )

        # load prompts and initialize selector
        available_prompts = {
            "explorative_data_analysis": cast(
                str,
                get_prompt_from_file(
                    os.path.join(
                        PROMPT_DS_BASE_PATH,
                        "_scenario_explorative_data_analysis.md",
                    ),
                    False,
                ),
            ),
            "data_modeling": cast(
                str,
                get_prompt_from_file(
                    os.path.join(
                        PROMPT_DS_BASE_PATH,
                        "_scenario_data_modeling_prompt.md",
                    ),
                    False,
                ),
            ),
            "data_computation": cast(
                str,
                get_prompt_from_file(
                    os.path.join(
                        PROMPT_DS_BASE_PATH,
                        "_scenario_data_computation_prompt.md",
                    ),
                    False,
                ),
            ),
        }

        self.prompt_selector = LLMPromptSelector(
            self.model,
            self.formatter,
            available_prompts,
        )
        self._selected_scenario_prompts: str = ""

        self.toolkit.register_tool_function(
            partial(todo_write, agent=self),
            func_description=get_prompt_from_file(
                os.path.join(
                    PROMPT_DS_BASE_PATH,
                    "_tool_todo_list_prompt.yaml",
                ),
                False,
            ),
        )

        self.toolkit.register_tool_function(self.think)

        self.register_instance_hook(
            "pre_reply",
            "get_user_input_to_mem_pre_reply_hook",
            get_user_input_to_mem_pre_reply_hook,
        )

        self.register_instance_hook(
            "pre_reply",
            "files_filter_pre_reply_hook",
            files_filter_pre_reply_hook,
        )

        logger.info(
            f"[{self.name}] "
            "DeepInsightAgent initialized (fully model-driven).",
        )

    @property
    def sys_prompt(self) -> str:
        base_prompt = self._sys_prompt

        todo_prompt = self.todo_list_prompt.replace(
            "{todoList}",
            json.dumps(self.todo_list, indent=2, ensure_ascii=False),
        )

        return (
            f"{base_prompt}{self._selected_scenario_prompts}\n\n{todo_prompt}"
        )

    @trace_reply
    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
        structured_model: Type[BaseModel] | None = None,
    ) -> Msg:
        self._selected_scenario_prompts = await self._load_scenario_prompts()
        self.remove_instance_hook(
            "pre_reply",
            "get_user_input_to_mem_pre_reply_hook",
        )
        self.remove_instance_hook(
            "pre_reply",
            "files_filter_pre_reply_hook",
        )

        if structured_model is None:
            structured_model = DefaultStructuredResponse

        # Record the input message(s) in the memory
        await self.memory.add(msg)

        # -------------- Retrieval process --------------
        # Retrieve relevant records from the long-term memory if activated
        await self._retrieve_from_long_term_memory(msg)
        # Retrieve relevant documents from the knowledge base(s) if any
        await self._retrieve_from_knowledge(msg)

        # Control if LLM generates tool calls in each reasoning step
        tool_choice: Literal["auto", "none", "required"] | None = None

        # -------------- Structured output management --------------
        self._required_structured_model = structured_model

        # Register generate_response tool only when structured output
        # is required
        if self.finish_function_name not in self.toolkit.tools:
            self.toolkit.register_tool_function(
                getattr(self, self.finish_function_name),
            )

        # Set the structured output model
        self.toolkit.set_extended_model(
            self.finish_function_name,
            structured_model,
        )
        tool_choice = "required"

        # -------------- The reasoning-acting loop --------------
        # Cache the structured output generated in the finish function call
        structured_output = None
        reply_msg = None
        for _ in range(self.max_iters):
            # -------------- The reasoning process --------------
            msg_reasoning = await self._reasoning(tool_choice)

            # -------------- The acting process --------------
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
            # Remove None results
            structured_outputs = [_ for _ in structured_outputs if _]

            msg_hint = None
            # If the acting step generates structured outputs
            if structured_outputs:
                # Cache the structured output data
                structured_output = structured_outputs[-1]

                reply_msg = Msg(
                    self.name,
                    structured_output.get("response"),
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

            if msg_hint and self.print_hint_msg:
                await self.print(msg_hint)

        # When the maximum iterations are reached
        # and no reply message is generated
        if reply_msg is None:
            reply_msg = await self._summarizing()
            reply_msg.metadata = structured_output
            await self.memory.add(reply_msg)

        # Post-process the memory, long-term memory
        if self._static_control:
            await self.long_term_memory.record(
                [
                    *([*msg] if isinstance(msg, list) else [msg]),
                    *await self.memory.get_memory(),
                    reply_msg,
                ],
            )

        return reply_msg

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(5), reraise=True)
    async def _reasoning(
        self,
        tool_choice: str = "required",
    ) -> Msg:
        """Perform the reasoning process."""
        prompt = await self.formatter.format(
            msgs=[
                Msg("system", self.sys_prompt, "system"),
                *await self.memory.get_memory(),
                # The hint messages to guide the agent's behavior, maybe empty
                *await self._reasoning_hint_msgs.get_memory(),
            ],
        )

        # Clear the hint messages after use
        await self._reasoning_hint_msgs.clear()

        try:
            res = await self.model(
                prompt,
                tools=self.toolkit.get_json_schemas(),
                tool_choice=tool_choice,
            )
        except Exception as e:
            logger.debug("Error while calling model in _reasoning: {}", e)

        # handle output from the model
        interrupted_by_user = False
        msg = None
        try:
            if self.model.stream:
                msg = Msg(self.name, [], "assistant")
                async for content_chunk in res:
                    msg.content = content_chunk.content
                    await self.print(msg, False)
                await self.print(msg, True)

            else:
                msg = Msg(self.name, list(res.content), "assistant")
                await self.print(msg, True)

            return msg

        except asyncio.CancelledError as e:
            interrupted_by_user = True
            raise e from None

        finally:
            # None will be ignored by the memory
            await self.memory.add(msg)

            # Post-process for user interruption
            if interrupted_by_user and msg:
                # Fake tool results
                tool_use_blocks: list = msg.get_content_blocks(
                    "tool_use",
                )
                for tool_call in tool_use_blocks:
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

    # pylint: disable=invalid-overridden-method, unused-argument
    async def generate_response(
        self,
        **kwargs: Any,
    ) -> ToolResponse:
        """
        Generate required structured output by this function and return it
        """
        memory = await self.memory.get_memory()
        memory_log = "\n\n".join(
            (
                "=" * 10
                + "\n"
                + f"Role: {item.role},\n"
                + f"Name: {item.name},\n"
                + f"content: {str(item.content)}\n"
                + "=" * 10
            )
            for item in memory
        )

        await self.print(
            Msg(
                name=self.name,
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Generating your response…\n"
                            "For complex queries, the agent may produce a "
                            "detailed report to ensure completeness. "
                            "This process can take up to 2–3 minutes. "
                            "Thank you for your patience!"
                        ),
                    },
                ],
                role="assistant",
            ),
        )

        report_generator = ReportGenerator(
            model=self.model,
            formatter=self.formatter,
            memory_log=memory_log,
        )

        response, report = await report_generator.generate_report()

        if report:
            # report = report.replace(self.tmp_file_storage_dir, ".")
            await self.toolkit.call_tool_function(
                ToolUseBlock(
                    type="tool_use",
                    id=str(uuid.uuid4()),
                    name="write_file",
                    input={
                        "path": self.detailed_report_path,
                        "content": report,
                    },
                ),
            )
            response = (
                f"{response}\n\n"
                "The detailed report has been saved to "
                f"{self.detailed_report_path}."
            )

        kwargs["response"] = response
        structured_output = {}

        # Prepare structured output
        if self._required_structured_model:
            try:
                # Use the metadata field of the message to store the
                # structured output
                structured_output = (
                    self._required_structured_model.model_validate(
                        kwargs,
                    ).model_dump()
                )

            except ValidationError as e:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=f"Arguments Validation Error: {e}",
                        ),
                    ],
                    metadata={
                        "success": False,
                        "structured_output": {},
                    },
                )

        await self.print(
            Msg(
                name=self.name,
                content=response,
                role="assistant",
            ),
            True,
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
                "structured_output": structured_output,
            },
            is_last=True,
        )

    async def _load_scenario_prompts(self):
        if self.prompt_selector is None or self._selected_scenario_prompts:
            return self._selected_scenario_prompts

        user_input = (await self.memory.get_memory())[0].content[0]["text"]

        selected_scenarios = await self.prompt_selector.select(user_input)

        # concat selected scenario prompts
        scenario_contents = []
        if selected_scenarios:
            for scenario in selected_scenarios:
                content = self.prompt_selector.get_prompt_by_scenario(scenario)
                scenario_contents.append(content)

        self._selected_scenario_prompts = "\n\n".join(scenario_contents)
        return self._selected_scenario_prompts

    def _print_todo_list(self):
        content = (
            f" The todoList is :\n"
            f"\n{json.dumps(self.todo_list, indent=4, ensure_ascii=False)}"
            "\n" + "==" * 10 + "\n"
        )
        logger.log("SEND_PLAN", content)
        with open(
            self.session_service.log_storage_path,
            "a",
            encoding="utf-8",
        ) as file:
            # Append the content
            file.write(content)

    def think(self, response: str):
        """
        Invoke this function whenever you need to
        pause and "think" or "summarize".

        Typical situations:
        - Consolidate, organize, or verify information at key milestones
        - Walk yourself (and the user) through your reasoning or trade-offs
        - Perform a final check before declaring the task complete,
        or explain why it cannot continue

        Simply write your reflection or summary into `response` after the call,
        execution will resume based on the insights you just recorded.

        Args:
            response (str): Your thoughts, summary, or explanation to capture.
        """
        instruction = (
            "This is a valuable insight. Next, please confirm whether the "
            "task has been completed:\n"
            "1. All subtasks have been addressed.\n"
            "2. If this is a data analysis task, has sufficient data "
            "exploration and analysis been performed to derive meaningful "
            "insights from the data?\n"
            f"If the task is not yet complete, proceed with completing it. "
            f"Otherwise, use the `{self.finish_function_name}` tool to "
            "finalize the task.\n"
            "Do not provide additional feedback—simply continue executing "
            "the task or end it directly."
        )
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=instruction,
                ),
            ],
        )


def init_ds_toolkit(full_toolkit: AliasToolkit) -> AliasToolkit:
    ds_toolkit = AliasToolkit(full_toolkit.sandbox, add_all=False)
    ds_tool_list = [
        "write_file",
        "run_ipython_cell",
        "run_shell_command",
    ]
    share_tools(full_toolkit, ds_toolkit, ds_tool_list)
    add_ds_specific_tool(ds_toolkit)
    return ds_toolkit
