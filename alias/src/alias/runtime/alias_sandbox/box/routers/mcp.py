# -*- coding: utf-8 -*-
import copy
import json
import logging
import os
import traceback

from fastapi import APIRouter, Body, HTTPException, Response

from .mcp_utils import MCPSessionHandler

mcp_router = APIRouter()

_MCP_SERVERS = {}
current_directory = os.path.dirname(os.path.abspath(__file__))
mcp_server_configs_path = os.path.abspath(
    os.path.join(current_directory, "../mcp_server_configs.json"),
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# NOTE: DO NOT use API-KEY Server in release version due to security issues
@mcp_router.post(
    "/mcp/add_servers",
    summary="Add and initialize MCP servers",
)
async def add_servers(
    server_configs: dict = Body(
        {},
        embed=True,
    ),
    overwrite: bool = Body(
        False,
        embed=True,
    ),
):
    global _MCP_SERVERS

    try:
        if not server_configs:
            raise HTTPException(
                status_code=400,
                detail="server_configs is required.",
            )

        new_servers = [
            MCPSessionHandler(name, config)
            for name, config in server_configs["mcpServers"].items()
        ]

        fail_servers = []

        # Initialize the servers
        for server in new_servers:
            if server.name in _MCP_SERVERS:
                if not overwrite:
                    continue
                # Cleanup old server
                await _MCP_SERVERS.pop(server.name).cleanup()
            try:
                await server.initialize()
                _MCP_SERVERS[server.name] = server
            except Exception as e:
                logging.error(f"Failed to initialize server: {e}")
                fail_servers.append(server)
                continue

        if fail_servers:
            for server in fail_servers:
                await server.cleanup()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize server: "
                f"{[server.name for server in fail_servers]}",
            )
        return Response(content="OK", status_code=200)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e


@mcp_router.get(
    "/mcp/list_tools",
    summary="List MCP tools",
)
async def list_tools():
    try:
        mcp_tools = {}

        for server_name, server in _MCP_SERVERS.items():
            tools = await server.list_tools()
            server_tools = {}
            for tool in tools:
                name = tool.name
                if name in server_tools:
                    logging.warning(
                        f"Service function `{name}` already exists, "
                        f"skip adding it.",
                    )
                else:
                    json_schema = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object",
                                "properties": tool.inputSchema.get(
                                    "properties",
                                    {},
                                ),
                                "required": tool.inputSchema.get(
                                    "required",
                                    [],
                                ),
                            },
                        },
                    }
                    server_tools[tool.name] = {
                        "name": tool.name,
                        "json_schema": json_schema,
                    }
            mcp_tools[server_name] = copy.deepcopy(server_tools)
        return mcp_tools
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e


@mcp_router.post(
    "/mcp/call_tool",
    summary="Execute MCP tool",
)
async def call_tool(
    tool_name: str = Body(
        ...,
        embed=True,
    ),
    arguments: dict = Body(
        {},
        embed=True,
    ),
) -> None:
    try:
        if not tool_name:
            raise HTTPException(
                status_code=400,
                detail="tool_name is required.",
            )

        tools = await list_tools()
        for server_name, server_tools in tools.items():
            if tool_name not in server_tools:
                continue
            server = _MCP_SERVERS[server_name]
            result = await server.call_tool(tool_name, arguments)
            return result.model_dump()
        raise ModuleNotFoundError(f"Tool '{tool_name}' not found.")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e


@mcp_router.on_event("shutdown")
async def cleanup_servers() -> None:
    """Clean up all servers properly."""
    global _MCP_SERVERS

    for server in reversed(list(_MCP_SERVERS.values())):
        try:
            await server.cleanup()
        except Exception as e:
            logging.error(f"Failed to cleanup server: {e}")

    _MCP_SERVERS = {}


@mcp_router.on_event("startup")
async def startup_event():
    # Load MCP server configs
    try:
        with open(mcp_server_configs_path, "r", encoding="utf-8") as file:
            mcp_server_configs = json.load(file)

    except Exception as e:
        logger.error(f"Failed to load MCP server configs: {e}")
        mcp_server_configs = {}

    # Call the add_servers function
    if mcp_server_configs:
        try:
            await add_servers(
                server_configs=mcp_server_configs,
                overwrite=False,
            )
        except Exception as e:
            logger.error(
                f"Failed to add MCP servers: {e}, {traceback.format_exc()}",
            )
