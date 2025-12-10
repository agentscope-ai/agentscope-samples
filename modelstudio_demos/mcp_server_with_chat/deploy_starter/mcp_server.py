"""
FastMCP Server 开发模版
这是一个基于 fastMcp 框架的 MCP Server 启动模版，让开发者可以快速开发自己的 MCP Server 并部署到阿里云百炼高代码

核心特性：
1. 使用 @mcp.tool() 装饰器快速定义工具
2. 内置健康检查接口
3. 支持http SSE,streamable连接方式
4. 提供完整的 MCP 协议支持（list tools、call tool 等）

开发者只需要专注于编写自己的工具函数即可。
"""
import json
import os
from typing import Optional, Annotated, List, Dict, Any

import uvicorn
from agentscope_runtime.tools import ModelstudioSearchLite
from agentscope_runtime.tools.searches import SearchLiteOutput, SearchLiteInput
from fastapi import FastAPI
from fastmcp import FastMCP
import asyncio
from fastmcp import FastMCP, Client

from pydantic import Field


# ==================== 配置读取 ====================

def read_config():
    """读取config.yml文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
    config = {}
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config[key] = value
    return config

config = read_config()

# ==================== 初始化 FastMCP ====================

# 创建 MCP 服务器实例，定义MCP name,版本
mcp = FastMCP(
    name=config.get('MCP_SERVER_NAME', "my-mcp-server"),
    version="1.0.0"
)

# ==================== 工具定义示例 ====================
# 开发者可以在这里定义自己的工具，使用 @mcp.tool() 装饰器

#示例tool1, 简单的加法tool,简单调用IO性能一般
@mcp.tool(
    name="add Tool",  # Custom tool name for the LLM
    description="一个简单的加法工具示例，用于计算两个整数的和",  # Custom description
)
def add_numbers(
        a: Annotated[int, Field(description="add a")],
        b: Annotated[int, Field(description="add b")]
) -> int:
    return a + b


#示例tool2, 阿里云百炼search,异步调用IO性能高
@mcp.tool(
    name="阿里云百炼search",  # Custom tool name for the LLM
    description="通过调用阿里云百炼search api封装搜索MCP，需要环境变量设置dashScope api key",  # Custom description
)
async def search_by_modelStudio(
        query :  Annotated[str, Field(description="搜索的query语句")],
        count :  Annotated[int, Field(description="搜索返回结果数")] = 5
) -> SearchLiteOutput:
    input_data = SearchLiteInput(
        query=query,
        count=count
    )
    search_component = ModelstudioSearchLite()
    result =  await search_component.arun(input_data)
    print(result)
    return result


# ==================== MCP工具调用辅助函数 ====================
# 使用 FastMCP Client 标准 API 进行工具列表获取和调用

async def list_mcp_tools() -> List[Dict[str, Any]]:
    """
    使用 FastMCP Client 通过 StreamableHttpTransport 获取 MCP 工具列表

    通过 HTTP URL 连接到 MCP Server，使用标准的 Streamable HTTP 传输协议。
    这种方式更符合生产环境的实践，且便于调试和监控。
    """
    mcp_base_url = f"http://{config.get('HOST', '127.0.0.1')}:{config.get('PORT', 8080)}"

    print(f"\n{'=' * 60}")
    print(f"📋 [MCP调用] 获取工具列表")
    print(f"{'=' * 60}")
    print(f"连接URL: {mcp_base_url}/mcp/")
    print(f"传输方式: StreamableHttpTransport")

    try:
        # 创建 FastMCP Client，传递 HTTP URL
        # Client 会自动推断使用 HTTP transport
        client = Client(f"{mcp_base_url}/mcp/")

        async with client:
            # 使用标准的 list_tools() 方法
            tools = await client.list_tools()

            # 转换为字典格式以便后续处理
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema
                }
                tools_list.append(tool_dict)

            print(f"✅ 成功获取 {len(tools_list)} 个工具")
            for i, tool in enumerate(tools_list, 1):
                print(f"  {i}. {tool['name']} - {tool['description']}")
            print(f"{'=' * 60}\n")

            return tools_list

    except Exception as e:
        print(f"❌ 获取工具列表失败: {e}")
        print(f"{'=' * 60}\n")
        return []


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    使用 FastMCP Client 通过 StreamableHttpTransport 调用 MCP 工具

    通过 HTTP URL 连接到 MCP Server，使用标准的 Streamable HTTP 传输协议。
    这种方式更符合生产环境的实践，且便于调试和监控。
    """
    mcp_base_url = f"http://{config.get('HOST', '127.0.0.1')}:{config.get('PORT', 8080)}"

    print(f"\n{'=' * 60}")
    print(f"🔧 [MCP调用] 执行工具")
    print(f"{'=' * 60}")
    print(f"连接URL: {mcp_base_url}/mcp/")
    print(f"传输方式: StreamableHttpTransport")
    print(f"工具名称: {tool_name}")
    print(f"工具参数: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

    try:
        # 创建 FastMCP Client，传递 HTTP URL
        # Client 会自动推断使用 HTTP transport
        client = Client(f"{mcp_base_url}/mcp/")

        async with client:
            # 使用标准的 call_tool() 方法
            result = await client.call_tool(tool_name, arguments)

            # 处理结果
            # result.content 是一个列表，包含工具返回的内容
            result_data = None
            if result.content:
                # 提取文本内容
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        result_data = content_item.text
                        break
                    elif hasattr(content_item, 'data'):
                        result_data = content_item.data
                        break

            print(f"✅ 工具执行成功")
            print(f"结果: {result_data}")
            print(f"{'=' * 60}\n")

            return result_data

    except Exception as e:
        print(f"❌ 工具执行失败: {e}")
        print(f"{'=' * 60}\n")
        return None


def convert_mcp_tools_to_openai_format(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将MCP工具格式转换为OpenAI function calling格式
    """
    openai_tools = []

    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
        }
        openai_tools.append(openai_tool)

    return openai_tools

# ==================== 更多工具示例 ====================
# 开发者可以继续添加更多工具 可以参考fastMcp Doc：https://gofastmcp.com/servers/tools


# # ==================== 自定义路由 ====================
# # 使用 @mcp.custom_route() 装饰器添加自定义 HTTP 路由
# 
# from starlette.requests import Request
# from starlette.responses import Response, JSONResponse
# 
# """健康检查接口,请勿修改"""
# @mcp.custom_route("/health", ["GET"])
# async def health_check(request: Request) -> Response:
#     return Response("OK")
# 
# 
# @mcp.custom_route("/", ["GET"])
# async def read_root(request: Request) -> Response:
#     """根路径信息"""
#     return JSONResponse({
#         "message": "MCP Server is running",
#         "version": "1.0.0",
#         "endpoints": {
#             "health": "/health",
#             "streamable-http": "/mcp",
#         }
#     })


# # ==================== 启动应用 ====================
# 
# if __name__ == '__main__':
#     # 使用 FastMCP 的 run 方法启动服务器
#     # 这会自动启动 HTTP 服务器并支持 MCP 协议
#     mcp.run(
#         transport="streamable-http",  # 使用 streamable-http 传输方式
#         host=config.get('FC_START_HOST', '127.0.0.1'),
#         port=config.get('PORT', 8080)
#     )