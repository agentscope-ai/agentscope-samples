# -*- coding: utf-8 -*-
from typing import Any, Optional, Type, TypeVar

from .base import BaseSerializer

T = TypeVar("T")


class NoOpSerializer(BaseSerializer):
    def serialize(self, obj: Any) -> Any:
        return obj

    def deserialize(self, data: Any, cls: Optional[Type[T]] = None) -> Any:
        return data
