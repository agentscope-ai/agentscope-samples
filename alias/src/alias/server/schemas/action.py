# -*- coding: utf-8 -*-
import uuid
from typing import Any, Optional, Union

from pydantic import BaseModel
from sqlmodel import SQLModel

from alias.server.models.action import (
    ActionType,
    FeedbackType,
)
from alias.server.models.field import formatted_datetime_field
from alias.server.models.plan import Roadmap

from alias.server.schemas.chat import ChatType


class ChangeRecord(SQLModel):
    previous: Optional[Any] = None
    current: Optional[Any] = None


class OperationRecord(SQLModel):
    target: Optional[str] = None
    content: Optional[Union[dict, BaseModel, str]] = None


class QueryRecord(SQLModel):
    query: Optional[str] = None
    session_content: Optional[list[Any]] = None


class Action(SQLModel):
    uid: uuid.UUID
    session_id: uuid.UUID
    action_type: ActionType
    message_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    action_time: str = formatted_datetime_field()
    data: Optional[
        Union[dict, BaseModel, str, ChangeRecord, OperationRecord, QueryRecord]
    ] = None
    reference_time: Optional[str] = None


class ChangeAction(Action):
    @classmethod
    def _resolve_action_type(
        cls,
        previous: Optional[Any] = None,
        current: Optional[Any] = None,
    ) -> ActionType:
        raise NotImplementedError

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_id: Optional[uuid.UUID] = None,
        previous: Optional[Any] = None,
        current: Optional[Any] = None,
    ):
        if previous == current:
            return None
        action_type = cls._resolve_action_type(previous, current)
        return cls(
            uid=user_id,
            session_id=conversation_id,
            action_type=action_type,
            message_id=message_id,
            data=ChangeRecord(
                previous=previous,
                current=current,
            ),
        )


class FeedbackAction(ChangeAction):
    @classmethod
    def _resolve_action_type(
        cls,
        previous: Optional[FeedbackType] = None,
        current: Optional[FeedbackType] = None,
    ) -> ActionType:
        if current is None:
            if previous == FeedbackType.LIKE:
                action_type = ActionType.CANCEL_LIKE
            if previous == FeedbackType.DISLIKE:
                action_type = ActionType.CANCEL_DISLIKE
        elif current == FeedbackType.DISLIKE:
            action_type = ActionType.DISLIKE
        elif current == FeedbackType.LIKE:
            action_type = ActionType.LIKE
        return action_type


class ToolCollectionAction(ChangeAction):
    @classmethod
    def _resolve_action_type(
        cls,
        previous: Optional[bool] = None,
        current: Optional[bool] = None,
    ) -> ActionType:
        if current:
            action_type = ActionType.COLLECT_TOOL
        else:
            action_type = ActionType.UNCOLLECT_TOOL
        return action_type


class SessionCollectionAction(ChangeAction):
    @classmethod
    def _resolve_action_type(
        cls,
        previous: Optional[bool] = None,
        current: Optional[bool] = None,
    ) -> ActionType:
        if current:
            action_type = ActionType.COLLECT_SESSION
        else:
            action_type = ActionType.UNCOLLECT_SESSION

        return action_type


class EditRoadMapAction(ChangeAction):
    @classmethod
    def _resolve_action_type(
        cls,
        previous: Optional[Roadmap] = None,
        current: Optional[Roadmap] = None,
    ):
        return ActionType.EDIT_ROADMAP


class ChatAction(Action):
    @classmethod
    def _resolve_action_type(
        cls,
        chat_type: Optional[Any] = None,
        history_length: int = 0,
    ) -> ActionType:
        if history_length == 0:
            action_type = ActionType.START_CHAT
        elif chat_type == ChatType.TASK:
            action_type = ActionType.FOLLOWUP_CHAT
        elif chat_type == ChatType.CHAT:
            action_type = ActionType.BREAK_CHAT
        else:
            raise ValueError(f"Unsupported chat type: {chat_type}")
        return action_type

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_id: Optional[uuid.UUID] = None,
        query: Optional[str] = None,
        chat_type: Optional[ChatType] = None,
        history_length: int = 0,
        session_content: Optional[list[dict]] = None,
    ):
        action_type = cls._resolve_action_type(chat_type, history_length)
        return cls(
            uid=user_id,
            session_id=conversation_id,
            action_type=action_type,
            message_id=message_id,
            data=QueryRecord(
                query=query,
                session_content=session_content,
            ),
        )


class TaskStopAction(Action):
    @classmethod
    def _resolve_action_type(
        cls,
    ) -> ActionType:
        return ActionType.TASK_STOP

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        task_id: uuid.UUID,
        data: Optional[dict] = None,
    ):
        action_type = cls._resolve_action_type()
        return cls(
            uid=user_id,
            session_id=conversation_id,
            action_type=action_type,
            task_id=task_id,
            data=data,
        )
