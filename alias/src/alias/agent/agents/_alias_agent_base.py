# -*- coding: utf-8 -*-
import asyncio
import json
import time
import traceback
from typing import Any, Optional, Literal

from loguru import logger

from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase, LongTermMemoryBase
from agentscope.message import Msg, ToolUseBlock, ToolResultBlock

from alias.agent.tools import AliasToolkit
from alias.agent.utils.constants import DEFAULT_PLANNER_NAME
from alias.agent.agents.common_agent_utils import (
    AliasAgentStates,
    alias_post_print_hook,
)
from alias.agent.utils.constants import DEFAULT_BROWSER_WORKER_NAME
from alias.agent.utils.constants import MODEL_MAX_RETRIES


class AliasAgentBase(ReActAgent):
    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        memory: MemoryBase,
        toolkit: AliasToolkit,
        session_service: Any,
        state_saving_dir: Optional[str] = None,
        sys_prompt: Optional[str] = None,
        max_iters: int = 10,
        long_term_memory: Optional[LongTermMemoryBase] = None,
        long_term_memory_mode: Literal[
            "agent_control",
            "static_control",
            "both",
        ] = "both",
    ):
        super().__init__(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            memory=memory,
            toolkit=toolkit,
            max_iters=max_iters,
            long_term_memory=long_term_memory,
            long_term_memory_mode=long_term_memory_mode,
        )

        self.session_service = session_service
        self.message_sending_mapping = {}
        self.state_saving_dir = state_saving_dir
        self.agent_stop_function_names = [self.finish_function_name]

        # for message output to backend
        self.register_instance_hook(
            "post_print",
            "alias_post_print_hook",
            alias_post_print_hook,
        )

        # register finish_function_name
        if self.finish_function_name not in self.toolkit.tools:
            self.toolkit.register_tool_function(
                getattr(self, self.finish_function_name),
            )

    async def _reasoning(
        self,
        tool_choice: Literal["auto", "none", "required"] | None = None,
    ):
        """Override _reasoning to add retry logic."""

        # Call the parent class's _reasoning method directly to
        # avoid double hook execution
        # We need to call the underlying implementation without hooks
        async def call_parent_reasoning():
            # Get the original method from the parent class before
            # metaclass processing
            # Access the method from the class that defines it
            # (before metaclass wrapping)
            original_method = ReActAgent.__dict__["_reasoning"]
            # Check if this is the wrapped version by looking for
            # the wrapper attributes
            if hasattr(original_method, "__wrapped__"):
                # This is the wrapped version, get the original
                original_method = original_method.__wrapped__

            return await original_method(self, tool_choice=tool_choice)

        for i in range(MODEL_MAX_RETRIES - 1):
            try:
                return await call_parent_reasoning()
            except Exception:
                logger.warning(
                    f"Reasoning fail at attempt {i + 1}. "
                    f"Max attempts {MODEL_MAX_RETRIES}\n"
                    f"{traceback.format_exc()}",
                )
                memory_msgs = await self.memory.get_memory()
                mem_len = len(memory_msgs)
                # ensure the last message has no tool_use before next attempt
                if mem_len > 0 and memory_msgs[-1].has_content_blocks(
                    "tool_use",
                ):
                    await self.memory.delete(index=mem_len - 1)
                time.sleep(2)

        # final attempt
        await call_parent_reasoning()

    async def _acting(self, tool_call: ToolUseBlock) -> dict | None:
        """Perform the acting process, and return the structured output if
        it's generated and verified in the finish function call.

        Args:
            tool_call (`ToolUseBlock`):
                The tool use block to be executed.

        Returns:
            `Union[dict, None]`:
                Return the structured output if it's verified in the finish
                function call.
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

            # Async generator handling
            async for chunk in tool_res:
                # Turn into a tool result block
                tool_res_msg.content[0][  # type: ignore[index]
                    "output"
                ] = chunk.content

                # todo: monkey patch to pass the metadata
                if chunk.metadata:
                    if tool_res_msg.metadata is None:
                        tool_res_msg.metadata = {}
                    for key, value in chunk.metadata.items():
                        try:
                            # verify it's JSON-serializable
                            json.dumps(value)
                            tool_res_msg.metadata[key] = value
                        except (TypeError, ValueError):
                            # Skip non-serializable values
                            pass

                # Skip the printing of the finish function call
                if self.name != DEFAULT_BROWSER_WORKER_NAME and (
                    tool_call["name"] != self.finish_function_name
                    or (
                        tool_call["name"] == self.finish_function_name
                        and chunk.metadata
                        and not chunk.metadata.get("success")
                    )
                ):
                    await self.print(tool_res_msg, chunk.is_last)

                # Return message if generate_response is called successfully
                if (
                    tool_call["name"] in self.agent_stop_function_names
                    and chunk.metadata
                    and chunk.metadata.get(
                        "success",
                        True,
                    )
                ):
                    return chunk.metadata.get("structured_output")
                elif chunk.is_interrupted:
                    raise asyncio.CancelledError

            return None
        finally:
            # Record the tool result message in the memory
            await self.memory.add(tool_res_msg)

    async def handle_interrupt(
        self,  # pylint: disable=unused-argument
        _msg: Msg | list[Msg] | None = None,
        **kwargs: Any,
    ) -> Msg:
        """
        The post-processing logic when the reply is interrupted by the
        user or something else.
        """
        response_msg = Msg(
            self.name,
            "I noticed that you have interrupted me. What can I "
            "do for you?",
            "assistant",
            metadata={
                # Expose this field to indicate the interruption
                "_is_interrupted": True,
            },
        )

        await self.print(response_msg, True)
        await self.memory.add(response_msg)

        # update and save agent states
        global_state = await self.session_service.get_state()
        if global_state is None:
            global_state = AliasAgentStates()
        else:
            global_state = AliasAgentStates(**global_state)
        global_state.agent_states[self.name] = self.state_dict()
        await self.session_service.create_state(
            content=global_state.model_dump(),
        )

        if self.name == DEFAULT_PLANNER_NAME:
            return response_msg
        else:
            raise asyncio.CancelledError

    def add_interrupt_function_name(
        self,
        func_name: str,
    ):
        """
        Add additional interrupt function name to the agent.
        """
        self.agent_stop_function_names.append(func_name)

    async def _retrieve_from_long_term_memory(
        self,
        msg: Msg | list[Msg] | None,  # pylint: disable=unused-argument
    ) -> None:
        """Override the parent method to retrieve from long-term memory using
        the last user message in memory if available.
        Args:
            msg (`Msg | list[Msg] | None`):
                The input message to the agent (may be None).
        """
        if self._static_control and self.long_term_memory:
            # Get messages from memory
            memory_msgs = await self.memory.get_memory()

            # Check if there are messages and the last one is from user
            if memory_msgs and len(memory_msgs) > 0:
                last_msg = memory_msgs[-1]
                if last_msg.role == "user":
                    # Check if the user message is just "continue"
                    user_content = str(last_msg.content).strip().lower()
                    if user_content == "continue":
                        logger.info(
                            "User input is 'continue' message, "
                            "skipping retrieve from long-term memory",
                        )
                        retrieved_info = None
                    else:
                        # Retrieve using the last user message
                        retrieved_info = await self.long_term_memory.retrieve(
                            last_msg,
                        )
                    if retrieved_info:
                        retrieved_msg = Msg(
                            name="long_term_memory",
                            content="<long_term_memory>The content below are "
                            "retrieved from long-term memory, which may be "
                            "related to user preference and may be useful:\n"
                            f"{retrieved_info}</long_term_memory>",
                            role="user",
                        )
                        await self.memory.add(retrieved_msg)
