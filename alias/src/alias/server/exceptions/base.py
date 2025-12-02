# -*- coding: utf-8 -*-
"""The base exceptions"""

from typing import Optional, Union


class BaseError(Exception):
    """The base exception"""

    code: Optional[int] = None
    message: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[int] = None,
        extra_info: Optional[Union[str, dict, list]] = None,
    ) -> None:
        """Initialize the base exception"""
        self.message = message or self.message
        if extra_info:
            self.message = f"{self.message}: {extra_info}"
        self.code = self.code if code is None else code
        super().__init__(message)

    def __str__(self):
        return self.message or self.__class__.__name__


class InternalServerError(BaseError):
    """The internal server error"""

    code = 500
    message = "Internal server error"


class NotFoundError(BaseError):
    """The not found exception"""

    code = 404
    message = "Not found"


class AlreadyExistsError(BaseError):
    """The already exists exception"""

    code = 409
    message = "Already exists"


class DisabledError(BaseError):
    """The disabled exception"""

    code = 403
    message = "Feature Disabled"


class AccessDeniedError(BaseError):
    """The access denied exception"""

    code = 403
    message = "Access denied"


class PermissionDeniedError(BaseError):
    """The permission denied exception"""

    code = 403
    message = "Permission denied"


class IncorrectParameterError(BaseError):
    """The incorrect parameter exception"""

    code = 400
    message = "Incorrect parameter"


class InvalidError(BaseError):
    """The invalid exception"""

    code = 400
    message = "Invalid"


class ValidationError(BaseError):
    """The validation error"""

    code = 400
    message = "Validation error"


class NotSetError(BaseError):
    """The not set exception"""

    code = 400
    message = "Not set"


class ExpiredError(BaseError):
    """The expired exception"""

    code = 401
    message = "Expired error"


class ServiceError(BaseError):
    """The base service error for third-party service calls"""

    code = 503
    message = "Service error"
