# -*- coding: utf-8 -*-
import uuid
from typing import Callable
from agentscope.memory import InMemoryMemory

from alias.agent.agents import AliasAgentBase
from alias.agent.tools import AliasToolkit
from alias.agent.tools.share_tools import share_tools


def default_dr_worker_builder(
    self: AliasAgentBase,
):
    worker_sys_prompt = (
        "You are a helpful assistant who is good at "
        "searching online information and "
        "summarizing the gathered information"
    )
    worker_toolkit = AliasToolkit(
        sandbox=self.toolkit.sandbox,
        add_all=False,
    )
    dr_tool_list = [
        "tavily_search",
        "tavily_extract",
        "write_file",
        "create_directory",
        "list_directory",
        "read_file",
        "run_shell_command",
    ]
    share_tools(self.toolkit, worker_toolkit, dr_tool_list)
    worker = AliasAgentBase(
        name="Deep_Research_Assistant_" + str(uuid.uuid4())[:8],
        model=self.model,
        formatter=self.formatter,
        memory=InMemoryMemory(),
        toolkit=worker_toolkit,
        sys_prompt=worker_sys_prompt,
        # state_saving_dir=self.state_saving_dir,
        session_service=self.session_service,
    )
    response_func = worker.toolkit.tools.get(worker.finish_function_name)
    response_func.json_schema["function"]["description"] = (
        "Call this function when you finish this task"
        "Notice you need to follow the descriptions and generate all "
        "attributes in the function tool."
    )
    return worker


def finance_dr_worker_builder(
    self: AliasAgentBase,
):
    worker_sys_prompt = (
        "You are a helpful assistant who is good at "
        "searching online information and "
        "summarizing the gathered information. Note that these tools "
        "(searchRealtimeAiAnalysis, tdx_wenda_quotes, tdx_PBHQInfo_quotes) "
        "only cover A-share markets and don’t provide global stock data."
    )
    worker_toolkit = AliasToolkit(
        sandbox=self.toolkit.sandbox,
        add_all=False,
    )
    dr_tool_list = [
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
    share_tools(self.toolkit, worker_toolkit, dr_tool_list)
    worker_toolkit.create_tool_group(
        group_name="finance",
        description="Finance Analysis tools",
        active=True,
    )

    worker = AliasAgentBase(
        name="Deep_Research_Assistant_" + str(uuid.uuid4())[:8],
        model=self.model,
        formatter=self.formatter,
        memory=InMemoryMemory(),
        toolkit=worker_toolkit,
        sys_prompt=worker_sys_prompt,
        # state_saving_dir=self.state_saving_dir,
        session_service=self.session_service,
    )
    response_func = worker.toolkit.tools.get(worker.finish_function_name)
    response_func.json_schema["function"]["description"] = (
        "Call this function when you finish this task"
        "Notice you need to follow the descriptions and generate all "
        "attributes in the function tool."
    )
    return worker


def get_deep_research_worker_builder(
    worker_type: str = "default",
) -> Callable[[AliasAgentBase], AliasAgentBase]:
    if worker_type == "default":
        return default_dr_worker_builder
    elif worker_type == "finance":
        return finance_dr_worker_builder
    else:
        raise NotImplementedError(f"Worker type {worker_type} not implemented")
