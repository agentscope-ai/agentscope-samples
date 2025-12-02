# -*- coding: utf-8 -*-
"""
User Profiling Service for Alias

This package provides a service-based approach for user profiling functionality
with independent dependency management.
"""

__version__ = "0.1.0"
__author__ = "Alias Team"


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
    UserProfilingDirectAddProfileRequest,
    UserProfilingDirectDeleteByPidRequest,
    UserProfilingDirectUpdateProfileRequest,
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
    "UserProfilingDirectAddProfileRequest",
    "UserProfilingDirectDeleteByPidRequest",
    "UserProfilingDirectUpdateProfileRequest",
    "UserProfilingResponseSubmitId",
    "UserProfilingResponseSubmitIdStatus",
    "UserProfilingRetrieveResponse",
    "UserProfilingShowAllResponse",
]
