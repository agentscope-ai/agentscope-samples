# -*- coding: utf-8 -*-
# pylint: disable=W0612,E0611,C2801
import os
import traceback
from datetime import datetime

from loguru import logger

from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import StdIOStatefulClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope_runtime.sandbox.box.sandbox import Sandbox

from alias.agent.agents import BrowserAgent, DeepResearchAgent, MetaPlanner
from alias.agent.agents._planning_tools._worker_manager import share_tools
from alias.agent.mock import MockSessionService
from alias.agent.tools import AliasToolkit
from alias.agent.tools.improved_tools import DashScopeMultiModalTools
from alias.agent.tools.toolkit_hooks import LongTextPostHook
from alias.agent.utils.constants import BROWSER_AGENT_DESCRIPTION

# Open source version always uses mock services
SessionService = MockSessionService


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
    # "gpt-5": [
    #     OpenAIChatModel(
    #         api_key=os.environ.get("OPENAI_API_KEY"),
    #         model_name="gpt-5-2025-08-07",
    #         stream=True,
    #     ),
    #     OpenAIChatFormatter(),
    # ],
    # "claude-4": [
    #     AnthropicChatModel(
    #         api_key=os.environ.get("ANTHROPIC_API_KEY"),
    #         model_name="claude-sonnet-4-20250514",
    #         stream=True,
    #     ),
    #     AnthropicChatFormatter(),
    # ],
}


MODEL_CONFIG_NAME = os.getenv("MODEL", "qwen3-max")
VL_MODEL_NAME = os.getenv("VISION_MODEL", "qwen-vl-max")


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
        await toolkit.add_and_connet_mcp_client(
            tavily_mcp_client,
            enable_funcs=["tavily_search", "tavily_extract"],
            postprocess_func=long_text_hook.truncate_and_save_response,
        )
    except Exception as e:
        print(traceback.format_exc())
        raise e from None


async def arun_agents(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
    enable_clarification: bool = True,
):
    time_str = datetime.now().strftime("%Y%m%d%H%M%S")

    # Initialize toolkit
    worker_full_toolkit = AliasToolkit(sandbox, add_all=True)
    await add_tools(
        worker_full_toolkit,
    )
    logger.info("Init full toolkit")

    # Browser agent uses traditional toolkit for compatibility
    browser_toolkit = AliasToolkit(
        sandbox,
        is_browser_toolkit=True,
        add_all=True,
    )
    logger.info("Init browser toolkit")

    try:
        model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
        browser_agent = BrowserAgent(
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=browser_toolkit,
            max_iters=50,
            start_url="https://www.google.com",
            session_service=session_service,
            state_saving_dir=f"./agent-states/run-{time_str}",
        )
        meta_planner = MetaPlanner(
            model=model,
            formatter=formatter,
            toolkit=AliasToolkit(sandbox=sandbox, add_all=False),
            worker_full_toolkit=worker_full_toolkit,
            browser_toolkit=browser_toolkit,
            agent_working_dir="/workspace",
            memory=InMemoryMemory(),
            state_saving_dir=f"./agent-states/run-{time_str}",
            max_iters=100,
            session_service=session_service,
            enable_clarification=enable_clarification,
        )
        meta_planner.worker_manager.register_worker(
            browser_agent,
            description=BROWSER_AGENT_DESCRIPTION,
            worker_type="built-in",
        )
        msg = await meta_planner()
    except Exception as e:
        print(traceback.format_exc())
        raise e from None
    finally:
        await worker_full_toolkit.close_mcp_clients()
    return meta_planner, msg


async def test_deepresearch_agent(
    task_str: str,
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
    instruction = Msg(
        "user",
        content=task_str,
        role="user",
    )

    global_toolkit = AliasToolkit(sandbox, add_all=True)
    await add_tools(global_toolkit)
    worker_toolkit = AliasToolkit(sandbox)
    model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
    test_tool_list = [
        "tavily_search",
        "tavily_extract",
        "write_file",
        "create_directory",
        "list_directory",
        "read_file",
        "run_shell_command",
    ]
    share_tools(global_toolkit, worker_toolkit, test_tool_list)
    try:
        worker_agent = DeepResearchAgent(
            name="Deep_Research_Assistant",
            sys_prompt=(
                "You are a helpful assistant that can use provided tools "
                "to help finish tasks."
            ),
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=worker_toolkit,
            session_service=session_service,
        )
        await worker_agent(instruction)
    except Exception as e:
        logger.error(f"---> Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        await global_toolkit.close_mcp_clients()


async def test_browseruse_agent(
    task_str: str,
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
    time_str = datetime.now().strftime("%Y%m%d%H%M%S")
    instruction = Msg(
        "user",
        content=task_str,
        role="user",
    )

    model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
    browser_toolkit = AliasToolkit(
        sandbox,
        add_all=True,
        is_browser_toolkit=True,
    )
    logger.info("Init browser toolkit")
    try:
        browser_agent = BrowserAgent(
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=browser_toolkit,
            max_iters=50,
            start_url="https://www.google.com",
            session_service=session_service,
            state_saving_dir=f"./agent-states/run_browser-{time_str}",
        )
        await browser_agent(instruction)
    except Exception as e:
        logger.error(f"---> Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        await browser_toolkit.close_mcp_clients()
