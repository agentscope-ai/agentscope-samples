# -*- coding: utf-8 -*-
"""
Main Entry Point
Supports: backtest, live, mock modes
"""
import argparse
import asyncio
import logging
import os
from contextlib import AsyncExitStack
from pathlib import Path
import loguru

from dotenv import load_dotenv

from backend.agents import AnalystAgent, PMAgent, RiskAgent
from backend.config.constants import ANALYST_TYPES
from backend.config.env_config import get_env_float, get_env_int, get_env_list
from backend.core.pipeline import TradingPipeline
from backend.core.scheduler import BacktestScheduler, Scheduler
from backend.utils.settlement import SettlementCoordinator
from backend.llm.models import get_agent_formatter, get_agent_model
from backend.services.gateway import Gateway
from backend.services.market import MarketService
from backend.services.storage import StorageService

load_dotenv()
logger = logging.getLogger(__name__)
loguru.logger.disable("flowllm")
loguru.logger.disable("reme_ai")


def create_long_term_memory(agent_name: str, config_name: str):
    """
    Create ReMeTaskLongTermMemory for an agent

    Requires DASHSCOPE_API_KEY env var
    """
    from agentscope.memory import ReMeTaskLongTermMemory
    from agentscope.model import DashScopeChatModel
    from agentscope.embedding import DashScopeTextEmbedding

    api_key = os.getenv("MEMORY_API_KEY")
    if not api_key:
        logger.warning("MEMORY_API_KEY not set, long-term memory disabled")
        return None

    memory_dir = str(Path(config_name) / "memory")

    return ReMeTaskLongTermMemory(
        agent_name=agent_name,
        user_name=agent_name,
        model=DashScopeChatModel(
            model_name=os.getenv("MEMORY_MODEL_NAME", "qwen3-max"),
            api_key=api_key,
            stream=False,
        ),
        embedding_model=DashScopeTextEmbedding(
            model_name=os.getenv(
                "MEMORY_EMBEDDING_MODEL",
                "text-embedding-v4",
            ),
            api_key=api_key,
            dimensions=1024,
        ),
        **{
            "vector_store.default.backend": "local",
            "vector_store.default.params.store_dir": memory_dir,
        },
    )


def create_agents(
    config_name: str,
    initial_cash: float,
    margin_requirement: float,
    enable_long_term_memory: bool = False,
):
    """Create all agents for the system

    Returns:
        tuple: (analysts, risk_manager, portfolio_manager, long_term_memories)
        long_term_memories is a list of memory
    """
    analysts = []
    long_term_memories = []

    for analyst_type in ANALYST_TYPES:
        model = get_agent_model(analyst_type)
        formatter = get_agent_formatter(analyst_type)
        toolkit = create_toolkit(analyst_type)

        long_term_memory = None
        if enable_long_term_memory:
            long_term_memory = create_long_term_memory(
                analyst_type,
                config_name,
            )
            if long_term_memory:
                long_term_memories.append(long_term_memory)

        analyst = AnalystAgent(
            analyst_type=analyst_type,
            toolkit=toolkit,
            model=model,
            formatter=formatter,
            agent_id=analyst_type,
            config={"config_name": config_name},
            long_term_memory=long_term_memory,
        )
        analysts.append(analyst)

    risk_long_term_memory = None
    if enable_long_term_memory:
        risk_long_term_memory = create_long_term_memory(
            "risk_manager",
            config_name,
        )
        if risk_long_term_memory:
            long_term_memories.append(risk_long_term_memory)

    risk_manager = RiskAgent(
        model=get_agent_model("risk_manager"),
        formatter=get_agent_formatter("risk_manager"),
        name="risk_manager",
        config={"config_name": config_name},
        long_term_memory=risk_long_term_memory,
    )

    pm_long_term_memory = None
    if enable_long_term_memory:
        pm_long_term_memory = create_long_term_memory(
            "portfolio_manager",
            config_name,
        )
        if pm_long_term_memory:
            long_term_memories.append(pm_long_term_memory)

    portfolio_manager = PMAgent(
        name="portfolio_manager",
        model=get_agent_model("portfolio_manager"),
        formatter=get_agent_formatter("portfolio_manager"),
        initial_cash=initial_cash,
        margin_requirement=margin_requirement,
        config={"config_name": config_name},
        long_term_memory=pm_long_term_memory,
    )

    return analysts, risk_manager, portfolio_manager, long_term_memories


def create_toolkit(analyst_type: str):
    """Create AgentScope Toolkit with tools for specific analyst type"""
    from agentscope.tool import Toolkit
    from backend.agents.prompt_loader import PromptLoader
    from backend.tools.analysis_tools import TOOL_REGISTRY

    # Load analyst persona config
    prompt_loader = PromptLoader()
    personas_config = prompt_loader.load_yaml_config("analyst", "personas")
    persona = personas_config.get(analyst_type, {})

    # Get tool names for this analyst type
    tool_names = persona.get("tools", [])

    # Create toolkit and register tools
    toolkit = Toolkit()
    for tool_name in tool_names:
        tool_func = TOOL_REGISTRY.get(tool_name)
        if tool_func:
            toolkit.register_tool_function(tool_func)

    return toolkit


async def run_with_gateway(args):
    """Run with WebSocket gateway"""
    is_backtest = args.mode == "backtest"

    # Load config from env, override with args
    tickers = get_env_list("TICKERS", ["AAPL", "MSFT"])
    initial_cash = get_env_float("INITIAL_CASH", 100000.0)
    margin_requirement = get_env_float("MARGIN_REQUIREMENT", 0.0)
    config_name = args.config_name

    # Create market service
    market_service = MarketService(
        tickers=tickers,
        poll_interval=args.poll_interval,
        mock_mode=args.mock and not is_backtest,
        backtest_mode=is_backtest,
        api_key=os.getenv("FINNHUB_API_KEY")
        if not args.mock and not is_backtest
        else None,
        backtest_start_date=args.start_date if is_backtest else None,
        backtest_end_date=args.end_date if is_backtest else None,
    )

    # Create storage service
    storage_service = StorageService(
        dashboard_dir=Path(config_name) / "team_dashboard",
        initial_cash=initial_cash,
        config_name=config_name,
    )

    if not storage_service.files["summary"].exists():
        storage_service.initialize_empty_dashboard()
    else:
        storage_service.update_leaderboard_model_info()

    # Create agents and pipeline
    analysts, risk_manager, pm, long_term_memories = create_agents(
        config_name=config_name,
        initial_cash=initial_cash,
        margin_requirement=margin_requirement,
        enable_long_term_memory=args.enable_memory,
    )
    portfolio_state = storage_service.load_portfolio_state()
    pm.load_portfolio_state(portfolio_state)

    settlement_coordinator = SettlementCoordinator(
        storage=storage_service,
        initial_capital=initial_cash,
    )

    pipeline = TradingPipeline(
        analysts=analysts,
        risk_manager=risk_manager,
        portfolio_manager=pm,
        settlement_coordinator=settlement_coordinator,
        max_comm_cycles=get_env_int("MAX_COMM_CYCLES", 2),
    )

    # Create scheduler callback
    scheduler_callback = None
    trading_dates = []

    if is_backtest:
        backtest_scheduler = BacktestScheduler(
            start_date=args.start_date,
            end_date=args.end_date,
            trading_calendar="NYSE",
            delay_between_days=0.5,
        )
        trading_dates = backtest_scheduler.get_trading_dates()

        async def scheduler_callback_fn(callback):
            await backtest_scheduler.start(callback)

        scheduler_callback = scheduler_callback_fn
    else:
        # Live mode: use daily scheduler with NYSE timezone
        live_scheduler = Scheduler(
            mode="daily",
            trigger_time=args.trigger_time,
            config={"config_name": config_name},
        )

        async def scheduler_callback_fn(callback):
            await live_scheduler.start(callback)

        scheduler_callback = scheduler_callback_fn

    # Create gateway
    gateway = Gateway(
        market_service=market_service,
        storage_service=storage_service,
        pipeline=pipeline,
        scheduler_callback=scheduler_callback,
        config={
            "mode": args.mode,
            "mock_mode": args.mock,
            "backtest_mode": is_backtest,
            "tickers": tickers,
            "config_name": config_name,
        },
    )

    if is_backtest:
        gateway.set_backtest_dates(trading_dates)

    # Start long-term memory contexts and run gateway
    async with AsyncExitStack() as stack:
        for memory in long_term_memories:
            await stack.enter_async_context(memory)
        await gateway.start(host=args.host, port=args.port)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Trading System")
    parser.add_argument("--mode", choices=["live", "backtest"], default="live")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--config-name", default="mock")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--trigger-time", default="09:30")  # NYSE market open
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument(
        "--enable-memory",
        action="store_true",
        help="Enable ReMeTaskLongTermMemory for agents",
    )

    args = parser.parse_args()

    # Load config from env for logging
    tickers = get_env_list("TICKERS", ["AAPL", "MSFT"])
    initial_cash = get_env_float("INITIAL_CASH", 100000.0)

    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode}, Config: {args.config_name}")
    logger.info(f"Tickers: {tickers}")
    logger.info(f"Initial Cash: ${initial_cash:,.2f}")
    logger.info(
        f"Long-term Memory: {'enabled' if args.enable_memory else 'disabled'}",
    )
    if args.mode == "backtest":
        if not args.start_date or not args.end_date:
            parser.error(
                "--start-date and --end-date required for backtest mode",
            )
        logger.info(f"Backtest: {args.start_date} to {args.end_date}")
    logger.info("=" * 60)

    asyncio.run(run_with_gateway(args))


if __name__ == "__main__":
    main()
