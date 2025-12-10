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

import os
import json
import asyncio
from typing import Optional, Annotated, List, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from agentscope_runtime.tools import ModelstudioSearchLite
from agentscope_runtime.tools.searches import SearchLiteOutput, SearchLiteInput
from agentscope_runtime.engine.helpers.agent_api_builder import ResponseBuilder
from agentscope_runtime.engine.schemas.agent_schemas import Role
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastmcp import FastMCP, Client
from pydantic import Field, BaseModel
from openai import AsyncOpenAI
from starlette.middleware.cors import CORSMiddleware

# 导入MCP Server实例
from deploy_starter.mcp_server import mcp, convert_mcp_tools_to_openai_format, list_mcp_tools, call_mcp_tool


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

# ==================== 创建 MCP ASGI 应用 ====================
# 提前创建 MCP 应用实例，以便在 lifespan 和 mount 中重用
mcp_asgi_app = mcp.streamable_http_app(path="/")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 集成 MCP 应用的 lifespan"""
    # 使用 MCP 应用的 lifespan 上下文管理器
    async with mcp_asgi_app.router.lifespan_context(app):
        # 应用启动完成，进入运行状态
        yield
        # 应用关闭时会自动清理

# 创建FastAPI应用
app = FastAPI(
    title=config.get('APP_NAME', 'MCP Server with Chat'),
    debug=config.get('DEBUG', False),
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 或 ["*"] 仅用于开发
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 挂载MCP Server路由 ====================
# 将MCP Server的路由集成到主应用中
# 这样只需要启动一个服务器就可以同时提供MCP工具和Chat接口
# 注意：mcp_asgi_app 已经在上面创建，这里直接使用

# 将MCP路由挂载到主应用的 /mcp 路径下
app.mount("/mcp", mcp_asgi_app)

@app.get("/")
def read_root():
    return "<h1>hi, i'm running</h1>"

@app.get("/health")
def health_check():
    return "OK"


class ContentItem(BaseModel):
    type: str  # 例如: "text", "data" 等
    text: Optional[str] = None  # 文本内容（可选）
    data: Optional[Dict[str, Any]] = None  # 数据内容（可选）
    status: Optional[str] = None  # 状态
    
    class Config:
        extra = "allow"  # 允许额外字段

class MessageItem(BaseModel):
    role: str  # 例如: "user", "assistant"
    content: Optional[List[ContentItem]] = None  # content 数组（可选）
    type: Optional[str] = None  # 消息类型：message、plugin_call、plugin_call_output 等
    
    class Config:
        extra = "allow"  # 允许额外字段（如 sequence_number、object、status、id 等）

class ChatRequest(BaseModel):
    input: List[MessageItem]  # 消息数组
    session_id: str  # 会话ID
    stream: Optional[bool] = True  # 是否流式响应


# ==================== Chat接口实现 ====================

#百炼示例chat调用接口，需配置DASHSCOPE_API_KEY
@app.post("/chat")
async def chat(request_data: ChatRequest):
    """
    Chat接口实现，支持LLM调用和MCP工具调用
    
    核心流程：
    1. 接收用户消息
    2. 获取MCP工具列表
    3. 调用LLM（带function calling）
    4. 如果LLM需要调用工具，则调用MCP工具
    5. 将工具结果返回给LLM
    6. 返回最终响应（符合AgentScope ResponseBuilder格式）
    """
    
    # 获取DashScope API Key
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        api_key = config.get("DASHSCOPE_API_KEY")
    
    if not api_key:
        return {"error": "DASHSCOPE_API_KEY not configured"}
    
    # 初始化OpenAI客户端（DashScope兼容OpenAI API）
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 转换消息格式为OpenAI格式
    # 保留对话历史：user 消息 + assistant 的最终回答（type="message"）
    # 忽略中间步骤：plugin_call、plugin_call_output、reasoning
    messages = []
    for msg in request_data.input:
        # 处理 user 消息
        if msg.role == "user":
            content_text = ""
            if msg.content:
                for content_item in msg.content:
                    if content_item.type == "text" and content_item.text:
                        content_text += content_item.text
            
            if content_text:  # 只添加非空消息
                messages.append({
                    "role": "user",
                    "content": content_text
                })
        
        # 处理 assistant 的最终回答（type="message"）
        elif msg.role == "assistant" and msg.type == "message":
            content_text = ""
            if msg.content:
                for content_item in msg.content:
                    if content_item.type == "text" and content_item.text:
                        content_text += content_item.text
            
            if content_text:
                messages.append({
                    "role": "assistant",
                    "content": content_text
                })
    
    # 获取MCP工具列表
    try:
        mcp_tools = await list_mcp_tools()
        openai_tools = convert_mcp_tools_to_openai_format(mcp_tools)
    except Exception as e:
        print(f"获取MCP工具失败: {e}")
        openai_tools = []
    
    async def generate_response():
        """生成流式响应 - 符合百炼 Response/Message/Content 架构"""
        # 创建ResponseBuilder
        response_builder = ResponseBuilder(
            session_id=request_data.session_id,
            response_id=f"resp_{request_data.session_id}"
        )
        
        # 1. 发送 Response created 状态
        yield f"data: {response_builder.created().model_dump_json()}\n\n"
        
        # 2. 发送 Response in_progress 状态
        yield f"data: {response_builder.in_progress().model_dump_json()}\n\n"
        
        try:
            # 第一阶段：LLM 初始响应（可能包含工具调用决策）
            if openai_tools:
                response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    tools=openai_tools,
                    stream=True
                )
            else:
                response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    stream=True
                )
            
            # 收集 LLM 响应内容和工具调用
            llm_content = ""
            tool_calls = []
            current_tool_call = None
            
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # 收集文本内容
                    if delta.content:
                        llm_content += delta.content
                    
                    # 收集工具调用
                    if delta.tool_calls:
                        for tool_call_chunk in delta.tool_calls:
                            if tool_call_chunk.index is not None:
                                if current_tool_call is None or current_tool_call["index"] != tool_call_chunk.index:
                                    if current_tool_call:
                                        tool_calls.append(current_tool_call)
                                    current_tool_call = {
                                        "index": tool_call_chunk.index,
                                        "id": tool_call_chunk.id or "",
                                        "type": "function",
                                        "function": {
                                            "name": tool_call_chunk.function.name or "",
                                            "arguments": tool_call_chunk.function.arguments or ""
                                        }
                                    }
                                else:
                                    if tool_call_chunk.function.arguments:
                                        current_tool_call["function"]["arguments"] += tool_call_chunk.function.arguments
            
            if current_tool_call:
                tool_calls.append(current_tool_call)
            
            # 根据是否有工具调用决定消息流程
            if tool_calls:
                # 场景：有工具调用
                # 3. 创建 reasoning message（如果 LLM 有思考内容）
                if llm_content.strip():
                    reasoning_msg_builder = response_builder.create_message_builder(
                        role=Role.ASSISTANT, 
                        message_type="reasoning"
                    )
                    yield f"data: {reasoning_msg_builder.get_message_data().model_dump_json()}\n\n"
                    
                    reasoning_content_builder = reasoning_msg_builder.create_content_builder()
                    yield f"data: {reasoning_content_builder.add_text_delta(llm_content).model_dump_json()}\n\n"
                    yield f"data: {reasoning_content_builder.complete().model_dump_json()}\n\n"
                    yield f"data: {reasoning_msg_builder.complete().model_dump_json()}\n\n"
                
                # 4. 先添加 assistant 消息（包含所有工具调用）到消息历史
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                
                # 5. 处理每个工具调用
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    try:
                        tool_args = json.loads(tool_call["function"]["arguments"])
                    except:
                        tool_args = {}
                    
                    # 5.1 创建 plugin_call message（显示给用户）
                    plugin_call_msg_builder = response_builder.create_message_builder(
                        role=Role.ASSISTANT,
                        message_type="plugin_call"
                    )
                    yield f"data: {plugin_call_msg_builder.get_message_data().model_dump_json()}\n\n"
                    
                    plugin_call_content_builder = plugin_call_msg_builder.create_content_builder(content_type="data")
                    tool_call_data = {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, ensure_ascii=False)
                    }
                    yield f"data: {plugin_call_content_builder.add_data_delta(tool_call_data).model_dump_json()}\n\n"
                    yield f"data: {plugin_call_content_builder.complete().model_dump_json()}\n\n"
                    yield f"data: {plugin_call_msg_builder.complete().model_dump_json()}\n\n"
                    
                    # 5.2 调用 MCP 工具
                    try:
                        tool_result = await call_mcp_tool(tool_name, tool_args)
                        
                        # 5.3 创建 plugin_call_output message（显示给用户）
                        plugin_output_msg_builder = response_builder.create_message_builder(
                            role=Role.ASSISTANT,
                            message_type="plugin_call_output"
                        )
                        yield f"data: {plugin_output_msg_builder.get_message_data().model_dump_json()}\n\n"
                        
                        plugin_output_content_builder = plugin_output_msg_builder.create_content_builder(content_type="data")
                        output_data = {
                            "name": tool_name,
                            "output": json.dumps(tool_result, ensure_ascii=False) if tool_result else ""
                        }
                        yield f"data: {plugin_output_content_builder.add_data_delta(output_data).model_dump_json()}\n\n"
                        yield f"data: {plugin_output_content_builder.complete().model_dump_json()}\n\n"
                        yield f"data: {plugin_output_msg_builder.complete().model_dump_json()}\n\n"
                        
                        # 添加 tool 消息到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(tool_result, ensure_ascii=False) if tool_result else ""
                        })
                    except Exception as e:
                        print(f"工具调用失败: {e}")
                        # 添加错误结果到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": f"Error: {str(e)}"
                        })
                
                # 6. 使用工具结果再次调用 LLM 生成最终回答
                final_response = await client.chat.completions.create(
                    model=config.get("DASHSCOPE_MODEL_NAME", "qwen-plus"),
                    messages=messages,
                    stream=True
                )
                
                # 7. 创建最终 message（基于工具结果的回答）
                final_msg_builder = response_builder.create_message_builder(
                    role=Role.ASSISTANT,
                    message_type="message"
                )
                yield f"data: {final_msg_builder.get_message_data().model_dump_json()}\n\n"
                
                final_content_builder = final_msg_builder.create_content_builder()
                
                async for chunk in final_response:
                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            yield f"data: {final_content_builder.add_text_delta(choice.delta.content).model_dump_json()}\n\n"
                
                yield f"data: {final_content_builder.complete().model_dump_json()}\n\n"
                yield f"data: {final_msg_builder.complete().model_dump_json()}\n\n"
                
            else:
                # 场景：无工具调用，直接返回 LLM 响应
                # 3. 创建 message（直接回答）
                msg_builder = response_builder.create_message_builder(
                    role=Role.ASSISTANT,
                    message_type="message"
                )
                yield f"data: {msg_builder.get_message_data().model_dump_json()}\n\n"
                
                content_builder = msg_builder.create_content_builder()
                yield f"data: {content_builder.add_text_delta(llm_content).model_dump_json()}\n\n"
                yield f"data: {content_builder.complete().model_dump_json()}\n\n"
                yield f"data: {msg_builder.complete().model_dump_json()}\n\n"
            
            # 8. 完成 Response
            yield f"data: {response_builder.completed().model_dump_json()}\n\n"
            # yield "data: [DONE]\n\n"
            
        except Exception as e:
            # 错误处理
            print(f"Chat接口错误: {e}")
            error_msg_builder = response_builder.create_message_builder(
                role=Role.ASSISTANT,
                message_type="error"
            )
            error_content_builder = error_msg_builder.create_content_builder()
            error_text = f"发生错误: {str(e)}"
            yield f"data: {error_content_builder.add_text_delta(error_text).model_dump_json()}\n\n"
            yield f"data: {error_content_builder.complete().model_dump_json()}\n\n"
            yield f"data: {error_msg_builder.complete().model_dump_json()}\n\n"
            yield f"data: {response_builder.completed().model_dump_json()}\n\n"
            # yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )


# ==================== 启动应用 ====================

if __name__ == '__main__':
    # 启动FastAPI应用
    uvicorn.run(
        app,
        host=config.get('FC_START_HOST', '127.0.0.1'),
        port=config.get('PORT', 8080)
    )