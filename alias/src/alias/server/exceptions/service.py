# -*- coding: utf-8 -*-
"""The services exceptions"""

from .base import (
    AccessDeniedError,
    AlreadyExistsError,
    DisabledError,
    ExpiredError,
    IncorrectParameterError,
    InternalServerError,
    InvalidError,
    NotFoundError,
    ServiceError,
)


class UserNotFoundError(NotFoundError):
    """The user not found exception"""

    message = "User not found"


class ConversationNotFoundError(NotFoundError):
    """The conversation not found exception"""

    message = "Conversation not found"


class MessageNotFoundError(NotFoundError):
    """The message not found exception"""

    message = "Message not found"


class PlanNotFoundError(NotFoundError):
    """The Plan not found exception"""

    message = "Plan not found"


class StateNotFoundError(NotFoundError):
    """The State not found exception"""

    message = "State not found"


class EmailAlreadyExistsError(AlreadyExistsError):
    """The email already exists exception"""

    message = "Email already exists"


class UserAlreadyExistsError(AlreadyExistsError):
    """The user already exists exception"""

    message = "User already exists"


class UserEmailAlreadyExistsError(AlreadyExistsError):
    """The user email already exists exception"""

    message = "User email already exists"


class UserAccessDeniedError(AccessDeniedError):
    """The user access denied exception"""

    message = "User access denied"


class ConversationAccessDeniedError(AccessDeniedError):
    """The conversation access denied exception"""

    message = "Conversation access denied"


class IncorrectEmailError(IncorrectParameterError):
    """The incorrect email exception"""

    message = "Incorrect email"


class IncorrectPasswordError(IncorrectParameterError):
    """The incorrect password exception"""

    message = "Incorrect password"


class InvalidTokenError(InvalidError):
    """The invalid token exception"""

    message = "Invalid token"


class InvalidBase64ImageError(InvalidError):
    """The invalid base64 image exception"""

    message = "Invalid base64 image"


class InvalidMessageError(InvalidError):
    """The invalid message exception"""

    message = "Invalid message"


class InvalidToolMessageError(InvalidMessageError):
    """The invalid message exception"""

    message = "Invalid tool message"


class TokenExpiredError(ExpiredError):
    """Token expired exception"""

    message = "Token expired"


class MemoryServiceError(ServiceError):
    """The memory service error"""

    message = "Memory Service error"


class MessageServiceError(ServiceError):
    """The message service error"""

    message = "Message Service error"


class StateServiceError(ServiceError):
    """The state service error"""

    message = "State Service error"


class PlanServiceError(ServiceError):
    """The plan service error"""

    message = "Plan Service error"


class SerializationError(InternalServerError):
    """Raised when serialization fails."""

    message = "Serialization error"


class DeserializationError(InternalServerError):
    """Raised when deserialization fails."""

    message = "Deserialization error"


class BackgroundChatError(DisabledError):
    """Raised when background chat fails."""

    message = "Background chat disabled"
