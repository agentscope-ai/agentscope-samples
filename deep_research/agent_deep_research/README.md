# Deep Research Agent Example

## What This Example Demonstrates

This example shows a **DeepResearch Agent** implementation using the AgentScope framework. The DeepResearch Agent specializes in performing multi-step research to collect and integrate information from multiple sources, and generates comprehensive reports to solve complex tasks.
## Prerequisites

- Python 3.10 or higher
- Node.js and npm (for the MCP server)
- DashScope API key from [Alibaba Cloud](https://dashscope.console.aliyun.com/)
- ModelStudio Search from [Modelstudio Web Search](https://bailian.console.aliyun.com/?tab=app#/mcp-market/detail/WebSearch)
- （Optional）Tavily search API key from [Tavily](https://www.tavily.com/)

## How to Run This Example
1. **Set Environment Variable**:
   ```bash
   export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
   export TAVILY_API_KEY="your_tavily_api_key_here"
   export AGENT_OPERATION_DIR="your_own_direction_here"
   ```
2. **Test Tavily MCP Server**:
    ```bash
    npx -y tavily-mcp@latest
    ```

2. **Run the script**:
    ```bash
   python main.py
   ```
3. **Deploy the Deepresearch as service**:
    ```bash
   python deploy.py
   ```

Once run the deploy script, the deepresearch will run at `http://0.0.0.0:8090/process` with sync manner,
and a webui will start at `http://localhost:5173/`, then user could test the service at the webui.


## Connect to Web Search MCP client
The DeepResearch Agent supports web search from Tavily MCP client and modelstudio web search currently.
The default search tool is modelstudio web search.

To use Tavily MCP, you need to start the MCP server locally and establish a connection to it, which has been fulfilled.
```
from agentscope.mcp import StdIOStatefulClient

tavily_search_client= StdIOStatefulClient(
    name="tavily_mcp",
    command="npx",
    args=["-y", "tavily-mcp@latest"],
    env={"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")},
)
await tavily_search_client.connect()
```
and make sure disable modelstudio_web_search, and enable tavily-search, in `deep_research_agent.py` at line 170 and line 177, respectively.


> Note: The example is built with DashScope chat model. If you want to change the model in this example, don't forget
> to change the formatter at the same time! The corresponding relationship between built-in models and formatters are
> list in [our tutorial](https://doc.agentscope.io/tutorial/task_prompt.html#id1)
