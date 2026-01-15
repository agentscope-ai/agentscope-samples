# -*- coding: utf-8 -*-
# flake8: noqa
# pylint: disable=line-too-long,too-many-branches,too-many-statements,too-many-nested-blocks
"""
FastMCP Server Development Template
This is an MCP Server starter template based on the fastMcp framework, allowing developers to quickly develop their own MCP Server and deploy it to Alibaba Cloud Bailian high-code platform

Core features:
1. Use @mcp.tool() decorator to quickly define tools
2. Built-in health check interface
3. Support for HTTP SSE, streamable connection methods
4. Provide complete MCP protocol support (list tools, call tool, etc.)

Developers only need to focus on writing their own tool functions.
"""

import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from agentscope_runtime.engine.helpers.agent_api_builder import ResponseBuilder
from agentscope_runtime.engine.schemas.agent_schemas import Role
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

# Import MCP Server instance
from deploy_starter.mcp_server import (
    call_mcp_tool,
    convert_mcp_tools_to_openai_format,
    list_mcp_tools,
    mcp,
)

# ==================== Configuration Reading ====================


def read_config():
    """Read config.yml file"""
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    config_data = {}
    with open(config_path, encoding="utf-8") as config_file:
        for line in config_file:
            line = line.strip()
            if line and not line.startswith("#"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config_data[key] = value
    return config_data


config = read_config()

# ==================== Create MCP ASGI Application ====================
# Pre-create MCP application instance for reuse in lifespan and mount
mcp_asgi_app = mcp.streamable_http_app(path="/")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifecycle management - integrate MCP application's lifespan"""
    # Use MCP application's lifespan context manager
    async with mcp_asgi_app.router.lifespan_context(fastapi_app):
        # Application startup completed, entering running state
        yield
        # Automatic cleanup when application closes


# Create FastAPI application
app = FastAPI(
    title=config.get("APP_NAME", "MCP Server with Chat"),
    debug=config.get("DEBUG", False),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or ["*"] for development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Mount MCP Server Routes ====================
# Integrate MCP Server routes into main application
# This way only one server needs to be started to provide both MCP tools and Chat interface
# Note: mcp_asgi_app is already created above, use it directly here

# Mount MCP routes to main application under /mcp path
app.mount("/mcp", mcp_asgi_app)


@app.get("/")
def read_root():
    return "<h1>hi, i'm running</h1>"


@app.get("/health")
def health_check():
    return "OK"


class ContentItem(BaseModel):
    type: str  # e.g.: "text", "data", etc.
    text: str | None = None  # Text content (optional)
    data: dict[str, Any] | None = None  # Data content (optional)
    status: str | None = None  # Status

    class Config:
        extra = "allow"  # Allow extra fields


class MessageItem(BaseModel):
    role: str  # e.g.: "user", "assistant"
    content: list[ContentItem] | None = None  # content array (optional)
    type: str | None = (
        None  # Message type: message, plugin_call, plugin_call_output, etc.
    )

    class Config:
        extra = "allow"  # Allow extra fields (like sequence_number, object, status, id, etc.)


class ChatRequest(BaseModel):
    input: list[MessageItem]  # Message array
    session_id: str  # Session ID
    stream: bool | None = True  # Whether to stream response


# ==================== Chat Interface Implementation ====================


# Bailian example process call interface, requires DASHSCOPE_API_KEY configuration
@app.post("/process")
async def chat(request_data: ChatRequest):
    """
    Chat interface implementation, supports LLM calls and MCP tool calls

    Core workflow:
    1. Receive user message
    2. Get MCP tool list
    3. Call LLM (with function calling)
    4. If LLM needs to call tools, call MCP tools
    5. Return tool results to LLM
    6. Return final response (conforms to AgentScope ResponseBuilder format)
    """

    # Get DashScope API Key
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        api_key = config.get("DASHSCOPE_API_KEY")

    if not api_key:
        return {"error": "DASHSCOPE_API_KEY not configured"}

    # Initialize OpenAI client (DashScope is compatible with OpenAI API)
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    # Convert message format to OpenAI format
    # Keep conversation history: user messages + assistant's final answer (type="message")
    # Ignore intermediate steps: plugin_call, plugin_call_output, reasoning
    messages = []
    for msg in request_data.input:
        # Process user messages
        if msg.role == "user":
            content_text = ""
            if msg.content:
                for content_item in msg.content:
                    if content_item.type == "text" and content_item.text:
                        content_text += content_item.text

            if content_text:  # Only add non-empty messages
                messages.append({"role": "user", "content": content_text})

        # Process assistant's final answer (type="message")
        elif msg.role == "assistant" and msg.type == "message":
            content_text = ""
            if msg.content:
                for content_item in msg.content:
                    if content_item.type == "text" and content_item.text:
                        content_text += content_item.text

            if content_text:
                messages.append({"role": "assistant", "content": content_text})

    # Get MCP tool list
    try:
        mcp_tools = await list_mcp_tools()
        openai_tools = convert_mcp_tools_to_openai_format(mcp_tools)
    except Exception as e:
        print(f"Failed to get MCP tools: {e}")
        openai_tools = []

    async def generate_response():
        """Generate streaming response - conforms to Bailian Response/Message/Content architecture"""
        # Create ResponseBuilder
        response_builder = ResponseBuilder(
            session_id=request_data.session_id,
            response_id=f"resp_{request_data.session_id}",
        )

        # 1. Send Response created status
        yield f"data: {response_builder.created().model_dump_json()}\n\n"

        # 2. Send Response in_progress status
        yield f"data: {response_builder.in_progress().model_dump_json()}\n\n"

        try:
            # First phase: LLM initial response (may contain tool call decisions)
            if openai_tools:
                response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    tools=openai_tools,
                    stream=True,
                )
            else:
                response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    stream=True,
                )

            # Collect LLM response content and tool calls
            llm_content = ""
            tool_calls = []
            current_tool_call: dict[str, Any] | None = None

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta = choice.delta

                    # Collect text content
                    if delta.content:
                        llm_content += delta.content

                    # Collect tool calls
                    if delta.tool_calls:
                        for tool_call_chunk in delta.tool_calls:
                            if tool_call_chunk.index is not None:
                                if current_tool_call is None:
                                    pass
                                elif (
                                    current_tool_call["index"]
                                    != tool_call_chunk.index
                                ):
                                    tool_calls.append(current_tool_call)
                                    current_tool_call = None

                                if current_tool_call is None:
                                    current_tool_call = {
                                        "index": tool_call_chunk.index,
                                        "id": tool_call_chunk.id or "",
                                        "type": "function",
                                        "function": {
                                            "name": tool_call_chunk.function.name
                                            or "",
                                            "arguments": (
                                                tool_call_chunk.function.arguments
                                                or ""
                                            ),
                                        },
                                    }
                                elif tool_call_chunk.function.arguments:
                                    current_tool_call["function"][
                                        "arguments"
                                    ] += tool_call_chunk.function.arguments

            if current_tool_call:
                tool_calls.append(current_tool_call)

            # Decide message flow based on whether there are tool calls
            if tool_calls:
                # Scenario: has tool calls
                # 3. Create reasoning message (if LLM has thinking content)
                if llm_content.strip():
                    reasoning_msg_builder = (
                        response_builder.create_message_builder(
                            role=Role.ASSISTANT,
                            message_type="reasoning",
                        )
                    )
                    yield f"data: {reasoning_msg_builder.get_message_data().model_dump_json()}\n\n"

                    reasoning_content_builder = (
                        reasoning_msg_builder.create_content_builder()
                    )
                    yield f"data: {reasoning_content_builder.add_text_delta(llm_content).model_dump_json()}\n\n"
                    yield f"data: {reasoning_content_builder.complete().model_dump_json()}\n\n"
                    yield f"data: {reasoning_msg_builder.complete().model_dump_json()}\n\n"

                # 4. First add assistant message (containing all tool calls) to message history
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    },
                )

                # 5. Process each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    # 5.1 Create plugin_call message (display to user)
                    plugin_call_msg_builder = (
                        response_builder.create_message_builder(
                            role=Role.ASSISTANT,
                            message_type="plugin_call",
                        )
                    )
                    yield f"data: {plugin_call_msg_builder.get_message_data().model_dump_json()}\n\n"

                    plugin_call_content_builder = (
                        plugin_call_msg_builder.create_content_builder(
                            content_type="data",
                        )
                    )
                    tool_call_data = {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, ensure_ascii=False),
                    }
                    yield f"data: {plugin_call_content_builder.add_data_delta(tool_call_data).model_dump_json()}\n\n"
                    yield f"data: {plugin_call_content_builder.complete().model_dump_json()}\n\n"
                    yield f"data: {plugin_call_msg_builder.complete().model_dump_json()}\n\n"

                    # 5.2 Call MCP tool
                    try:
                        tool_result = await call_mcp_tool(tool_name, tool_args)

                        # 5.3 Create plugin_call_output message (display to user)
                        plugin_output_msg_builder = (
                            response_builder.create_message_builder(
                                role=Role.ASSISTANT,
                                message_type="plugin_call_output",
                            )
                        )
                        yield f"data: {plugin_output_msg_builder.get_message_data().model_dump_json()}\n\n"

                        plugin_output_content_builder = (
                            plugin_output_msg_builder.create_content_builder(
                                content_type="data",
                            )
                        )
                        output_data = {
                            "name": tool_name,
                            "output": (
                                json.dumps(tool_result, ensure_ascii=False)
                                if tool_result
                                else ""
                            ),
                        }
                        yield f"data: {plugin_output_content_builder.add_data_delta(output_data).model_dump_json()}\n\n"
                        yield f"data: {plugin_output_content_builder.complete().model_dump_json()}\n\n"
                        yield f"data: {plugin_output_msg_builder.complete().model_dump_json()}\n\n"

                        # Add tool message to message history
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": (
                                    json.dumps(tool_result, ensure_ascii=False)
                                    if tool_result
                                    else ""
                                ),
                            },
                        )
                    except Exception as e:
                        print(f"Tool call failed: {e}")
                        # Add error result to message history
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": f"Error: {str(e)}",
                            },
                        )

                # 6. Use tool results to call LLM again to generate final answer
                final_response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    stream=True,
                )

                # 7. Create final message (answer based on tool results)
                final_msg_builder = response_builder.create_message_builder(
                    role=Role.ASSISTANT,
                    message_type="message",
                )
                yield f"data: {final_msg_builder.get_message_data().model_dump_json()}\n\n"

                final_content_builder = (
                    final_msg_builder.create_content_builder()
                )

                async for chunk in final_response:
                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            yield f"data: {final_content_builder.add_text_delta(choice.delta.content).model_dump_json()}\n\n"

                yield f"data: {final_content_builder.complete().model_dump_json()}\n\n"
                yield f"data: {final_msg_builder.complete().model_dump_json()}\n\n"

            else:
                # Scenario: no tool calls, return LLM response directly
                # 3. Create message (direct answer)
                msg_builder = response_builder.create_message_builder(
                    role=Role.ASSISTANT,
                    message_type="message",
                )
                yield f"data: {msg_builder.get_message_data().model_dump_json()}\n\n"

                content_builder = msg_builder.create_content_builder()
                yield f"data: {content_builder.add_text_delta(llm_content).model_dump_json()}\n\n"
                yield f"data: {content_builder.complete().model_dump_json()}\n\n"
                yield f"data: {msg_builder.complete().model_dump_json()}\n\n"

            # 8. Complete Response
            yield f"data: {response_builder.completed().model_dump_json()}\n\n"
            # yield "data: [DONE]\n\n"

        except Exception as e:
            # Error handling
            print(f"Chat interface error: {e}")
            error_msg_builder = response_builder.create_message_builder(
                role=Role.ASSISTANT,
                message_type="error",
            )
            error_content_builder = error_msg_builder.create_content_builder()
            error_text = f"Error occurred: {str(e)}"
            yield f"data: {error_content_builder.add_text_delta(error_text).model_dump_json()}\n\n"
            yield f"data: {error_content_builder.complete().model_dump_json()}\n\n"
            yield f"data: {error_msg_builder.complete().model_dump_json()}\n\n"
            yield f"data: {response_builder.completed().model_dump_json()}\n\n"
            # yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
    )


# ==================== Start Application ====================


def run_app():
    """Entry point for running the application via command line."""
    uvicorn.run(
        "deploy_starter.main:app",
        host=config.get("FC_START_HOST", "127.0.0.1"),
        port=config.get("PORT", 8080),
        reload=config.get("RELOAD", False),
    )


if __name__ == "__main__":
    # Start FastAPI application
    run_app()
