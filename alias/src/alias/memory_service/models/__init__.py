# -*- coding: utf-8 -*-
"""
Memory Service for Alias

This package provides a service-based approach for user profiling functionality
with independent dependency management.
"""

from alias.memory_service.models.user_profiling import (
    UserProfilingServiceSettings,
    UserProfilingAddRequest,
    UserProfilingRetrieveRequest,
    UserProfilingProcessRequest,
    UserProfilingShowAllRequest,
    UserProfilingDeleteRequest,
    UserProfilingRecordActionRequest,
    UserProfilingTaskStatusRequest,
    UserProfilingClearRequest,
    UserProfilingResponseSubmitId,
    UserProfilingResponseSubmitIdStatus,
    UserProfilingRetrieveResponse,
    UserProfilingShowAllResponse,
)

__all__ = [
    "UserProfilingServiceSettings",
    "UserProfilingAddRequest",
    "UserProfilingRetrieveRequest",
    "UserProfilingProcessRequest",
    "UserProfilingShowAllRequest",
    "UserProfilingDeleteRequest",
    "UserProfilingRecordActionRequest",
    "UserProfilingTaskStatusRequest",
    "UserProfilingClearRequest",
    "UserProfilingResponseSubmitId",
    "UserProfilingResponseSubmitIdStatus",
    "UserProfilingRetrieveResponse",
    "UserProfilingShowAllResponse",
]
