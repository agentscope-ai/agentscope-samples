# -*- coding: utf-8 -*-
import json
from typing import Any, Optional, Type, TypeVar

from loguru import logger

from alias.server.exceptions.service import (
    DeserializationError,
    SerializationError,
)

from .base import BaseSerializer

T = TypeVar("T")


class JsonSerializer(BaseSerializer):
    """JSON serializer implementation."""

    def serialize(self, obj: Any) -> Any:
        if obj is None:
            return json.dumps(None)
        try:
            if hasattr(obj, "model_dump_json"):
                return obj.model_dump_json()
            if hasattr(obj, "model_dump"):
                obj = obj.model_dump()
            json_str = json.dumps(obj)
            return json_str
        except Exception as e:
            logger.error(f"JSON serialization failed: {str(e)}")
            raise SerializationError(
                f"Failed to serialize object: {str(e)}",
            ) from e

    def deserialize(
        self,
        data: Any,
        cls: Optional[Type[T]] = None,
    ) -> Any:  # mypy: disable=no-any-return
        if data is None:
            return None
        try:
            obj = json.loads(data)
            if cls is not None and obj is not None:
                if hasattr(cls, "model_validate"):
                    return cls.model_validate(obj)
            return obj
        except Exception as e:
            logger.error(f"JSON deserialization failed: {str(e)}")
            raise DeserializationError(
                f"Failed to deserialize data: {str(e)}",
            ) from e
