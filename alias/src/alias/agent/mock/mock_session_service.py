# -*- coding: utf-8 -*-
# mypy: ignore-errors
# flake8: noqa
# pylint: skip-file
import uuid
import os
from typing import Any, Optional, List, Literal
import json
from loguru import logger
from datetime import datetime, timezone
from dataclasses import dataclass, field
from .mock_message_models import BaseMessage, MessageState, MockMessage


try:
    logger.level("SEND_MSG", no=52, color="<blue>", icon="💻")
    logger.level("SEND_PLAN", no=52, color="<white>", icon="📒")
except TypeError:
    pass


@dataclass
class MockPlan:
    task_id: uuid.UUID = uuid.uuid4()
    conversation_id: uuid.UUID = uuid.uuid4()
    message_id: uuid.UUID = uuid.uuid4()
    user_id: uuid.UUID = uuid.uuid4()
    runtime_id: uuid.UUID = uuid.uuid4()
    content: Any = None
    upload_files: List[Any] = field(default_factory=list)


class SessionEntity:
    task_id: uuid.UUID
    session_id: uuid.UUID
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    user_id: uuid.UUID
    runtime_id: uuid.UUID
    query: str
    upload_files: List = []
    is_chat: bool = False
    use_long_term_memory_service: bool = False

    def __init__(
        self,
        chat_mode: Literal[
            "general",
            "dr",
            "browser",
            "bi",
            "finance",
        ] = "general",
        use_long_term_memory_service: bool = False,
    ):
        self.user_id: uuid.UUID = uuid.UUID(
            "00000000-0000-0000-0000-000000000001",
        )
        # Hardcoded UUID for mock/testing purposes:
        # this value is used to represent a mock
        # user in test sessions.
        self.conversation_id: uuid.UUID = uuid.uuid4()
        self.session_id: uuid.UUID = uuid.uuid4()
        self.chat_mode = chat_mode
        self.use_long_term_memory_service = use_long_term_memory_service

    def ids(self):
        return {
            "task_id": str(self.task_id),
            "conversation_id": str(self.conversation_id),
            "message_id": str(self.message_id),
            "runtime_id": str(self.runtime_id),
        }


class MockSessionService:
    all_checkpoint_dir = "./logs/checkpoints/"

    def __init__(
        self,
        runtime_model: Any = None,
        use_long_term_memory_service: bool = False,
    ):
        self.session_id = "mock_session"
        self.conversation_id = "mock_conversation"
        self.messages = []
        self.plan = MockPlan()
        self.session_entity = SessionEntity(
            use_long_term_memory_service=use_long_term_memory_service,
        )
        logger.info(
            f"> user_id {self.session_entity.user_id}\n "
            f"> conversation_id {self.session_entity.conversation_id}",
        )
        # log for testing
        self.log_storage_path = os.path.join(
            "./logs",
            datetime.now().strftime("%Y%m%d%H%M%S") + ".log",
        )
        if not os.path.exists("./logs"):
            os.mkdir("./logs")
        self.plan_update_counter = 0
        self.runtime_model = runtime_model
        self.current_checkpoint_dir = os.path.join(
            self.all_checkpoint_dir,
            datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        self.state_save_count = 0
        self.state = {}

    # Plan
    async def create_plan(self, content: Any) -> MockPlan:
        self.plan = MockPlan(content=content)
        content = (
            f"\nCreate plan {self.plan_update_counter}:\n"
            f"\n{json.dumps(self.plan.content, indent=4, ensure_ascii=False)}"
            "\n" + "==" * 10 + "\n"
            'Type "continue" if the program halts and you are satisfied with '
            "the plan; otherwise, you can type your suggestion."
            "\n" + "==" * 10 + "\n"
        )
        logger.log("SEND_PLAN", content)
        with open(self.log_storage_path, "a") as file:
            # Append the content
            file.write(content)
        self.plan_update_counter += 1
        return self.plan

    async def update_plan(self, content: Any) -> MockPlan:
        self.plan = MockPlan(content=content)
        content = (
            f"Update plan {self.plan_update_counter}:\n"
            f"\n{json.dumps(self.plan.content, indent=4, ensure_ascii=False)}"
            "\n" + "==" * 10 + "\n"
            'Type "continue" if the program halts and you are satisfied with '
            "the plan; otherwise, you can type your suggestion."
            "\n" + "==" * 10 + "\n"
        )
        # logger.log("SEND_PLAN", content)
        with open(self.log_storage_path, "a") as file:
            # Append the content
            file.write(content)
        self.plan_update_counter += 1
        return self.plan

    async def delete_plan(self) -> None:
        logger.log("SEND_PLAN", f"Delete plan: {self.plan.content}")
        self.plan_update_counter = 0
        self.plan = MockPlan()

    async def create_message(
        self,
        message: BaseMessage,
        message_id: Optional[uuid.UUID] = None,
    ) -> MockMessage:
        db_message = None
        if message.status == MessageState.FINISHED:
            if message_id:
                for msg in self.messages:
                    if msg.id == message_id:
                        db_message = msg
                if db_message is None:
                    db_message = MockMessage()
                    self.messages.append(db_message)
                else:
                    # Update existing message's update_time
                    db_message.update_time = datetime.now(
                        timezone.utc,
                    ).isoformat()
                db_message.message = message.model_dump()
            else:
                db_message = MockMessage()
                db_message.message = message.model_dump()
                self.messages.append(db_message)
            logger.log(
                "SEND_MSG",
                f"Create new message {type(message)}, "
                f"buffer has {len(self.messages)}",
            )
            content = (
                "=" * 10
                + "\n"
                + f"Role: {db_message.message.get('role')},\n"
                + f"Name: {db_message.message.get('name')},\n"
                + f"Type: {db_message.message.get('type')},\n"
                + f"Statue: {db_message.message.get('status')},\n"
                + f"content: {str(db_message.message.get('content'))}\n"
                + "=" * 10
            )
            with open(self.log_storage_path, "a") as file:
                # Append the content
                file.write(content)

        elif message.status == MessageState.RUNNING:
            if message_id:
                for msg in self.messages:
                    if msg.id == message_id:
                        db_message = msg
                if db_message is None:
                    db_message = MockMessage()
                    self.messages.append(db_message)
                    logger.log(
                        "SEND_MSG",
                        f"Updating message {len(self.messages) - 1}",
                    )
                else:
                    # Update existing message's update_time
                    db_message.update_time = datetime.now(
                        timezone.utc,
                    ).isoformat()
                db_message.message = message.model_dump()
            else:
                db_message = MockMessage()
                db_message.message = message.model_dump()
                self.messages.append(db_message)
        return db_message

    async def get_messages(self) -> List[MockMessage]:
        logger.log("SEND_MSG", "Get all messages")
        return self.messages

    async def create_state(
        self,
        content: Any,
    ):
        postfix = ""
        if isinstance(content, dict):
            if "running_agent" in content:
                postfix += content["running_agent"] + "-"
            if "react_state" in content:
                postfix += str(content["react_state"]) + "-"
            if "react_round" in content:
                postfix += str(content["react_round"]) + "-"
            if "exec_tool_names" in content:
                postfix += "_".join(content["exec_tool_names"]) + "-"
        postfix += str(self.state_save_count)

        os.makedirs(self.current_checkpoint_dir, exist_ok=True)
        checkpoint_path = os.path.join(
            self.current_checkpoint_dir,
            f"state-{postfix}.json",
        )
        with open(checkpoint_path, "w") as file:
            json.dump(content, file, indent=4, ensure_ascii=False)
        # logger.info(f"State saved to {checkpoint_path}")
        self.state_save_count += 1
        self.state = content

    async def get_state(self) -> dict:
        return self.state
