# -*- coding: utf-8 -*-
# pylint: disable=W0612,E0611,C2801
import os
import traceback
from datetime import datetime
import asyncio
from typing import Literal

from loguru import logger

from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope_runtime.sandbox.box.sandbox import Sandbox

from alias.agent.agents import (
    BrowserAgent,
    DeepResearchAgent,
    MetaPlanner,
    DataScienceAgent,
    init_ds_toolkit,
    init_dr_toolkit,
)
from alias.agent.agents.meta_planner_utils._worker_manager import share_tools
from alias.agent.mock import MockSessionService as SessionService
from alias.agent.tools import AliasToolkit

from alias.agent.utils.constants import (
    BROWSER_AGENT_DESCRIPTION,
    DEFAULT_DEEP_RESEARCH_AGENT_NAME,
    DEEPRESEARCH_AGENT_DESCRIPTION,
    DS_AGENT_DESCRIPTION,
)
from alias.agent.tools.add_tools import add_tools
from alias.agent.agents.ds_agent_utils import (
    add_ds_specific_tool,
)
from alias.agent.memory.longterm_memory import AliasLongTermMemory
from alias.server.clients.memory_client import MemoryClient


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


async def arun_meta_planner(
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

    # Init deep research toolkit
    deep_research_toolkit = init_dr_toolkit(worker_full_toolkit)

    # Init BI agent toolkit
    ds_toolkit = init_ds_toolkit(worker_full_toolkit)

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

        # Initialize long-term memory if enabled
        long_term_memory = None
        if session_service.session_entity.use_long_term_memory_service:
            # Check if memory service is available
            if await MemoryClient.is_available():
                long_term_memory = AliasLongTermMemory(
                    session_service=session_service,
                )
                logger.info(
                    "Long-term memory service is available and initialized",
                )
            else:
                logger.warning(
                    "use_long_term_memory_service is True, but memory "
                    "service is not available. Long-term memory will not "
                    "be used. Please check if the memory service is "
                    "running.",
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
            long_term_memory=long_term_memory,
        )
        meta_planner.worker_manager.register_worker(
            browser_agent,
            description=BROWSER_AGENT_DESCRIPTION,
            worker_type="built-in",
        )
        # == add deep research agent ===
        dr_agent = DeepResearchAgent(
            name=DEFAULT_DEEP_RESEARCH_AGENT_NAME,
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=deep_research_toolkit,
            session_service=session_service,
            agent_working_dir="/workspace",
            max_depth=2,
            enforce_mode="auto",
        )
        meta_planner.worker_manager.register_worker(
            dr_agent,
            description=DEEPRESEARCH_AGENT_DESCRIPTION,
            worker_type="built-in",
        )
        # === add BI agent ===
        ds_agent = DataScienceAgent(
            name="Data_Science_Agent",
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=ds_toolkit,
            max_iters=30,
            session_service=session_service,
        )
        meta_planner.worker_manager.register_worker(
            ds_agent,
            description=DS_AGENT_DESCRIPTION,
            worker_type="built-in",
        )

        msg = await meta_planner()
    except Exception as e:
        print(traceback.format_exc())
        raise e from None
    finally:
        await worker_full_toolkit.close_mcp_clients()
    return meta_planner, msg


async def arun_deepresearch_agent(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
    enforce_mode: Literal["general", "finance", "auto"] = "auto",
):
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
    worker_agent = DeepResearchAgent(
        name="Deep_Research_Agent",
        model=model,
        formatter=formatter,
        memory=InMemoryMemory(),
        toolkit=worker_toolkit,
        session_service=session_service,
        agent_working_dir="/workspace",
        max_depth=2,
        enforce_mode=enforce_mode,
    )
    try:
        await worker_agent()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Deep Research Agent execution interrupted by user")
        raise  # Re-raise so it can be handled in cli.py
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        raise e from None
    finally:
        try:
            await global_toolkit.close_mcp_clients()
        except (RuntimeError, asyncio.CancelledError) as e:
            # Event loop might be closed during shutdown
            if "Event loop is closed" in str(e) or isinstance(
                e,
                asyncio.CancelledError,
            ):
                logger.info(f"Skipping MCP client cleanup: {e}")
            else:
                raise
        except Exception as e:
            # Log but don't fail on cleanup errors
            logger.warning(f"Error during MCP client cleanup: {e}")


async def arun_finance_agent(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
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
        "SearchHotTopic",
        # "SearchFinancialNews",
        "searchRealtimeAiAnalysis",
        "tdx_wenda_quotes",
        "tdx_PBHQInfo_quotes",
    ]
    share_tools(global_toolkit, worker_toolkit, test_tool_list)
    worker_toolkit.create_tool_group(
        group_name="finance",
        description="Finance Analysis tools",
        active=True,
    )

    worker_agent = DeepResearchAgent(
        name="Deep_Research_Agent",
        model=model,
        formatter=formatter,
        memory=InMemoryMemory(),
        toolkit=worker_toolkit,
        session_service=session_service,
        agent_working_dir="/workspace",
        max_depth=2,
        enforce_mode="finance",
    )
    try:
        await worker_agent()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Deep Agent execution interrupted by user")
        raise  # Re-raise so it can be handled in cli.py
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        raise e from None
    finally:
        try:
            await global_toolkit.close_mcp_clients()
        except (RuntimeError, asyncio.CancelledError) as e:
            # Event loop might be closed during shutdown
            if "Event loop is closed" in str(e) or isinstance(
                e,
                asyncio.CancelledError,
            ):
                logger.info(f"Skipping MCP client cleanup: {e}")
            else:
                raise
        except Exception as e:
            # Log but don't fail on cleanup errors
            logger.warning(f"Error during MCP client cleanup: {e}")


async def arun_datascience_agent(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
    global_toolkit = AliasToolkit(sandbox, add_all=True)
    # await add_tools(global_toolkit)
    worker_toolkit = AliasToolkit(sandbox)
    model, formatter = MODEL_FORMATTER_MAPPING[MODEL_CONFIG_NAME]
    test_tool_list = [
        "write_file",
        "run_ipython_cell",
        "run_shell_command",
    ]
    share_tools(global_toolkit, worker_toolkit, test_tool_list)
    add_ds_specific_tool(worker_toolkit)

    try:
        worker_agent = DataScienceAgent(
            name="Data_Science_Agent",
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            toolkit=worker_toolkit,
            max_iters=30,
            session_service=session_service,
        )
        await worker_agent()
        # await worker_agent(instruction)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Data Science Agent execution interrupted by user")
        raise  # Re-raise so it can be handled in cli.py
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        raise e from None
    finally:
        try:
            await global_toolkit.close_mcp_clients()
        except (RuntimeError, asyncio.CancelledError) as e:
            # Event loop might be closed during shutdown
            if "Event loop is closed" in str(e) or isinstance(
                e,
                asyncio.CancelledError,
            ):
                logger.info(f"Skipping MCP client cleanup: {e}")
            else:
                raise
        except Exception as e:
            # Log but don't fail on cleanup errors
            logger.warning(f"Error during MCP client cleanup: {e}")


async def arun_browseruse_agent(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
    time_str = datetime.now().strftime("%Y%m%d%H%M%S")

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
        await browser_agent()
    except Exception as e:
        logger.error(f"---> Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        await browser_toolkit.close_mcp_clients()


async def arun_agents(
    session_service: SessionService,  # type: ignore[valid-type]
    sandbox: Sandbox = None,
):
    """
    This is the entry point for backend service executing agents.
    """
    chat_mode = session_service.session_entity.chat_mode
    if chat_mode == "dr":
        await arun_deepresearch_agent(session_service, sandbox)
    elif chat_mode == "browser":
        await arun_browseruse_agent(session_service, sandbox)
    elif chat_mode == "ds":
        await arun_datascience_agent(session_service, sandbox)
    elif chat_mode == "finance":
        await arun_finance_agent(session_service, sandbox)
    else:
        if chat_mode != "general":
            logger.warning(
                f"Unknown chat mode: {chat_mode}."
                "Invoke general mode instead.",
            )
        await arun_meta_planner(
            session_service,
            sandbox,
        )
