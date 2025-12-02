# -*- coding: utf-8 -*-
import asyncio
import uuid
from typing import Dict
from dataclasses import dataclass

from loguru import logger
from alias.server.utils.redis import redis_client


@dataclass
class TaskInfo:
    """Task information."""

    task_id: uuid.UUID
    task: asyncio.Task
    user_id: uuid.UUID


class TaskManager:
    """Task manager supporting task management, data waiting,
    and distributed stop."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._tasks: Dict[uuid.UUID, TaskInfo] = {}  # type: ignore
        self._stop_listener = None
        self._initialized = True
        logger.info("TaskManager initialized")

    async def start(self):
        """Start task manager."""
        if not self._stop_listener:
            self._stop_listener = asyncio.create_task(
                self._listen_stop_signals(),
            )
            logger.info("TaskManager started")

    async def stop(self):
        """Stop task manager."""
        if self._stop_listener:
            self._stop_listener.cancel()
            try:
                await self._stop_listener
            except asyncio.CancelledError:
                pass
            self._stop_listener = None

        for task_id in list(self._tasks.keys()):
            await self._stop_task(task_id)
        logger.info("TaskManager stopped")

    def register_task(
        self,
        task_id: uuid.UUID,
        task: asyncio.Task,
        user_id: uuid.UUID,
    ) -> None:
        """Register task."""
        task_info = TaskInfo(
            task_id=task_id,
            task=task,
            user_id=user_id,
        )
        self._tasks[task_id] = task_info
        logger.info(f"Task {task_id} registered")

    async def stop_task(
        self,
        task_id: uuid.UUID,
    ) -> bool:
        """Send stop signal."""
        try:
            result = await self._stop_task(task_id)
            if result:
                return True

            await redis_client.setex(
                f"task_stop:{task_id}",
                300,
                "1",
            )
            logger.info(f"Stop signal sent for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop task {task_id}: {e}")
            return False

    async def _stop_task(self, task_id: uuid.UUID) -> bool:
        """Execute task stop."""
        task_info = self._tasks.pop(task_id, None)
        if not task_info:
            return False

        if not task_info.task.done():
            task_info.task.cancel()
            try:
                await task_info.task
            except asyncio.CancelledError:
                pass

        import threading

        logger.info(
            f"Task {task_id} stopped and cleaned up",
            threading.current_thread().ident,
        )
        return True

    async def _listen_stop_signals(self):
        """Listen for stop signals."""
        try:
            while True:
                task_ids = list(self._tasks.keys())
                for task_id in task_ids:
                    stop_key = f"task_stop:{task_id}"
                    if await redis_client.exists(stop_key):
                        await self._stop_task(task_id)
                        await redis_client.delete(stop_key)
                        continue

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Signal listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in signal listener: {e}")
            raise

        finally:
            import traceback

            logger.error(f"Error in signal listener: {traceback.format_exc()}")


task_manager = TaskManager()
