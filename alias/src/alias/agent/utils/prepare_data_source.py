# -*- coding: utf-8 -*-
import os

from agentscope_runtime.sandbox.box.sandbox import Sandbox

from alias.agent.agents.data_source.data_source import DataSourceManager
from alias.agent.tools import AliasToolkit, share_tools
from alias.agent.utils.llm_call_manager import (
    LLMCallManager,
)

if os.getenv("TEST_MODE") not in ["local", "runtime-test"]:
    from alias.server.services.session_service import (
        SessionService,
    )
else:
    from alias.agent.mock import MockSessionService as SessionService


async def prepare_data_sources(
    session_service: SessionService,
    sandbox: Sandbox,
    binded_toolkit: AliasToolkit = None,
    llm_call_manager: LLMCallManager = None,
):
    data_manager = await build_data_manager(
        session_service,
        sandbox,
        llm_call_manager,
    )
    if len(data_manager):
        await add_user_data_message(session_service, data_manager)

    if binded_toolkit:
        add_data_source_tools(data_manager, binded_toolkit)

    return data_manager


async def build_data_manager(
    session_service: SessionService,
    sandbox: Sandbox,
    llm_call_manager: LLMCallManager,
):
    data_manager = DataSourceManager(sandbox, llm_call_manager)
    if (
        hasattr(session_service.session_entity, "data_config")
        and session_service.session_entity.data_config
    ):
        data_configs = session_service.session_entity.data_config
        for config in data_configs:
            data_manager.add_data_source(config)

    await data_manager.prepare_data_sources()
    return data_manager


def add_data_source_tools(
    data_manager: DataSourceManager,
    *toolkits: AliasToolkit,
):
    data_source_toolkit = data_manager.toolkit
    tool_names = list(data_source_toolkit.tools.keys())
    for toolkit in toolkits:
        share_tools(data_source_toolkit, toolkit, tool_names)


async def add_user_data_message(
    session_service: SessionService,
    data_manager: DataSourceManager,
):
    await session_service.append_to_latest_message(
        "\n\n" + data_manager.get_all_data_sources_desc(),
    )


def get_data_source_config_from_file(config_file: str):
    """Load and parse data source configuration from a JSON file."""
    import json

    # Validate file existence upfront
    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in data source configuration file `'{config_file}'`\
                : {e.msg} at line {e.lineno}",
        ) from e
