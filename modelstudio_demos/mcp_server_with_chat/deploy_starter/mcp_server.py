# -*- coding: utf-8 -*-
# flake8: noqa
# pylint: disable=line-too-long
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
from typing import Annotated, Any

from agentscope_runtime.tools import ModelstudioSearchLite
from agentscope_runtime.tools.searches import SearchLiteInput, SearchLiteOutput
from fastmcp import Client, FastMCP
from pydantic import Field

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

# ==================== Initialize FastMCP ====================

# Create MCP server instance, define MCP name and version
mcp = FastMCP(
    name=config.get("MCP_SERVER_NAME", "my-mcp-server"),
    version="1.0.0",
)

# ==================== Tool Definition Examples ====================
# Developers can define their own tools here, using @mcp.tool() decorator


# Example tool1, simple addition tool, simple call with average IO performance
@mcp.tool(
    name="add Tool",  # Custom tool name for the LLM
    description="A simple addition tool example for calculating the sum of two integers",  # Custom description
)
def add_numbers(
    a: Annotated[int, Field(description="add a")],
    b: Annotated[int, Field(description="add b")],
) -> int:
    return a + b


# Example tool2, Alibaba Cloud Bailian search, asynchronous call with high IO performance
@mcp.tool(
    name="Alibaba Cloud Bailian search",  # Custom tool name for the LLM
    description="Search MCP wrapper by calling Alibaba Cloud Bailian search API, requires dashScope api key in environment variables",  # Custom description
)
async def search_by_modelStudio(
    query: Annotated[str, Field(description="Search query statement")],
    count: Annotated[
        int,
        Field(description="Number of search results returned"),
    ] = 5,
) -> SearchLiteOutput:
    input_data = SearchLiteInput(query=query, count=count)
    search_component = ModelstudioSearchLite()
    result = await search_component.arun(input_data)
    print(result)
    return result


# ==================== MCP Tool Call Helper Functions ====================
# Use FastMCP Client standard API for tool listing and calling


async def list_mcp_tools() -> list[dict[str, Any]]:
    """
    Get MCP tool list using FastMCP Client via StreamableHttpTransport

    Connect to MCP Server via HTTP URL, using standard Streamable HTTP transport protocol.
    This approach is more suitable for production environments and easier to debug and monitor.
    """
    mcp_base_url = (
        f"http://{config.get('HOST', '127.0.0.1')}:{config.get('PORT', 8080)}"
    )

    print(f"\n{'=' * 60}")
    print("📋 [MCP Call] Get tool list")
    print(f"{'=' * 60}")
    print(f"Connection URL: {mcp_base_url}/mcp/")
    print("Transport method: StreamableHttpTransport")

    try:
        # Create FastMCP Client, pass HTTP URL
        # Client will automatically infer to use HTTP transport
        client = Client(f"{mcp_base_url}/mcp/")

        async with client:
            # Use standard list_tools() method
            tools = await client.list_tools()

            # Convert to dictionary format for subsequent processing
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema,
                }
                tools_list.append(tool_dict)

            print(f"✅ Successfully retrieved {len(tools_list)} tools")
            for i, tool in enumerate(tools_list, 1):
                print(f"  {i}. {tool['name']} - {tool['description']}")
            print(f"{'=' * 60}\n")

            return tools_list

    except Exception as e:
        print(f"❌ Failed to get tool list: {e}")
        print(f"{'=' * 60}\n")
        return []


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Call MCP tool using FastMCP Client via StreamableHttpTransport

    Connect to MCP Server via HTTP URL, using standard Streamable HTTP transport protocol.
    This approach is more suitable for production environments and easier to debug and monitor.
    """
    mcp_base_url = (
        f"http://{config.get('HOST', '127.0.0.1')}:{config.get('PORT', 8080)}"
    )

    print(f"\n{'=' * 60}")
    print("🔧 [MCP Call] Execute tool")
    print(f"{'=' * 60}")
    print(f"Connection URL: {mcp_base_url}/mcp/")
    print("Transport method: StreamableHttpTransport")
    print(f"Tool name: {tool_name}")
    print(
        f"Tool arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}",
    )

    try:
        # Create FastMCP Client, pass HTTP URL
        # Client will automatically infer to use HTTP transport
        client = Client(f"{mcp_base_url}/mcp/")

        async with client:
            # Use standard call_tool() method
            result = await client.call_tool(tool_name, arguments)

            # Process result
            # result.content is a list containing the content returned by the tool
            result_data = None
            if result.content:
                # Extract text content
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        result_data = content_item.text
                        break
                    if hasattr(content_item, "data"):
                        result_data = content_item.data
                        break

            print("✅ Tool execution successful")
            print(f"Result: {result_data}")
            print(f"{'=' * 60}\n")

            return result_data

    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        print(f"{'=' * 60}\n")
        return None


def convert_mcp_tools_to_openai_format(
    mcp_tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert MCP tool format to OpenAI function calling format
    """
    openai_tools = []

    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "inputSchema",
                    {"type": "object", "properties": {}, "required": []},
                ),
            },
        }
        openai_tools.append(openai_tool)

    return openai_tools
