# -*- coding: utf-8 -*-
import json
import logging
import os
import time

from quart import Quart, Response, jsonify, request
from quart_cors import cors

from agentscope_browseruse_agent import AgentscopeBrowseruseAgent
from agentscope_runtime.engine.schemas.agent_schemas import (
    DataContent,
    TextContent,
)


app = Quart(__name__)
app = cors(app, allow_origin="*")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

agent = AgentscopeBrowseruseAgent()


if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv(".env")


async def user_mode(input_data):
    messages = input_data.get("messages", [])
    last_name = ""
    async for item in agent.chat(messages):
        if item:
            res = ""
            if isinstance(item, TextContent):
                res = item.text

            elif isinstance(item, DataContent):
                if "name" in item.data.keys():
                    if json.dumps(item.data["name"]) == last_name:
                        continue
                    res = "I will use the tool" + json.dumps(item.data["name"])
                    last_name = json.dumps(item.data["name"])
            elif isinstance(item, str):
                res = item
            yield simple_yield(res)
        else:
            yield simple_yield()


def simple_yield(content="", ctype="content"):
    dumped = json.dumps(
        wrap_as_openai_response(content, content, ctype=ctype),
        ensure_ascii=False,
    )
    reply = f"data: {dumped}\n\n"
    return reply


def wrap_as_openai_response(text_content, card_content, ctype="content"):
    if ctype == "content":
        content_type = "content"
    elif ctype == "think":
        content_type = "reasoning_content"
    elif ctype == "site":
        content_type = "site_content"
    else:
        content_type = "content"

    return {
        "id": "some_unique_id",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "choices": [
            {
                "delta": {content_type: text_content, "cards": card_content},
                "index": 0,
                "finish_reason": None,
            },
        ],
    }


@app.route("/v1/chat/completions", methods=["POST"])
@app.route("/chat/completions", methods=["POST"])
async def stream():
    data = await request.json
    return Response(user_mode(data), mimetype="text/event-stream")


@app.route("/env_info", methods=["GET"])
async def get_env_info():
    if agent.desktop_url is not None:
        url = agent.desktop_url
        logger.info(url)
        return jsonify({"url": url})
    else:
        return jsonify({"error": "WebSocket connection failed"}), 500


if __name__ == "__main__":
    agent.chat([{"role": "user", "content": "hello"}])
    app.run(host="0.0.0.0", port=9000)
