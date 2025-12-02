# -*- coding: utf-8 -*-
import os
from typing import TYPE_CHECKING
import traceback
from agentscope.mcp import StdIOStatefulClient, HttpStatelessClient

from alias.agent.tools.improved_tools import DashScopeMultiModalTools
from alias.agent.tools.toolkit_hooks import LongTextPostHook

if TYPE_CHECKING:
    from alias.agent.tools.alias_toolkit import AliasToolkit
else:
    AliasToolkit = "alias.agent.tools.alias_toolkit.AliasToolkit"


async def add_tools(
    toolkit: AliasToolkit,
):
    """
    Adding additional MCP server to the toolkit for the application.
    Currently added MCP:
    - multimodal content to text tools (based on DashScope models)
    - tavily search
    """
    try:
        multimodal_tools = DashScopeMultiModalTools(
            sandbox=toolkit.sandbox,
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        )
        toolkit.register_tool_function(
            multimodal_tools.dashscope_audio_to_text,
        )
        toolkit.register_tool_function(
            multimodal_tools.dashscope_image_to_text,
        )
    except Exception as e:
        print(traceback.format_exc())
        raise e from None

    try:
        long_text_hook = LongTextPostHook(toolkit.sandbox)
        tavily_mcp_client = StdIOStatefulClient(
            name="tavily_mcp_client",
            command="npx",
            args=[
                "-y",
                "mcp-remote",
                "https://mcp.tavily.com/mcp/"
                f"?tavilyApiKey={os.getenv('TAVILY_API_KEY')}",
            ],
        )
        await toolkit.add_and_connect_mcp_client(
            tavily_mcp_client,
            enable_funcs=["tavily_search", "tavily_extract"],
            postprocess_func=long_text_hook.truncate_and_save_response,
        )
    except Exception as e:
        print(traceback.format_exc())
        raise e from None

    try:
        toolkit.create_tool_group(
            group_name="finance",
            description="Finance Analysis tools",
            active=True,
        )
        stock_data_client = HttpStatelessClient(
            "bailian_stock_data",
            "sse",
            "https://dashscope.aliyuncs.com/api/v1/mcps/tendency-software/sse",
            {
                "Authorization": f"Bearer {os.getenv('DASHSCOPE_MCP_API_KEY')}",  # noqa E501
            },
        )
        await toolkit.add_and_connect_mcp_client(
            stock_data_client,
            group_name="finance",
            enable_funcs=["tdx_wenda_quotes", "tdx_PBHQInfo_quotes"],
            postprocess_func=long_text_hook.truncate_and_save_response,
        )

        financial_advisory_client = HttpStatelessClient(
            "bailian_financial_advisory",
            "sse",
            "https://dashscope.aliyuncs.com/api/v1/mcps/Qieman/sse",
            {"Authorization": f"Bearer {os.getenv('DASHSCOPE_MCP_API_KEY')}"},
        )
        await toolkit.add_and_connect_mcp_client(
            financial_advisory_client,
            group_name="finance",
            enable_funcs=[
                "SearchHotTopic",
                # "SearchFinancialNews",
                "searchRealtimeAiAnalysis",
            ],
            postprocess_func=long_text_hook.truncate_and_save_response,
        )
    except Exception:
        from loguru import logger

        # pylint: disable=W0703
        logger.warning(
            "You do not register financial mcp tools successfully. "
            "Please export DASHSCOPE_MCP_API_KEY=YOUR_KEY and \n"
            "register Qieman tool at: https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/Qieman \n"  # pylint: disable=line-too-long # noqa E501
            "register tdx tool at: https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/tendency-software",  # pylint: disable=line-too-long # noqa E501
        )
