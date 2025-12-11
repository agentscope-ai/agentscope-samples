# -*- coding: utf-8 -*-
# pylint:disable=redefined-outer-name, unused-argument


import os

from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit, execute_python_code
from agentscope.pipeline import stream_printing_messages

from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel

from agentscope_runtime.engine import AgentApp
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.adapters.agentscope.memory import (
    AgentScopeSessionHistoryMemory,
)
from agentscope_runtime.engine.services.agent_state import (
    InMemoryStateService,
)
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)


def local_deploy():
    from dotenv import load_dotenv

    load_dotenv()

    server_port = int(os.environ.get("SERVER_PORT", "8090"))
    # server_endpoint = os.environ.get("SERVER_ENDPOINT", "process")

    agent_app = AgentApp(
        app_name="Friday",
        app_description="A simple LLM agent to generate a short response",
    )

    @agent_app.init
    async def init_func(self):
        self.state_service = InMemoryStateService()
        self.session_service = InMemorySessionHistoryService()

        await self.state_service.start()
        await self.session_service.start()

    @agent_app.shutdown
    async def shutdown_func(self):
        await self.state_service.stop()
        await self.session_service.stop()

    @agent_app.query(framework="agentscope")
    async def query_func(
        self,
        msgs,
        request: AgentRequest = None,
        **kwargs,
    ):
        session_id = request.session_id
        user_id = request.user_id

        state = await self.state_service.export_state(
            session_id=session_id,
            user_id=user_id,
        )

        toolkit = Toolkit()
        toolkit.register_tool_function(execute_python_code)

        agent = ReActAgent(
            name="Friday",
            model=DashScopeChatModel(
                "qwen-turbo",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                enable_thinking=True,
                stream=True,
            ),
            sys_prompt="You're a helpful assistant named Friday.",
            toolkit=toolkit,
            memory=AgentScopeSessionHistoryMemory(
                service=self.session_service,
                session_id=session_id,
                user_id=user_id,
            ),
            formatter=DashScopeChatFormatter(),
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

    agent_app.run(host="127.0.0.1", port=server_port)


if __name__ == "__main__":
    local_deploy()
