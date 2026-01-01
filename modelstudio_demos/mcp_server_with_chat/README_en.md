# FastMCP Server Development Template

> MCP Server development template based on FastMCP framework, quickly develop and deploy to Alibaba Cloud Bailian high-code platform

## 🎉 Features

Core features of this project:

- **🔧 Modular Architecture**: MCP Server code separated into `mcp_server.py`, main program `main.py` handles routing integration
- **💬 Chat API Integration**: New `/process` endpoint supporting Alibaba Cloud Bailian LLM calls and streaming responses
- **🤖 Intelligent Tool Calling**: LLM can automatically identify and call MCP tools (Function Calling)
- **📡 Unified Service Architecture**: FastAPI + FastMCP integration, one service providing both MCP and Chat functionality
- **🔄 Standardized Responses**: Structured streaming responses based on AgentScope ResponseBuilder
- **🌐 CORS Support**: Cross-origin requests supported for frontend integration
- **🎯 Route Optimization**: MCP Server mounted at `/mcp` path, main app provides more endpoints

## ⚡ Quick Start Locally

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Service

```bash
python -m deploy_starter.main
```

### 3. Verify Running

**Health Check:**
```bash
curl http://localhost:8080/health
```

**Test Chat Endpoint:**
```bash
curl -X POST http://localhost:8080/process \
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

![MCP inspector.png](MCP inspector.png)

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
    name="Alibaba Cloud Bailian search",
    description="Search via Alibaba Cloud Bailian API"
)
async def search_by_modelStudio(
    query: Annotated[str, Field(description="Search query statement")],
    count: Annotated[int, Field(description="Number of search results returned")] = 5
) -> SearchLiteOutput:
    input_data = SearchLiteInput(query=query, count=count)
    search_component = ModelstudioSearchLite()
    result = await search_component.arun(input_data)
    return result
```

**Note**: Async tools require setting the environment variable `DASHSCOPE_API_KEY` to call Bailian services
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
    description="Detailed tool description"      # Tool purpose description
)
def your_tool(
    param1: Annotated[str, Field(description="Description of parameter 1")],
    param2: Annotated[int, Field(description="Description of parameter 2")] = 10
) -> dict:
    # Your business logic
    return {"result": "success"}
```

---
## Alibaba Cloud Bailian High-Code Cloud Deployment

### Priority option: Upload code package directly through Alibaba Cloud Bailian high-code console
[Create Application - High-Code Application](https://bailian.console.aliyun.com//app-center?tab=app#/app-center)



### Command line console method for code upload and deployment - Better for quick code modifications and update deployments
#### 1. Install Dependencies

```bash
pip install agentscope-runtime==1.0.0
pip install "agentscope-runtime[deployment]==1.0.0"
```

#### 2. Set Environment Variables

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=...            # Your Alibaba Cloud AccessKey (required)
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...        # Your Alibaba Cloud SecurityKey (required)

# Optional: If you want to use separate OSS AK/SK, you can set the following (if not set, the above account AK/SK will be used), please ensure the account has OSS read/write permissions
export MODELSTUDIO_WORKSPACE_ID=...               # Your Bailian workspace ID
export OSS_ACCESS_KEY_ID=...
export OSS_ACCESS_KEY_SECRET=...
export OSS_REGION=cn-beijing
```

#### 3. Package and Deploy

##### Method A: Manually Build Wheel File

Ensure your project can be built as a wheel file. You can use setup.py, setup.cfg, or pyproject.toml.

Build wheel file:
```bash
python setup.py bdist_wheel
```

Deploy:
```bash
runtime-fc-deploy \
  --deploy-name [Your application name] \
  --whl-path [Relative path to your wheel file e.g. "/dist/your_app.whl"]
```


For details, please refer to the Alibaba Cloud Bailian high-code deployment documentation: [Alibaba Cloud Bailian High-Code Deployment Documentation](https://bailian.console.aliyun.com/?tab=api#/api/?type=app&url=2983030)

---

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
- `main.py`: FastAPI main app, provides `/process` endpoint and lifecycle management, mounts MCP Server at `/mcp` path
- `mcp_server.py`: FastMCP server instance, defines all MCP tools, provides tool list and call functions

---

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

# Alibaba Cloud Bailian API Key (optional, can also use environment variable)
# DASHSCOPE_API_KEY: "sk-xxx"
DASHSCOPE_MODEL_NAME: "qwen-plus"  # LLM model name
```

### DashScope API Configuration

To use Chat and LLM features, you need to configure the Alibaba Cloud Bailian DashScope API KEY:

1. Set `DASHSCOPE_API_KEY` in `deploy_starter/config.yml`:
   ```yaml
   DASHSCOPE_API_KEY: "sk-xxx"
   ```

2. Or set it as an environment variable:
   ```bash
   export DASHSCOPE_API_KEY="sk-xxx"
   ```

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

### Bailian High-Code Agent Integration

If your application is deployed to Bailian high-code platform, you can directly use the `/process` endpoint for Agent conversations, supporting:
- Natural language interaction
- Automatic tool calling
- Streaming responses
- Complete conversation context management

---

## 📚 API Endpoints

| Endpoint     | Method | Description |
|------------|------|------|
| `/`        | GET | Server information |
| `/health`  | GET | Health check (do not modify) |
| `/process` | POST | Chat endpoint, supports LLM conversation and tool calling (requires DASHSCOPE_API_KEY) |
| `/mcp`     | GET/POST | MCP Server endpoint (Streamable HTTP transport) |

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
