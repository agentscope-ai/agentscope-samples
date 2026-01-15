# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
from typing import Any, Optional, List, Union, Dict

from agentscope.message import Msg
from reme_ai import ReMeApp
from reme_ai.schema.memory import ToolCallResult

from .basememory import BaseMemory
from .profiling_utils.logging_utils import setup_logging

logger = setup_logging()


class ToolMemory(BaseMemory):
    """
    Tool Memory implementation using ReMe backend.

    This class manages tool execution history and retrieves usage guidelines
    for tools based on historical performance.

    Args:
        summary_time_threshold: Time threshold in seconds for triggering
            summary (default: 300s = 5min)
        summary_count_threshold: Count threshold for triggering summary
            (default: 5)
    """

    def __init__(
        self,
        summary_time_threshold: int = 300,
        summary_count_threshold: int = 5,
    ):
        super().__init__()
        qdrant_host = os.getenv("QDRANT_HOST", "0.0.0.0")
        qdrant_port_str = os.getenv("QDRANT_PORT", "6333")
        qdrant_port = int(qdrant_port_str)
        vector_store_url = (
            f"vector_store.default.params.url="
            f"http://{qdrant_host}:{qdrant_port}"
        )
        self._app = ReMeApp(
            "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
            "embedding_model.default.model_name=text-embedding-v4",
            "vector_store.default.backend=qdrant",
            vector_store_url,
            llm_api_key=os.environ.get("DASHSCOPE_API_KEY"),
            llm_api_base=("https://dashscope.aliyuncs.com/compatible-mode/v1"),
            embedding_api_key=os.environ.get("DASHSCOPE_API_KEY"),
            embedding_api_base=(
                "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
        )

        self.inited: bool = False

        # Summary thresholds (configurable)
        self.summary_time_threshold = summary_time_threshold
        self.summary_count_threshold = summary_count_threshold

        # Track summary state for each tool per workspace
        # Format: {uid: {tool_name: {"last_summary_time": datetime,
        #                             "unsummarized_count": int}}}
        self._tool_summary_state: Dict[str, Dict[str, Dict[str, Any]]] = {}

    async def __aenter__(self):
        self.inited = True
        return await self._app.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._app.__aexit__(exc_type, exc_val, exc_tb)

    async def retrieve(
        self,
        uid: str,
        query: str = None,
        **kwargs,
    ) -> Any | bool:
        if not self.inited:
            await self.__aenter__()
        uid = uid or "alias"

        # Use tool_names if provided, otherwise use query as tool_names
        tool_names = query

        if not tool_names:
            logger.warning("No tool_names provided for retrieve")
            return "No tool_names provided for retrieve"

        result = await self._app.async_execute(
            name="retrieve_tool_memory",
            workspace_id=uid,
            tool_names=tool_names,
        )
        answer = result.get("answer", "")
        return answer

    async def add_memory(self, uid: str, content: List[Msg], **kwargs) -> Any:
        if not self.inited:
            await self.__aenter__()

        result = await self._app.async_execute(
            name="add_tool_call_result",
            workspace_id=uid,
            tool_call_results=[json.loads(x.content) for x in content],
        )

        return result["answer"]

    async def process_content(self, uid: str, content: Union[List[Msg], Msg]):
        """extract info in content for memory."""

    async def delete(self, uid: str, key: Any) -> None:
        """Delete part of memory by some criteria."""

    async def clear_memory(self, uid: str) -> None:
        """Clear all memory."""

    async def show_all_memory(self, uid: str) -> Any:
        """Show all memory."""

    @staticmethod
    def time_diff_seconds(time_str1: str, time_str2: str) -> float:
        """
        Convert two ISO 8601 formatted time strings
        (e.g., '2025-10-22T09:14:17.290252+00:00') to datetime objects,
        calculate their difference, and return a float value in seconds.

        Args:
            time_str1 (str): First time string
            time_str2 (str): Second time string

        Returns:
            float: The difference between time_str1 and time_str2 in seconds
        """
        dt1 = datetime.fromisoformat(time_str1)
        dt2 = datetime.fromisoformat(time_str2)
        diff = dt1 - dt2
        return diff.total_seconds()

    def _init_tool_state(self, uid: str, tool_name: str) -> None:
        """Initialize tracking state for a tool if not exists."""
        if uid not in self._tool_summary_state:
            self._tool_summary_state[uid] = {}
        if tool_name not in self._tool_summary_state[uid]:
            self._tool_summary_state[uid][tool_name] = {
                "last_summary_time": None,
                "unsummarized_count": 0,
            }

    def _increment_tool_count(
        self,
        uid: str,
        tool_name: str,
        count: int = 1,
    ) -> None:
        """Increment the unsummarized count for a tool."""
        self._init_tool_state(uid, tool_name)
        self._tool_summary_state[uid][tool_name]["unsummarized_count"] += count

    def _reset_tool_state(self, uid: str, tool_name: str) -> None:
        """Reset the tool state after summarization."""
        self._init_tool_state(uid, tool_name)
        self._tool_summary_state[uid][tool_name][
            "last_summary_time"
        ] = datetime.now()
        self._tool_summary_state[uid][tool_name]["unsummarized_count"] = 0

    def _should_summarize(self, uid: str, tool_name: str) -> bool:
        """
        Check if a tool should be summarized based on:
        1. Time since last summary exceeds summary_time_threshold
        2. Unsummarized count exceeds summary_count_threshold
        """
        self._init_tool_state(uid, tool_name)
        state = self._tool_summary_state[uid][tool_name]

        # Check count threshold
        if state["unsummarized_count"] > self.summary_count_threshold:
            return True

        # Check time threshold
        if state["last_summary_time"] is None:
            return True

        time_diff = (
            datetime.now() - state["last_summary_time"]
        ).total_seconds()
        if time_diff > self.summary_time_threshold:
            return True

        return False

    def parse_session_content(
        self,
        session_content: list,
    ) -> List[ToolCallResult]:
        group_result: dict[str, ToolCallResult] = {}
        for message_obj in session_content:
            message = message_obj["message"]
            msg_type = message["type"]
            if msg_type not in ["tool_use", "tool_result"]:
                continue

            tool_name = message["tool_name"]
            content = json.loads(message["content"])
            status = message["status"]
            call_id = content[0].get("id", "unknown")

            if call_id not in group_result:
                group_result[call_id] = ToolCallResult(tool_name=tool_name)

            tool_call_result = group_result[call_id]
            if not tool_call_result.create_time and message_obj.get(
                "create_time",
                "",
            ):
                tool_call_result.create_time = message_obj.get(
                    "create_time",
                    "",
                )

            if (
                msg_type == "tool_use"
                and not group_result[call_id].input
                and message.get("arguments", "")
            ):
                group_result[call_id].input = json.dumps(message["arguments"])

            if (
                msg_type == "tool_result"
                and not group_result[call_id].output
                and content
            ):
                group_result[call_id].output = json.dumps(
                    [x["output"] for x in content],
                    ensure_ascii=False,
                )

            if msg_type == "tool_result" and status != "finished":
                group_result[call_id].success = False

            if (
                msg_type == "tool_result"
                and group_result[call_id].time_cost <= 0
            ):
                group_result[call_id].time_cost = self.time_diff_seconds(
                    message_obj["update_time"],
                    message_obj["create_time"],
                )

        result = []
        for _id, tool_call_result in group_result.items():
            print(
                f"id={_id} "
                f"tool_call_result={tool_call_result.model_dump_json()}",
            )
            result.append(tool_call_result)
        return result

    async def record_action(
        self,
        uid: str,
        action: str,
        session_id: Optional[str] = None,
        reference_time: Optional[str] = None,
        action_message_id: Optional[str] = None,
        data: Optional[Any] = None,
        session_content=None,
        **kwargs,
    ):
        if not self.inited:
            await self.__aenter__()
        uid = uid or "alias"

        logger.info(
            f"record_action called with: uid={uid}, action={action}, "
            f"session_id={session_id} action_message_id={action_message_id}",
        )
        session_len = len(session_content) if session_content else 0
        logger.info(f"session_content length: {session_len}")

        tool_call_results = self.parse_session_content(session_content)

        result = await self._app.async_execute(
            name="add_tool_call_result",
            workspace_id=uid,
            tool_call_results=[x.model_dump() for x in tool_call_results],
        )

        logger.info(result)

        # Group tool call results by tool name and increment counts
        tool_call_counts = {}
        for tcr in tool_call_results:
            tool_name = tcr.tool_name
            tool_call_counts[tool_name] = (
                tool_call_counts.get(tool_name, 0) + 1
            )

        # Increment counts for each tool
        for tool_name, count in tool_call_counts.items():
            self._increment_tool_count(uid, tool_name, count)

        # Check which tools need to be summarized
        tools_to_summarize = []
        for tool_name in tool_call_counts:
            if self._should_summarize(uid, tool_name):
                tools_to_summarize.append(tool_name)
                tool_state = self._tool_summary_state[uid][tool_name]
                logger.info(
                    f"Tool '{tool_name}' meets summarization criteria: "
                    f"unsummarized_count={tool_state['unsummarized_count']}, "
                    f"last_summary_time={tool_state['last_summary_time']}",
                )

        # Only execute summary if there are tools that meet the criteria
        if tools_to_summarize:
            logger.info(
                f"Executing summary_tool_memory for tools: "
                f"{tools_to_summarize}",
            )
            result = await self._app.async_execute(
                name="summary_tool_memory",
                workspace_id=uid,
                tool_names=sorted(tools_to_summarize),
                **kwargs,
            )

            logger.info(result)

            # Reset state for summarized tools
            for tool_name in tools_to_summarize:
                self._reset_tool_state(uid, tool_name)
        else:
            tool_counts = [
                (tn, self._tool_summary_state[uid][tn]["unsummarized_count"])
                for tn in tool_call_counts
            ]
            logger.info(
                f"No tools meet summarization criteria. "
                f"Current tool counts: {tool_counts}",
            )
