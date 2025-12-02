# -*- coding: utf-8 -*-
import pickle
from typing import Any, Optional, Type, TypeVar

from loguru import logger

from alias.server.exceptions.service import (
    DeserializationError,
    SerializationError,
)

from .base import BaseSerializer

T = TypeVar("T")


class PickleSerializer(BaseSerializer):
    """Pickle serializer implementation."""

    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol

    def serialize(self, obj: Any) -> Any:
        try:
            return pickle.dumps(obj, protocol=self.protocol)
        except Exception as e:
            logger.error(f"Pickle serialization failed: {str(e)}")
            raise SerializationError(
                f"Failed to serialize object: {str(e)}",
            ) from e

    def deserialize(self, data: Any, cls: Optional[Type[T]] = None) -> Any:
        try:
            obj = pickle.loads(data)
            if cls is not None and not isinstance(obj, cls):
                raise DeserializationError(
                    f"Deserialized obj is not an instance of {cls.__name__}",
                )
            return obj
        except Exception as e:
            logger.error(f"Pickle deserialization failed: {str(e)}")
            raise DeserializationError(
                f"Failed to deserialize data: {str(e)}",
            ) from e
