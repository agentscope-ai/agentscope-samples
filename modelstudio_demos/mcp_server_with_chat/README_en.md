# FastMCP Server Development Template

> MCP Server development template based on FastMCP framework, quickly develop and deploy to Alibaba Cloud ModelStudio high-code platform

## 🎉 Latest Refactoring Features

This project has undergone a comprehensive refactoring with the following new core features:

- **🔧 Modular Architecture**: MCP Server code separated into `mcp_server.py`, main program `main.py` handles routing integration
- **💬 Chat API Integration**: New `/chat` endpoint supporting Alibaba Cloud ModelStudio LLM calls and streaming responses
- **🤖 Intelligent Tool Calling**: LLM can automatically identify and call MCP tools (Function Calling)
- **📡 Unified Service Architecture**: FastAPI + FastMCP integration, one service providing both MCP and Chat functionality
- **🔄 Standardized Responses**: Structured streaming responses based on AgentScope ResponseBuilder
- **🌐 CORS Support**: Cross-origin requests supported for frontend integration
- **🎯 Route Optimization**: MCP Server mounted at `/mcp` path, main app provides more endpoints

## Project Introduction

This is a starter project based on FastAPI Web framework and FastMCP, providing you with an initial template for developing and deploying MCP Servers locally or via Alibaba Cloud ModelStudio high-code cloud deployment.
It supports direct local running and testing, allowing you to freely code and assemble atomic capabilities such as LLM, MCP tools, RAG, memory, and search from Alibaba Cloud ModelStudio & AgentScope.

## ⚡ Quick Start

### 1. Install Dependencies

First, make sure you have Python 3.10 or higher installed.

```bash
pip install -r requirements.txt
```

### Dependency Description

- `fastapi`: For building Web APIs
- `uvicorn`: For running FastAPI applications
- `fastmcp`: FastMCP framework for MCP Server development
- `agentscope-runtime`: AgentScope runtime environment
- `openai`: OpenAI SDK (for DashScope API compatibility)
- `PyYAML`: YAML configuration parsing

## 🔧 Configuration

Edit `deploy_starter/config.yml`:

```yaml
# MCP Server Configuration
MCP_SERVER_NAME: "my-mcp-server"
MCP_SERVER_VERSION: "1.0.0"

# Server Configuration
FC_START_HOST: "0.0.0.0"  # For cloud deployment
PORT: 8080
HOST: "127.0.0.1"  # For local development

# Alibaba Cloud ModelStudio API Key (optional, can also use environment variable)
# DASHSCOPE_API_KEY: "sk-xxx"
DASHSCOPE_MODEL_NAME: "qwen-plus"  # LLM model name
```

### DashScope API Configuration

To use Chat and LLM features, you need to configure the Alibaba Cloud ModelStudio DashScope API KEY:

1. Set `DASHSCOPE_API_KEY` in `deploy_starter/config.yml`:
   ```yaml
   DASHSCOPE_API_KEY: "sk-xxx"
   ```

2. Or set it as an environment variable:
   ```bash
   export DASHSCOPE_API_KEY="sk-xxx"
   ```

### 2. Start the Service

```bash
python -m deploy_starter.main
```

Or with Uvicorn:

```bash
uvicorn deploy_starter.main:app --host 127.0.0.1 --port 8080 --reload
```

### 3. Verify Running

**Health Check:**
```bash
curl http://localhost:8080/health
```

**Test Chat Endpoint:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello"}]
      }
    ],
    "session_id": "test-session-001",
    "stream": true
  }'
```

### 4. Recommended: Use MCP Inspector to Verify MCP Server Locally

```bash
npx @modelcontextprotocol/inspector
```
Connect to: `http://localhost:8080/mcp`

---

## 🛠️ Develop Your First MCP Tool

Define tools in `deploy_starter/mcp_server.py` using the `@mcp.tool()` decorator:

> **Note**: After refactoring, all MCP tool definitions are in `mcp_server.py`, while `main.py` handles integration and routing

### Example 1: Synchronous Tool (Simple call, average IO performance)

```python
from typing import Annotated
from pydantic import Field

@mcp.tool(
    name="add Tool",
    description="A simple addition tool example"
)
def add_numbers(
    a: Annotated[int, Field(description="add a")],
    b: Annotated[int, Field(description="add b")]
) -> int:
    return a + b
```

### Example 2: Asynchronous Tool (Async call, high IO performance)

```python
@mcp.tool(
    name="Alibaba Cloud ModelStudio Search",
    description="Search via Alibaba Cloud ModelStudio API"
)
async def search_by_modelStudio(
    query: Annotated[str, Field(description="Search query statement")],
    count: Annotated[int, Field(description="Number of search results")] = 5
) -> SearchLiteOutput:
    input_data = SearchLiteInput(query=query, count=count)
    search_component = ModelstudioSearchLite()
    result = await search_component.arun(input_data)
    return result
```

**Note**: Async tools require setting the environment variable `DASHSCOPE_API_KEY` to call ModelStudio services:
```bash
export DASHSCOPE_API_KEY='sk-xxxxxx'
```

---

## 📝 Parameter Description Specification

Use `Annotated` + `Field` to add descriptions for each parameter:

```python
from typing import Annotated, Optional
from pydantic import Field

@mcp.tool(
    name="your_tool_name",           # Tool name (what AI sees)
    description="Detailed tool description"  # Tool purpose description
)
def your_tool(
    param1: Annotated[str, Field(description="Description of parameter 1")],
    param2: Annotated[int, Field(description="Description of parameter 2")] = 10
) -> dict:
    # Your business logic
    return {"result": "success"}
```

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/` | GET | Server information |
| `/health` | GET | Health check (do not modify) |
| `/chat` | POST | Chat endpoint, supports LLM conversation and tool calling (requires DASHSCOPE_API_KEY) |
| `/mcp` | GET/POST | MCP Server endpoint (Streamable HTTP transport) |

### Chat Endpoint Details

**Request Format:**
```json
{
  "input": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "User message"}
      ]
    }
  ],
  "session_id": "Session ID",
  "stream": true
}
```

**Response Format:**
- Streaming response (SSE), complies with AgentScope ResponseBuilder standard
- Supports multiple message types: `message` (normal answer), `reasoning` (thinking process), `plugin_call` (tool call), `plugin_call_output` (tool output)

**Core Features:**
- ✅ Automatically identify and call MCP tools
- ✅ Support multi-turn conversation context
- ✅ Streaming response, real-time results
- ✅ Transparent tool calling process

## Notes

1. Chat functionality will be unavailable if `DASHSCOPE_API_KEY` is not configured.
2. The default model is `qwen-plus`. You can change `DASHSCOPE_MODEL_NAME` in `config.yml` to switch models.

## 📋 Project Structure

```
.
├── deploy_starter/
│   ├── main.py          # Main program - FastAPI app entry, integrates Chat and MCP routing
│   ├── mcp_server.py    # MCP Server definition - Define your MCP tools here
│   └── config.yml       # Configuration file
├── requirements.txt     # Dependency list
├── setup.py            # Package configuration (for cloud deployment)
├── README_zh.md        # Chinese documentation
└── README_en.md        # English documentation
```

**Core Files Description:**
- `main.py`: FastAPI main app, provides `/chat` endpoint and lifecycle management, mounts MCP Server at `/mcp` path
- `mcp_server.py`: FastMCP server instance, defines all MCP tools, provides tool list and call functions

---

## 💡 Development Suggestions

### Synchronous vs Asynchronous Tools

- **Synchronous Tools**: Suitable for simple calculations, local operations
  ```python
  @mcp.tool()
  def sync_tool(param: str) -> str:
      return f"processed: {param}"
  ```

- **Asynchronous Tools**: Suitable for API calls, database queries, I/O operations
  ```python
  @mcp.tool()
  async def async_tool(param: str) -> str:
      result = await some_api_call(param)
      return result
  ```

### Tool Naming Conventions

- `name`: Tool name visible to AI (supports Chinese)
- `description`: Detailed explanation of tool purpose, helps AI understand when to call

---

## 🎯 Using in AI Clients

### Claude Desktop

Edit the configuration file `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "python",
      "args": ["-m", "deploy_starter.main"],
      "env": {}
    }
  }
}
```

### Cursor / Cline

Connect to MCP Server URL:
```
http://localhost:8080/mcp
```

### ModelStudio High-Code Agent Integration

If your application is deployed to ModelStudio high-code, you can directly use the `/chat` endpoint for Agent conversations, supporting:
- Natural language interaction
- Automatic tool calling
- Streaming responses
- Complete conversation context management

---

## 🚀 Deploy to Alibaba Cloud ModelStudio

### Step 1: Install Deployment Tools

```bash
pip install agentscope-runtime
pip install "agentscope-runtime[deployment]"
```

### Step 2: Configure Environment Variables

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="Your Alibaba Cloud AccessKey"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="Your Alibaba Cloud SecretKey"
export MODELSTUDIO_WORKSPACE_ID="Your ModelStudio Workspace ID"
```

### Step 3: Package and Deploy

```bash
# 1. Build wheel package
python setup.py bdist_wheel

# 2. Deploy to cloud
runtime-fc-deploy \
  --deploy-name my-mcp-server \
  --whl-path dist/mcp-server-starter-0.1.0-py3-none-any.whl
```

After successful deployment, you will get a cloud URL that can be used in Claude Desktop or other MCP clients.

---

**Optional: Advanced Deployment Configuration**

```bash
# Optional: If you want to use separate OSS AK/SK
export OSS_ACCESS_KEY_ID=...
export OSS_ACCESS_KEY_SECRET=...
export OSS_REGION=cn-beijing
```

For details, please refer to the [Alibaba Cloud ModelStudio High-Code Deployment Documentation](https://bailian.console.aliyun.com/?tab=api#/api/?type=app&url=2983030)
