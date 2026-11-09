# -*- coding: utf-8 -*-
"""Create the table discovery agent."""

import asyncio

from agentscope.agent import ReActAgent
from agentscope.formatter import DeepSeekChatFormatter, FormatterBase
from agentscope.message import Msg
from agentscope.model import ChatModelBase, OpenAIChatModel
from agentscope.tool import Toolkit
from openai import OpenAIError

from indexing import ColumnIndex
from tools.seeker import create_seeker


def create_agent(
    index: ColumnIndex,
    model: ChatModelBase,
    formatter: FormatterBase,
) -> ReActAgent:
    """Bind a ReAct agent to a prebuilt column index."""
    toolkit = Toolkit()
    toolkit.register_tool_function(create_seeker(index))
    return ReActAgent(
        name="table_discovery",
        sys_prompt=(
            "Help the user find columns in a CSV data lake. For a lookup, "
            "call seek_columns once. Use the metadata channel for names "
            "and types, or the content channel for values and statistics. "
            "Answer briefly using only the returned table and column names. "
            "If the results are insufficient, say so."
        ),
        model=model,
        formatter=formatter,
        toolkit=toolkit,
        max_iters=2,
    )


def run_query(
    index: ColumnIndex, question: str, model_name: str, api_key: str
) -> str:
    """Ask the discovery agent a single question using DeepSeek."""
    try:
        model = OpenAIChatModel(
            model_name=model_name,
            api_key=api_key,
            stream=False,
            client_kwargs={"base_url": "https://api.deepseek.com"},
            generate_kwargs={
                "extra_body": {"thinking": {"type": "disabled"}},
            },
        )
        agent = create_agent(index, model, DeepSeekChatFormatter())
        agent.set_console_output_enabled(False)
        response = asyncio.run(
            agent(Msg(name="user", content=question, role="user"))
        )
    except OpenAIError as error:
        raise RuntimeError(str(error).replace(api_key, "[redacted]")) from None
    answer = response.get_text_content()
    if not answer:
        raise RuntimeError("the discovery agent returned an empty response")
    return answer
