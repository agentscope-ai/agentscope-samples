# -*- coding: utf-8 -*-
import asyncio
import os

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import Toolkit, execute_python_code
from agentscope_runtime.adapters.agentscope.memory import (
    AgentScopeSessionHistoryMemory,
)
from agentscope_runtime.engine import AgentApp, LocalDeployManager
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest
from agentscope_runtime.engine.services.agent_state import InMemoryStateService
from agentscope_runtime.engine.services.session_history import (
    InMemorySessionHistoryService,
)
from agentscope_runtime.engine.tracing import TraceType, trace


# Read config.yml file
def read_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    config_data = {}
    with open(config_path, "r", encoding="utf-8") as config_file:
        for line in config_file:
            line = line.strip()
            if line and not line.startswith("#"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config_data[key] = value
    return config_data


# Read configuration
config = read_config()

agent_app = AgentApp(
    app_name=config.get("APP_NAME"),
    app_description="A helpful assistant",
)


# Initialize services (required)
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


@agent_app.endpoint("/")
def read_root():
    return {"hi, i'm running"}


@agent_app.endpoint("/health")
def health_check():
    return "OK"


# Default interface implementation for /process
@trace(trace_type=TraceType.LLM, trace_name="llm_func")
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

    toolkit = Toolkit()
    toolkit.register_tool_function(execute_python_code)

    agent = ReActAgent(
        name="Friday",
        model=DashScopeChatModel(
            config.get("DASHSCOPE_MODEL_NAME"),
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


async def main():
    """Deploy AgentScope Runtime using LocalDeployManager"""
    deployer = LocalDeployManager(
        host=config.get("FC_START_HOST", "127.0.0.1"),
        port=config.get("PORT", 8080),
    )

    # Deploy agent_app
    await agent_app.deploy(deployer)

    # Keep the service running
    print("Service started, press Ctrl+C to stop...")
    try:
        # Wait indefinitely until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping service...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nService stopped")
