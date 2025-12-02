# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Any, List, Union, Optional

from agentscope.message import Msg


class BaseMemory(ABC):
    """Base class for memory."""

    def __init__(self):
        pass

    @abstractmethod
    async def retrieve(self, uid: str, query: str, **kwargs) -> Any | bool:
        """retrieve memory"""

    @abstractmethod
    async def add_memory(self, uid: str, content: List[Msg], **kwargs) -> Any:
        """Save content to memory."""

    @abstractmethod
    async def process_content(self, uid: str, content: Union[List[Msg], Msg]):
        """extract info in content for memory."""

    @abstractmethod
    async def delete(self, uid: str, key: Any) -> None:
        """Delete part of memory by some criteria."""

    @abstractmethod
    async def clear_memory(self, uid: str) -> None:
        """Clear all memory."""

    @abstractmethod
    async def show_all_memory(self, uid: str) -> Any:
        """Show all memory."""

    @abstractmethod
    async def record_action(
        self,
        uid: str,
        action: str,
        session_id: Optional[str] = None,
        reference_time: Optional[str] = None,
        action_message_id: Optional[str] = None,
        data: Optional[Any] = None,
        session_content=None,
        **kwargs,
    ):
        """
        record the action of the user
        Args:
            uid (str): the user id
            action (str): the action
            session_id (str): the session id
            reference_time (str): the reference time
            action_message_id (str): the action message id
            data (Any): the user edit or chat content
            session_content (list): the session content
        Returns:
            dict: the result of the action
        """
