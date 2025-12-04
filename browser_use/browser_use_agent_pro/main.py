# -*- coding: utf-8 -*-
"""Main entry point for browser-use agent"""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
import asyncio
from loguru import logger

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.mcp import StdIOStatefulClient

from _browser_agent import BrowserAgent



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
    toolkit: Toolkit | None = None,
    start_url: str = "https://www.bing.com",
    mcp_client: StdIOStatefulClient | None = None,
):
    """Run the browser agent with a given task.
    
    Args:
        task: The task description for the browser agent
        toolkit: Optional toolkit instance. If None, will create a new Toolkit with MCP client.
                 Should be a standard Toolkit with MCP clients registered (e.g., playwright-mcp).
        start_url: The initial URL to navigate to
        mcp_client: Optional MCP client. If toolkit is None, will create a playwright-mcp client.
                    If toolkit is provided, this parameter is ignored.
    
    Example:
        # Using default Toolkit with MCP client (created automatically)
        await run_browser_agent("Search for Python tutorials")
        
        # Providing a custom Toolkit with MCP client
        from agentscope.tool import Toolkit
        from agentscope.mcp import StdIOStatefulClient
        toolkit = Toolkit()
        browser_client = StdIOStatefulClient(
            name="playwright-mcp",
            command="npx",
            args=["@playwright/mcp@latest"]
        )
        await browser_client.connect()
        await toolkit.register_mcp_client(browser_client)
        await run_browser_agent("Search for Python tutorials", toolkit=toolkit)
    """
    model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
    
    # Create toolkit and MCP client if not provided
    browser_client = None
    if toolkit is None:
        # Create toolkit
        browser_toolkit = Toolkit()
        
        # Create and connect MCP client
        if mcp_client is None:
            browser_client = StdIOStatefulClient(
                name="playwright-mcp",
                command="npx",
                args=["@playwright/mcp@latest"],
            )
        else:
            browser_client = mcp_client
        
        try:
            await browser_client.connect()
            await browser_toolkit.register_mcp_client(browser_client)
            logger.info("Init browser toolkit with MCP client (playwright-mcp)")
        except Exception as e:
            logger.error(f"Failed to connect MCP client: {e}")
            if browser_client:
                try:
                    await browser_client.close()
                except Exception:
                    pass
            raise
    else:
        browser_toolkit = toolkit
        logger.info("Using provided toolkit")
    
    try:
        browser_agent = BrowserAgent(
            name="BrowserBot",
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=browser_toolkit,
            max_iters=50,
            start_url=start_url,
        )
        from agentscope.message import Msg
        await browser_agent.reply(Msg(name="user", content=task, role="user"))
    except Exception as e:
        logger.error(f"---> Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close MCP client if we created it
        if browser_client is not None:
            try:
                await browser_client.close()
                logger.info("MCP client closed successfully")
            except Exception as cleanup_error:
                logger.warning(f"Error while closing MCP client: {cleanup_error}")
        # Close MCP clients if the toolkit supports it
        elif hasattr(browser_toolkit, 'close_mcp_clients'):
            try:
                await browser_toolkit.close_mcp_clients()
            except Exception as cleanup_error:
                logger.warning(f"Error while closing toolkit MCP clients: {cleanup_error}")


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <task> [start_url]")
        print("Example: python main.py 'Search for Python tutorials' 'https://www.google.com'")
        print("\nNote: This requires playwright-mcp to be available via npx.")
        print("Make sure you can run: npx @playwright/mcp@latest")
        sys.exit(1)
    
    task = sys.argv[1]
    start_url = sys.argv[2] if len(sys.argv) > 2 else "https://www.bing.com"
    
    print("Starting Browser Agent Example...")
    print(
        "The browser agent will use "
        "playwright-mcp (https://github.com/microsoft/playwright-mcp). "
        "Make sure the MCP server can be installed "
        "by `npx @playwright/mcp@latest`"
    )
    
    await run_browser_agent(task=task, start_url=start_url)


if __name__ == "__main__":
    asyncio.run(main())

