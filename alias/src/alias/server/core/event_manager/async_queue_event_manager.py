# -*- coding: utf-8 -*-
import uuid
import asyncio

from .base import BaseEventManager


class AsyncQueueEventManager(BaseEventManager):
    def __init__(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        _queue = asyncio.Queue()
        super().__init__(
            task_id=task_id,
            user_id=user_id,
            queue=_queue,
        )
