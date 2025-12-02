# -*- coding: utf-8 -*-
# pylint: disable=R1724
from typing import Any, Callable

from loguru import logger

from agentscope.mcp import (
    MCPClientBase,
    StatefulClientBase,
    HttpStatelessClient,
)
from agentscope.message import TextBlock, ToolUseBlock
from agentscope.tool import ToolResponse, Toolkit

from alias.agent.tools.toolkit_hooks import (
    LongTextPostHook,
)
from alias.agent.tools.improved_tools import ImprovedFileOperations
from alias.agent.tools.tool_blacklist import TOOL_BLACKLIST
from alias.agent.tools.toolkit_hooks import read_file_post_hook
from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox


FilesystemSandbox = AliasSandbox


class AliasToolkit(Toolkit):
    def __init__(  # pylint: disable=W0102
        self,
        sandbox: AliasSandbox = None,
        add_all: bool = False,
        is_browser_toolkit: bool = False,
        tool_blacklist: list = TOOL_BLACKLIST,
    ):
        super().__init__()
        if sandbox is not None:
            self.sandbox = sandbox
            self.session_id = self.sandbox.sandbox_id
        else:
            logger.warning("Sandbox is None, use pure testing local mode!")
            self.sandbox = None
            self.session_id = None
        self.categorized_functions = {}
        self.tool_blacklist = tool_blacklist

        if add_all and sandbox:
            # Get tools
            tools_schema = self.sandbox.list_tools()
            for category, function_dicts in tools_schema.items():
                if (is_browser_toolkit and category == "playwright") or (
                    not is_browser_toolkit and category != "playwright"
                ):
                    for _, function_json in function_dicts.items():
                        if function_json["name"] not in self.tool_blacklist:
                            logger.info(f"add {function_json['name']}")
                            self._add_io_function(function_json)

            # for improved tools
            file_sys = ImprovedFileOperations(sandbox)
            self.register_tool_function(
                file_sys.read_file,
            )
        self.additional_mcp_clients = []

        self.long_text_post_hook = LongTextPostHook(sandbox)
        self._add_tool_postprocessing_func()

    def _add_io_function(
        self,
        json_schema: dict,
        is_browser_tool: bool = False,  # pylint: disable=W0613
    ) -> None:
        tool_name = json_schema["name"]

        def wrap_tool_func(name: str) -> Callable:
            def wrapper(**kwargs) -> ToolResponse:
                try:
                    # Call the sandbox tool with the extracted arguments
                    result = self.sandbox.call_tool(
                        name=name,
                        arguments=kwargs,
                    )
                    # Convert the result to ToolResponse format
                    if isinstance(result, dict) and "content" in result:
                        # If result already has content structure, use it
                        content = result["content"]
                        if isinstance(content, list):
                            for i, block in enumerate(content):
                                if (
                                    isinstance(block, dict)
                                    and "annotations" in block
                                ):
                                    block.pop("annotations")
                                    content[i] = block
                                if (
                                    isinstance(block, dict)
                                    and "description" in block
                                ):
                                    block.pop("description")
                                    content[i] = block
                    else:
                        # Otherwise, wrap the result in a TextBlock
                        content = [
                            TextBlock(
                                type="text",
                                text=str(result),
                            ),
                        ]

                    return ToolResponse(
                        metadata={"success": True, "tool_name": name},
                        content=content,
                    )

                except Exception as e:
                    logger.error(f"Error executing tool {name}: {str(e)}")
                    return ToolResponse(
                        metadata={
                            "success": False,
                            "tool_name": name,
                            "error": str(e),
                        },
                        content=[
                            TextBlock(
                                type="text",
                                text=f"Error executing tool {name}: {str(e)}",
                            ),
                        ],
                    )

            wrapper.__name__ = name
            return wrapper

        tool_func = wrap_tool_func(tool_name)

        self.register_tool_function(
            tool_func=tool_func,
            json_schema=json_schema.get("json_schema", {}),
        )

    def _add_tool_postprocessing_func(self) -> None:
        long_text_hook = LongTextPostHook(self.sandbox)
        for tool_func, _ in self.tools.items():
            if tool_func.startswith(("read_file", "read_multiple_files")):
                self.tools[tool_func].postprocess_func = read_file_post_hook
            if tool_func.startswith("tavily"):
                self.tools[
                    tool_func
                ].postprocess_func = long_text_hook.truncate_and_save_response

    async def add_and_connect_mcp_client(
        self,
        mcp_client: MCPClientBase,
        group_name: str = "basic",
        enable_funcs: list[str] | None = None,
        disable_funcs: list[str] | None = None,
        preset_kwargs_mapping: dict[str, dict[str, Any]] | None = None,
        postprocess_func: Callable[
            [
                ToolUseBlock,
                ToolResponse,
            ],
            ToolResponse | None,
        ]
        | None = None,
    ):
        """
        Add stateful MCP clients. No need to call `connect()` before add.
        """
        if isinstance(mcp_client, StatefulClientBase):
            await mcp_client.connect()
            self.additional_mcp_clients.append(mcp_client)
            await self.register_mcp_client(
                mcp_client,
                enable_funcs=enable_funcs,
                group_name=group_name,
                disable_funcs=disable_funcs,
                preset_kwargs_mapping=preset_kwargs_mapping,
                postprocess_func=postprocess_func,
            )
        elif isinstance(mcp_client, HttpStatelessClient):
            self.additional_mcp_clients.append(mcp_client)
            await self.register_mcp_client(
                mcp_client,
                enable_funcs=enable_funcs,
                group_name=group_name,
                disable_funcs=disable_funcs,
                preset_kwargs_mapping=preset_kwargs_mapping,
                postprocess_func=postprocess_func,
            )

        else:
            raise ValueError(
                "mcp_client must be either StatefulClientBase "
                "or StatelessClientBase",
            )

    async def close_mcp_clients(self) -> None:
        for client in reversed(self.additional_mcp_clients):
            if isinstance(client, StatefulClientBase):
                await client.close()
