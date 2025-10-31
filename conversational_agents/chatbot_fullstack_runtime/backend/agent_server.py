# -*- coding: utf-8 -*-
import asyncio
import os

from agentscope.agent import ReActAgent
from agentscope_runtime.engine import LocalDeployManager, Runner
from agentscope.model import DashScopeChatModel
from agentscope_runtime.engine.agents.agentscope_agent import AgentScopeAgent
from agentscope_runtime.engine.services.context_manager import ContextManager


def local_deploy():
    asyncio.run(_local_deploy())


async def _local_deploy():
    from dotenv import load_dotenv

    load_dotenv()

    server_port = int(os.environ.get("SERVER_PORT", "8090"))
    server_endpoint = os.environ.get("SERVER_ENDPOINT", "agent")
    model = DashScopeChatModel(
        model_name="qwen-turbo",
        api_key=os.getenv("DASHSCOPE_API_KEY"),

    )
    agent = AgentScopeAgent(
        name="Friday",
        model=model,
        agent_config={"sys_prompt": "A simple LLM agent to generate a short response"},
        agent_builder=ReActAgent,
    )

    context_manager = ContextManager()

    runner = Runner(
        agent=agent,
        context_manager=context_manager,
    )

    deploy_manager = LocalDeployManager(host="localhost", port=server_port)
    try:
        deployment_info = await runner.deploy(
            deploy_manager,
            endpoint_path=f"/{server_endpoint}",
        )

        print("✅ Service deployed successfully!")
        print(f"   URL: {deployment_info['url']}")
        print(f"   Endpoint: {deployment_info['url']}/{server_endpoint}")
        print("\nAgent Service is running in the background.")

        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        # This block will be executed when you press Ctrl+C.
        print("\nShutdown signal received. Stopping the service...")
        if deploy_manager.is_running:
            await deploy_manager.stop()
        print("✅ Service stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")
        if deploy_manager.is_running:
            await deploy_manager.stop()


if __name__ == "__main__":
    local_deploy()
