# -*- coding: utf-8 -*-
import asyncio
import time
import uuid
from typing import AsyncGenerator

from alias.server.core.config import settings
from alias.server.core.event import Event, HeartBeatEvent, StopEvent


class BaseEventManager:
    def __init__(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        queue: asyncio.Queue,
        heartbeat_interval: int = 0,
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.queue = queue
        self.heartbeat_interval = (
            heartbeat_interval or settings.HEARTBEAT_INTERVAL
        )

    async def put(self, event: Event) -> None:
        await self.queue.put(event)

    async def stop(self):
        await self.put(StopEvent())

    async def listen(self) -> AsyncGenerator[Event, None]:
        start_time = time.time()
        last_event_time = start_time

        while True:
            try:
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0,
                )

                if isinstance(event, (StopEvent)):
                    yield event
                    return

                yield event

                last_event_time = time.time()

            except asyncio.TimeoutError:
                pass
            except Exception:
                continue
            finally:
                current_time = time.time()
                working_time = current_time - start_time

                if working_time > settings.MAX_CHAT_EXECUTION_TIME:
                    break  # pylint: disable=W0150

                if (
                    self.heartbeat_interval > 0
                    and current_time - last_event_time
                    > self.heartbeat_interval
                ):
                    await self.put(HeartBeatEvent())
                    last_event_time = current_time

    async def close(self):
        while not self.queue.empty():
            try:
                await self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        await self.stop()
