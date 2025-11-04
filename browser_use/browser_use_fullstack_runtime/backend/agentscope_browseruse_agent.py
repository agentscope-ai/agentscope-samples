# -*- coding: utf-8 -*-
import os
from typing import List, Dict, AsyncGenerator

from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope_runtime.engine import Runner
from agentscope_runtime.engine.agents.agentscope_agent import AgentScopeAgent
from agentscope_runtime.engine.schemas.agent_schemas import (
    AgentRequest,
    RunStatus,
)
from agentscope_runtime.engine.services import SandboxService
from agentscope_runtime.engine.services.context_manager import ContextManager
from agentscope_runtime.engine.services.environment_manager import (
    EnvironmentManager,
)
from agentscope_runtime.engine.services.memory_service import (
    InMemoryMemoryService,
)
from agentscope_runtime.engine.services.session_history_service import (
    InMemorySessionHistoryService,
)
from agentscope_runtime.sandbox.tools.browser import (
    browser_click,
    browser_close,
    browser_console_messages,
    browser_drag,
    browser_file_upload,
    browser_handle_dialog,
    browser_hover,
    browser_navigate,
    browser_navigate_back,
    browser_navigate_forward,
    browser_network_requests,
    browser_pdf_save,
    browser_press_key,
    browser_resize,
    browser_select_option,
    browser_snapshot,
    browser_tab_close,
    browser_tab_list,
    browser_tab_new,
    browser_tab_select,
    browser_take_screenshot,
    browser_type,
    browser_wait_for,
    run_ipython_cell,
    run_shell_command,
)

from prompts import SYSTEM_PROMPT

if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv(".env")

USER_ID = "user_1"
SESSION_ID = "session_001"  # Using a fixed ID for simplicity


class AgentscopeBrowseruseAgent:
    def __init__(self) -> None:
        self.tools = [
            run_shell_command,
            run_ipython_cell,
            browser_close,
            browser_resize,
            browser_console_messages,
            browser_handle_dialog,
            browser_file_upload,
            browser_press_key,
            browser_navigate,
            browser_navigate_back,
            browser_navigate_forward,
            browser_network_requests,
            browser_pdf_save,
            browser_take_screenshot,
            browser_snapshot,
            browser_click,
            browser_drag,
            browser_hover,
            browser_type,
            browser_select_option,
            browser_tab_list,
            browser_tab_new,
            browser_tab_select,
            browser_tab_close,
            browser_wait_for,
        ]
        self.agent = AgentScopeAgent(
            name="Friday",
            model=DashScopeChatModel(
                "qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
            ),
            agent_config={
                "sys_prompt": SYSTEM_PROMPT,
            },
            tools=self.tools,
            agent_builder=ReActAgent,
        )

    async def connect(self) -> None:
        session_history_service = InMemorySessionHistoryService()

        await session_history_service.create_session(
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        self.mem_service = InMemoryMemoryService()
        await self.mem_service.start()
        self.sandbox_service = SandboxService()
        await self.sandbox_service.start()

        self.context_manager = ContextManager(
            memory_service=self.mem_service,
            session_history_service=session_history_service,
        )
        self.environment_manager = EnvironmentManager(
            sandbox_service=self.sandbox_service,
        )
        sandboxes = self.sandbox_service.connect(
            session_id=SESSION_ID,
            user_id=USER_ID,
            tools=self.tools,
        )

        if len(sandboxes) > 0:
            sandbox = sandboxes[0]
            self.desktop_url = sandbox.desktop_url
        else:
            self.desktop_url = ""

        runner = Runner(
            agent=self.agent,
            context_manager=self.context_manager,
            environment_manager=self.environment_manager,
        )
        self.runner = runner

    async def chat(
        self,
        chat_messages: List[Dict],
    ) -> AsyncGenerator[Dict, None]:
        convert_messages = []
        for chat_message in chat_messages:
            convert_messages.append(
                {
                    "role": chat_message["role"],
                    "content": [
                        {
                            "type": "text",
                            "text": chat_message["content"],
                        },
                    ],
                },
            )
        request = AgentRequest(input=convert_messages, session_id=SESSION_ID)
        request.tools = []
        async for message in self.runner.stream_query(
            user_id=USER_ID,
            request=request,
        ):
            if (
                message.object == "message"
                and RunStatus.Completed == message.status
            ):
                yield message.content

    async def close(self) -> None:
        await self.sandbox_service.stop()
        await self.mem_service.stop()
