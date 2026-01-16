# -*- coding: utf-8 -*-
import asyncio
import os
import json
from typing import Union
from agentscope.message import Msg
from tenacity import retry, stop_after_attempt, wait_fixed
from .ds_config import PROMPT_DS_BASE_PATH

MODEL_MAX_RETRIES = 50


def get_prompt_from_file(
    file_path: str,
    return_json: bool,
) -> Union[str, dict]:
    """Get prompt from file"""
    with open(os.path.join(file_path), "r", encoding="utf-8") as f:
        if return_json:
            prompt = json.load(f)
        else:
            prompt = f.read()
    return prompt


@retry(
    stop=stop_after_attempt(MODEL_MAX_RETRIES),
    wait=wait_fixed(5),
    reraise=True,
    # before_sleep=_print_exc_on_retry
)
async def model_call_with_retry(
    model,
    formatter,
    msgs,
    tool_json_schemas=None,
    tool_choice=None,
    msg_name="model_call",
) -> Msg:
    prompt = await formatter.format(msgs=msgs)

    res = await model(prompt, tools=tool_json_schemas, tool_choice=tool_choice)

    if model.stream:
        msg = Msg(msg_name, [], "assistant")
        async for content_chunk in res:
            # print(f"content_chunk.content: {str(content_chunk)}")
            msg.content = content_chunk.content

        # Add a tiny sleep to yield the last message object in the
        # message queue
        await asyncio.sleep(0.001)

    else:
        msg = Msg(msg_name, list(res.content), "assistant")

    return msg


def set_run_ipython_cell(sandbox):
    # Clear all previous variables and imports
    print(
        sandbox.call_tool(
            "run_ipython_cell",
            {
                "code": """
        %reset -f -s
        print("All variables and imports cleared")
        """,
            },
        ),
    )

    # Set pandas display options
    print(
        sandbox.call_tool(
            "run_ipython_cell",
            {
                "code": """
        import pandas as pd
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)
    """,
            },
        ),
    )

    # Set matplotlib inline plotting
    with open(
        f"{PROMPT_DS_BASE_PATH}/_summarize_chart_code.txt",
        encoding="utf-8",
    ) as f:
        summarize_chart_code = f.read()
    print(
        sandbox.call_tool("run_ipython_cell", {"code": summarize_chart_code}),
    )
