# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


class BaseSerializer(ABC):
    @abstractmethod
    def serialize(self, obj: Any) -> Any:
        pass

    @abstractmethod
    def deserialize(self, data: Any, cls: Optional[Type[T]] = None) -> Any:
        pass
