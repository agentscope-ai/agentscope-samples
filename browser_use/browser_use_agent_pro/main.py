# -*- coding: utf-8 -*-
"""Main entry point for browser-use agent"""
import os
import sys
import traceback
from pathlib import Path
import asyncio
from loguru import logger
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.mcp import StdIOStatefulClient
from agentscope.message import Msg
from _browser_agent import BrowserAgent

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

MODEL_FORMATTER_MAPPING = {
    "qwen3-max": [
        DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen3-max-preview",
            stream=True,
        ),
        DashScopeChatFormatter(),
    ],
    "qwen-vl-max": [
        DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen-vl-max-latest",
            stream=True,
        ),
        DashScopeChatFormatter(),
    ],
}

MODEL_CONFIG_NAME = os.getenv("MODEL", "qwen3-max")


async def run_browser_agent(
    task: str,
    start_url: str = "https://www.google.com",
):
    """Run the browser agent with a given task.

    Args:
        task: The task description for the browser agent
        start_url: The initial URL to navigate to

    Example:
        await run_browser_agent("Search for Python tutorials")
    """
    model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]

    # Create toolkit and MCP client
    browser_toolkit = Toolkit()
    browser_client = StdIOStatefulClient(
        name="playwright-mcp",
        command="npx",
        args=["@playwright/mcp@latest"],
    )

    try:
        await browser_client.connect()
        await browser_toolkit.register_mcp_client(browser_client)
        logger.info(
            "Init browser toolkit with MCP client (playwright-mcp)",
        )
    except Exception as e:
        logger.error(f"Failed to connect MCP client: {e}")
        try:
            await browser_client.close()
        except Exception:
            # Ignore errors when closing failed client connection
            pass
        raise

    try:
        browser_agent = BrowserAgent(
            name="BrowserUseAgentPro",
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=browser_toolkit,
            max_iters=50,
            start_url=start_url,
        )

        await browser_agent.reply(Msg(name="user", content=task, role="user"))
    except Exception as e:
        logger.error(f"Browser agent execution failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close MCP client
        if browser_client is not None:
            try:
                await browser_client.close()
                logger.info("MCP client closed successfully")
            except Exception as cleanup_error:
                logger.warning(
                    f"Error while closing MCP client: {cleanup_error}",
                )


async def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <task> [start_url]")
        sys.exit(1)

    task = sys.argv[1]
    start_url = sys.argv[2] if len(sys.argv) > 2 else "https://www.google.com"

    print("Starting Browser Agent Example...")
    print(
        "The browser agent will use "
        "playwright-mcp (https://github.com/microsoft/playwright-mcp). "
        "Make sure the MCP server can be installed "
        "by `npx @playwright/mcp@latest`",
    )

    await run_browser_agent(task=task, start_url=start_url)


if __name__ == "__main__":
    asyncio.run(main())
