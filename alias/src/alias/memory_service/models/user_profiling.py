# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ActionType(str, Enum):
    """Action types based on the Action classes provided"""

    # Feedback actions
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    CANCEL_LIKE = "CANCEL_LIKE"
    CANCEL_DISLIKE = "CANCEL_DISLIKE"

    # Collection actions
    COLLECT_TOOL = "COLLECT_TOOL"
    UNCOLLECT_TOOL = "UNCOLLECT_TOOL"
    COLLECT_SESSION = "COLLECT_SESSION"
    UNCOLLECT_SESSION = "UNCOLLECT_SESSION"

    # Chat actions
    START_CHAT = "START_CHAT"
    FOLLOWUP_CHAT = "FOLLOWUP_CHAT"
    BREAK_CHAT = "BREAK_CHAT"

    # Edit actions
    EDIT_ROADMAP = "EDIT_ROADMAP"
    EDIT_FILE = "EDIT_FILE"
    EXECUTE_SHELL_COMMAND = "EXECUTE_SHELL_COMMAND"
    BROWSER_OPERATION = "BROWSER_OPERATION"

    # Task actions
    TASK_STOP = "TASK_STOP"


class FeedbackType(str, Enum):
    """Feedback types for user feedback actions"""

    LIKE = "like"
    DISLIKE = "dislike"


class ChatType(str, Enum):
    """Chat types for chat actions"""

    TASK = "task"
    CHAT = "chat"


# =============================================================================
# Data Records
# =============================================================================


class ChangeRecord(BaseModel):
    """Data structure for change actions (feedback, collection, etc.)"""

    previous: Optional[Any] = None
    current: Optional[Any] = None


class QueryRecord(BaseModel):
    """Data structure for chat actions"""

    query: Optional[str] = None


class OperationRecord(BaseModel):
    """Data structure for operation actions"""

    operation_type: str
    operation_data: Optional[dict] = None


class Roadmap(BaseModel):
    """Data structure for roadmap editing"""

    content: Optional[str] = None
    metadata: Optional[dict] = None


# =============================================================================
# Base Request/Response Classes
# =============================================================================


class BaseUserProfilingRequest(BaseModel):
    """Base class for user profiling requests"""

    uid: str = Field(description="User ID")


class BaseUserProfilingResponse(BaseModel):
    """Base class for user profiling responses"""

    status: str = Field(description="Status of the response")


class BaseUserProfilingResponseWithId(BaseUserProfilingResponse):
    """Base class for responses that include submit_id"""

    submit_id: str = Field(description="Submit ID")


# =============================================================================
# Service Settings
# =============================================================================


class UserProfilingServiceSettings(BaseModel):
    """Settings for user profiling service"""

    base_url: str = os.getenv(
        "USER_PROFILING_BASE_URL",
        "http://localhost:8000",
    )
    # model_config = SettingsConfigDict(env_file=".env")
    timeout: int = 20  # seconds


# =============================================================================
# Submit ID Responses
# =============================================================================


class UserProfilingResponseSubmitId(BaseUserProfilingResponseWithId):
    """Response with submit ID"""


class UserProfilingResponseSubmitIdStatus(BaseUserProfilingResponseWithId):
    """Response with submit ID and status data"""

    data: Optional[Any] = Field(default=None)


# =============================================================================
# Mem0 Response Models
# =============================================================================


class Mem0RetrieveResponse(BaseModel):
    """Response structure for Mem0 retrieve operations"""

    results: List[Any] = Field(default_factory=list)
    relations: Optional[List[Any]] = Field(default=None)
    #  dict: A dictionary containing the search results, typically
    #        under a "results" key, and potentially "relations" if graph
    #        store is enabled. Example for v1.1+:
    #        `{"results": [{"id": "...", "memory": "...", "score": 0.8,
    #        ...}]}`


class UserProfilingMem0RetrieveResponse(BaseModel):
    candidates: dict = Field(default_factory=dict)
    profiling: dict = Field(default_factory=dict)
    user_info: dict = Field(default_factory=dict)
    #  dict: A dictionary containing the search results, typically
    #        under a "results" key, and potentially "relations" if graph
    #        store is enabled. Example for v1.1+:
    #        `{"results": [{"id": "...", "memory": "...", "score": 0.8,
    #        ...}]}`

    # Documentation for v1.1+ format:
    # Example: {"results": [{"id": "...", "memory": "...", "score": 0.8, ...}]}


# =============================================================================
# Basic CRUD Operations
# =============================================================================


class UserProfilingAddRequest(BaseUserProfilingRequest):
    """Request for adding user profiling content"""

    content: List[Any] = Field(default_factory=list)
    session_id: Optional[str] = Field(default=None, description="Session ID")


class UserProfilingRetrieveRequest(BaseUserProfilingRequest):
    """Request for retrieving user profiling data"""

    query: str
    limit: Optional[int] = Field(
        default=3,
        description="The maximum number of memories to retrieve",
    )
    threshold: Optional[float] = Field(
        default=0.6,
        description="The threshold for the memories to retrieve",
    )


class UserProfilingRetrieveResponse(BaseUserProfilingResponse):
    """Response for user profiling retrieve operations"""

    uid: str
    query: str
    data: UserProfilingMem0RetrieveResponse


class UserProfilingShowAllRequest(BaseUserProfilingRequest):
    """Request for showing all user profiling data"""


class UserProfilingShowAllResponse(BaseUserProfilingResponse):
    """Response for showing all user profiling data"""

    uid: str
    data: dict


class UserProfilingShowAllUserProfilesRequest(BaseUserProfilingRequest):
    """Request for showing all user profiles"""


class UserProfilingShowAllUserProfilesData(BaseModel):
    """Data for showing all user profiles"""

    pid: str
    uid: str
    content: str
    metadata: UserProfilingShowAllUserProfilesMetadata


class UserProfilingShowAllUserProfilesMetadata(BaseModel):
    """Metadata for showing all user profiles"""

    session_id: Optional[str] = Field(default=None, description="Session ID")
    is_confirmed: int = Field(
        default=0,
        description="0: not confirmed, 1: confirmed",
    )


class UserProfilingShowAllUserProfilesResponse(BaseUserProfilingResponse):
    """Response for showing all user profiles"""

    status: str = Field(description="Status of the response")
    data: list[UserProfilingShowAllUserProfilesData] = Field(
        description="List of user profiles",
    )


class UserProfilingDeleteRequest(BaseUserProfilingRequest):
    """Request for deleting user profiling data"""

    key: Any = Field(description="Key of the user profiling data")


class UserProfilingProcessRequest(BaseUserProfilingRequest):
    """Request for processing user profiling content"""

    content: List[Any] = Field(default_factory=list)


class UserProfilingClearRequest(BaseUserProfilingRequest):
    """Request for clearing user profiling data"""


# =============================================================================
# Action Recording
# =============================================================================


class UserProfilingRecordActionRequest(BaseUserProfilingRequest):
    """Request for recording user actions"""

    session_id: str = Field(description="Session ID")
    action_type: Optional[ActionType] = Field(
        default=None,
        description="Action type",
    )
    message_id: Optional[str] = Field(default=None, description="Message ID")
    action_time: Optional[str] = Field(default=None, description="Action time")
    data: Optional[
        Union[dict, ChangeRecord, OperationRecord, QueryRecord, Roadmap]
    ] = Field(default=None, description="the data of the action")
    reference_time: Optional[str] = Field(
        default=None,
        description="Reference time",
    )

    # Legacy fields for backward compatibility
    action: Optional[str] = Field(
        default=None,
        description="Legacy action field, deprecated",
    )
    action_message_id: Optional[str] = Field(
        default=None,
        description="Legacy action message ID, deprecated",
    )
    user_edit: Optional[dict] = Field(
        default=None,
        description=(
            "Legacy user edit data, deprecated. User edit data is now "
            "included in the data field."
        ),
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Handle legacy format: if action_type is not provided but action is,
        # we'll let the server handle the conversion
        if self.action_type is None and self.action is None:
            raise ValueError("Either action_type or action must be provided")

    @classmethod
    def create_feedback_action(
        cls,
        uid: str,
        session_id: str,
        message_id: Optional[str] = None,
        previous: Optional[FeedbackType] = None,
        current: Optional[FeedbackType] = None,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create a feedback action request"""
        if current is None:
            if previous == FeedbackType.LIKE:
                action_type = ActionType.CANCEL_LIKE
            elif previous == FeedbackType.DISLIKE:
                action_type = ActionType.CANCEL_DISLIKE
            else:
                raise ValueError("Invalid feedback state")
        elif current == FeedbackType.DISLIKE:
            action_type = ActionType.DISLIKE
        elif current == FeedbackType.LIKE:
            action_type = ActionType.LIKE
        else:
            raise ValueError("Invalid feedback state")

        return cls(
            uid=uid,
            session_id=session_id,
            action_type=action_type,
            message_id=message_id,
            data=ChangeRecord(previous=previous, current=current),
            reference_time=reference_time,
        )

    @classmethod
    def create_tool_collection_action(
        cls,
        uid: str,
        session_id: str,
        message_id: Optional[str] = None,
        previous: Optional[bool] = None,
        current: Optional[bool] = None,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create a tool collection action request"""
        action_type = (
            ActionType.COLLECT_TOOL if current else ActionType.UNCOLLECT_TOOL
        )

        return cls(
            uid=uid,
            session_id=session_id,
            action_type=action_type,
            message_id=message_id,
            data=ChangeRecord(previous=previous, current=current),
            reference_time=reference_time,
        )

    @classmethod
    def create_session_collection_action(
        cls,
        uid: str,
        session_id: str,
        message_id: Optional[str] = None,
        previous: Optional[bool] = None,
        current: Optional[bool] = None,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create a session collection action request"""
        action_type = (
            ActionType.COLLECT_SESSION
            if current
            else ActionType.UNCOLLECT_SESSION
        )

        return cls(
            uid=uid,
            session_id=session_id,
            action_type=action_type,
            message_id=message_id,
            data=ChangeRecord(previous=previous, current=current),
            reference_time=reference_time,
        )

    @classmethod
    def create_edit_roadmap_action(
        cls,
        uid: str,
        session_id: str,
        message_id: Optional[str] = None,
        previous: Optional[Roadmap] = None,
        current: Optional[Roadmap] = None,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create an edit roadmap action request"""
        return cls(
            uid=uid,
            session_id=session_id,
            action_type=ActionType.EDIT_ROADMAP,
            message_id=message_id,
            data=ChangeRecord(previous=previous, current=current),
            reference_time=reference_time,
        )

    @classmethod
    def create_chat_action(
        cls,
        uid: str,
        session_id: str,
        message_id: Optional[str] = None,
        query: Optional[str] = None,
        chat_type: Optional[ChatType] = None,
        history_length: int = 0,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create a chat action request"""
        if history_length == 0:
            action_type = ActionType.START_CHAT
        elif chat_type == ChatType.TASK:
            action_type = ActionType.FOLLOWUP_CHAT
        elif chat_type == ChatType.CHAT:
            action_type = ActionType.BREAK_CHAT
        else:
            raise ValueError(f"Unsupported chat type: {chat_type}")

        return cls(
            uid=uid,
            session_id=session_id,
            action_type=action_type,
            message_id=message_id,
            data=QueryRecord(query=query),
            reference_time=reference_time,
        )

    @classmethod
    def create_operation_action(
        cls,
        uid: str,
        session_id: str,
        action_type: ActionType,
        operation_data: Optional[dict] = None,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create an operation action request"""
        valid_operation_types = [
            ActionType.EDIT_FILE,
            ActionType.EXECUTE_SHELL_COMMAND,
            ActionType.BROWSER_OPERATION,
        ]

        if action_type not in valid_operation_types:
            raise ValueError(f"Unsupported action type: {action_type}")

        return cls(
            uid=uid,
            session_id=session_id,
            action_type=action_type,
            data=OperationRecord(
                operation_type=action_type.value,
                operation_data=operation_data,
            ),
            reference_time=reference_time,
        )

    @classmethod
    def create_task_stop_action(
        cls,
        uid: str,
        session_id: str,
        task_id: str,
        reference_time: Optional[str] = None,
    ) -> UserProfilingRecordActionRequest:
        """Create a task stop action request"""
        return cls(
            uid=uid,
            session_id=session_id,
            action_type=ActionType.TASK_STOP,
            data={"task_id": task_id},
            reference_time=reference_time,
        )


# =============================================================================
# Direct Profile Operations
# =============================================================================


class UserProfilingDirectAddProfileRequest(BaseUserProfilingRequest):
    """Request for directly adding a profile"""

    content: Any = Field(description="Content of the profile")


class UserProfilingDirectResponse(BaseUserProfilingResponse):
    """Base response class for direct profile operations"""

    uid: str = Field(description="User ID")
    pid: str = Field(description="Profile ID")


class UserProfilingDirectAddProfileResponse(UserProfilingDirectResponse):
    """Response for direct add profile operation"""

    data: Any


class UserProfilingDirectDeleteByPidRequest(BaseUserProfilingRequest):
    """Request for deleting a profile by PID"""

    pid: str = Field(description="Profile ID")


class UserProfilingDirectDeleteByPidResponse(UserProfilingDirectResponse):
    """Response for direct delete by pid operation"""

    data: Any = Field(description="Data of the deleted profile")


class UserProfilingDirectUpdateProfileRequest(BaseUserProfilingRequest):
    """Request for directly editing a profile"""

    pid: str = Field(description="Profile ID")
    content_before: Any = Field(description="Content before editing")
    content_after: Any = Field(description="Content after editing")


class UserProfilingDirectUpdateProfileResponse(UserProfilingDirectResponse):
    """Response for direct edit operation"""

    data: Any


class UserProfilingDirectConfirmProfileRequest(BaseUserProfilingRequest):
    """Request for directly confirming a profile"""

    pid: str = Field(description="Profile ID")


class UserProfilingDirectConfirmProfileResponse(BaseModel):
    """Response for direct confirm operation"""

    status: str
    data: UserProfilingShowAllUserProfilesData


# =============================================================================
# Task Status
# =============================================================================


class UserProfilingTaskStatusRequest(BaseModel):
    """Request for task status"""

    submit_id: str
