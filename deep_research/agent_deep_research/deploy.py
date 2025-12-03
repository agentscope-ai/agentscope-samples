# -*- coding: utf-8 -*-
"""The main entry point of the Deep Research agent example."""
import asyncio
import os
import shutil

from agentscope import logger
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import StdIOStatefulClient
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope_runtime.engine.app import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.engine.services.agent_state import (
    InMemoryStateService,
)
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)

from deep_research_agent import DeepResearchAgent

agent_app = AgentApp(
    app_name="Friday",
    app_description="A helpful assistant",
)

@agent_app.init
async def init_func(self):
    self.state_service = InMemoryStateService()
    self.session_service = InMemorySessionHistoryService()

    await self.state_service.start()
    await self.session_service.start()

    self.tavily_search_client = StdIOStatefulClient(
        name="tavily_mcp",
        command="npx",
        args=["-y", "tavily-mcp@latest"],
        env={"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")},
    )

    await self.tavily_search_client.connect()


@agent_app.shutdown
async def shutdown_func(self):
    await self.state_service.stop()
    await self.session_service.stop()
    await self.tavily_search_client.close()


@agent_app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    assert kwargs is not None, "kwargs is Required for query_func"
    session_id = request.session_id
    user_id = request.user_id

    state = await self.state_service.export_state(
        session_id=session_id,
        user_id=user_id,
    )

    local_temp_dir_name = "deepresearch_agent_local_temp_" +  session_id + "_" + user_id
    agent_working_dir = os.path.join(
        os.path.dirname(__file__),
        local_temp_dir_name,
    )
    os.makedirs(agent_working_dir, exist_ok=True)

    agent = DeepResearchAgent(
        name="Friday",
        sys_prompt="You are a helpful assistant named Friday.",
        model=DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen-max",
            enable_thinking=False,
            stream=True,
        ),
        formatter=DashScopeChatFormatter(),
        memory=InMemoryMemory(),
        search_mcp_client=self.tavily_search_client,
        tmp_file_storage_dir=agent_working_dir,
    )

    if state:
        agent.load_state_dict(state)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    state = agent.state_dict()

    await self.state_service.save_state(
        user_id=user_id,
        session_id=session_id,
        state=state,
    )

    # delete the temp working dir immediately after finish the task
    shutil.rmtree(agent_working_dir, ignore_errors=True)



if __name__ == "__main__":
    try:
        agent_app.run(web_ui=True)
    except Exception as e:
        logger.exception(e)
