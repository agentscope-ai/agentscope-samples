# -*- coding: utf-8 -*-
"""
Custom exception classes for memory service
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class MemoryServiceError(Exception):
    """Base exception for memory service"""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(MemoryServiceError):
    """Validation error for request data"""

    def __init__(self, message: str, field: Optional[str] = None):
        error_code = (
            f"VALIDATION_ERROR_{field.upper()}"
            if field
            else "VALIDATION_ERROR"
        )
        super().__init__(message, error_code, 400)


class MissingRequiredFieldError(ValidationError):
    """Error for missing required fields"""

    def __init__(self, field: str):
        super().__init__(f"Missing required field: {field}", field)


class InvalidActionError(ValidationError):
    """Error for invalid action types"""

    def __init__(self, action: str):
        super().__init__(f"Invalid action type: {action}", "action_type")


class EmptyQueryError(ValidationError):
    """Error for empty queries"""

    def __init__(self):
        super().__init__("Query cannot be empty", "query")


class UserNotFoundError(MemoryServiceError):
    """Error when user is not found"""

    def __init__(self, uid: str):
        super().__init__(f"User not found: {uid}", "USER_NOT_FOUND", 404)


class UserProfilingServiceError(MemoryServiceError):
    """Error from memory service operations"""

    def __init__(
        self,
        message: str,
        error_code: str = "USER_PROFILING_SERVICE_ERROR",
        status_code: int = 503,
    ):
        super().__init__(message, error_code, status_code)


class TaskNotFoundError(MemoryServiceError):
    """Error when task is not found"""

    def __init__(self, submit_id: str):
        super().__init__(f"Task not found: {submit_id}", "TASK_NOT_FOUND", 404)


class ServiceUnavailableError(MemoryServiceError):
    """Error when service dependencies are unavailable"""

    def __init__(self, service: str):
        super().__init__(
            f"Service unavailable: {service}",
            "SERVICE_UNAVAILABLE",
            503,
        )


class EmptyStringFieldError(MemoryServiceError):
    """Error when field is empty"""

    def __init__(self, field: str):
        super().__init__(f"Field is empty: {field}", "EMPTY_STRING_FIELD", 400)


class ErrorResponse(BaseModel):
    """Standard error response format"""

    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
