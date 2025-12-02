# -*- coding: utf-8 -*-
import asyncio
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import redis

# from loguru import logger
from alias.memory_service.service.config.redis_config import redis_config
from alias.memory_service.profiling_utils.logging_utils import setup_logging

logger = setup_logging()


# Redis-based task manager to track background tasks
class UserProfilingTaskManager:
    """
    Redis-based task manager to track background tasks
    """

    def __init__(
        self,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_db: Optional[int] = None,
        redis_password: Optional[str] = None,
    ):
        """
        Initialize the task manager with Redis storage

        Args:
            redis_host (str, optional): Redis server host
                (defaults to config)
            redis_port (int, optional): Redis server port
                (defaults to config)
            redis_db (int, optional): Redis database number
                (defaults to config)
            redis_password (str, optional): Redis password
                (defaults to config)
        """
        # Use provided parameters or fall back to config
        host = redis_host or redis_config.REDIS_HOST
        port = redis_port or redis_config.REDIS_PORT
        db = redis_db or redis_config.REDIS_DB
        password = redis_password or redis_config.REDIS_PASSWORD

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Redis connection established: {host}:{port}/{db}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # Key prefixes for different data types
        self.task_prefix = f"{redis_config.KEY_PREFIX}:task:"
        self.task_index_prefix = f"{redis_config.KEY_PREFIX}:index:"
        self.task_date_prefix = f"{redis_config.KEY_PREFIX}:date:"
        self.task_status_prefix = f"{redis_config.KEY_PREFIX}:status:"

        # Default expiration time for tasks
        self.default_expiry = redis_config.get_task_expiry_seconds()

        logger.info("UserProfilingTaskManager initialized with Redis storage")

    def _get_task_key(self, submit_id: str) -> str:
        """Get Redis key for a specific task"""
        return f"{self.task_prefix}{submit_id}"

    def _get_index_key(self, submit_id: str) -> str:
        """Get Redis key for task index"""
        return f"{self.task_index_prefix}{submit_id}"

    def _get_date_key(self, task_date: date) -> str:
        """Get Redis key for tasks on a specific date"""
        return f"{self.task_date_prefix}{task_date.isoformat()}"

    def _get_status_key(self, status: str) -> str:
        """Get Redis key for tasks with a specific status"""
        return f"{self.task_status_prefix}{status}"

    def _serialize_task(self, task_data: Dict[str, Any]) -> str:
        """Serialize task data to JSON string"""
        # Convert datetime objects to ISO format for JSON serialization
        serialized_data = task_data.copy()
        for key, value in task_data.items():
            if isinstance(value, datetime):
                serialized_data[key] = value.isoformat()
        return json.dumps(serialized_data)

    def _deserialize_task(self, task_json: str) -> Dict[str, Any]:
        """Deserialize task data from JSON string"""
        task_data = json.loads(task_json)
        # Convert ISO format strings back to datetime objects
        for key in ["created_at", "completed_at"]:
            if key in task_data and task_data[key]:
                try:
                    task_data[key] = datetime.fromisoformat(task_data[key])
                except (ValueError, TypeError):
                    pass  # Keep as string if parsing fails
        return task_data

    def add_task(self, submit_id: str, task: asyncio.Task, task_type: str):
        """
        Add a task to the task manager

        Args:
            submit_id (str): Unique task identifier
            task (asyncio.Task): The asyncio task object (currently unused,
                kept for future use)
            task_type (str): Type of the task
        """
        # Task object is kept for potential future use (e.g., cancellation)
        # Assign to _ to indicate it's intentionally unused
        _ = task  # noqa: F841
        current_date = date.today()
        task_data = {
            "task_type": task_type,
            "status": "running",
            "created_at": datetime.now(),
            "completed_at": None,
            "result": None,
            "error": None,
            "date": current_date.isoformat(),
        }

        # Store task data
        task_key = self._get_task_key(submit_id)
        self.redis_client.setex(
            task_key,
            self.default_expiry,
            self._serialize_task(task_data),
        )

        # Update index
        index_key = self._get_index_key(submit_id)
        self.redis_client.setex(
            index_key,
            self.default_expiry,
            current_date.isoformat(),
        )

        # Add to date-based set
        date_key = self._get_date_key(current_date)
        self.redis_client.sadd(date_key, submit_id)
        self.redis_client.expire(date_key, self.default_expiry)

        # Add to status-based set
        status_key = self._get_status_key("running")
        self.redis_client.sadd(status_key, submit_id)
        self.redis_client.expire(status_key, self.default_expiry)

        logger.info(f"Task {submit_id} added to Redis storage")

    def update_task_status(
        self,
        submit_id: str,
        status: str,
        result: Any = None,
        error: str = None,
    ):
        """
        Update the status of a task

        Args:
            submit_id (str): Task identifier
            status (str): New status
            result (Any, optional): Task result
            error (str, optional): Error message
        """
        task_key = self._get_task_key(submit_id)
        task_json = self.redis_client.get(task_key)

        if task_json:
            task_data = self._deserialize_task(task_json)
            old_status = task_data.get("status", "unknown")

            # Update task data
            task_data["status"] = status
            task_data["completed_at"] = datetime.now()
            if result is not None:
                task_data["result"] = result
            if error is not None:
                task_data["error"] = error

            # Save updated task
            self.redis_client.setex(
                task_key,
                self.default_expiry,
                self._serialize_task(task_data),
            )

            # Update status-based sets
            if old_status != status:
                # Remove from old status set
                old_status_key = self._get_status_key(old_status)
                self.redis_client.srem(old_status_key, submit_id)

                # Add to new status set
                new_status_key = self._get_status_key(status)
                self.redis_client.sadd(new_status_key, submit_id)
                self.redis_client.expire(new_status_key, self.default_expiry)

            logger.info(f"Task {submit_id} status updated to {status}")
        else:
            logger.warning(f"Task {submit_id} not found in Redis")

    def get_task_status(self, submit_id: str) -> Dict[str, Any]:
        """
        Get the status of a task

        Args:
            submit_id (str): Task identifier

        Returns:
            Dict[str, Any]: Task information or error message
        """
        task_key = self._get_task_key(submit_id)
        task_json = self.redis_client.get(task_key)

        if task_json:
            return self._deserialize_task(task_json)

        return {"error": "Task not found"}

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks from Redis

        Returns:
            Dict[str, Dict[str, Any]]: All tasks
        """
        all_tasks = {}
        pattern = f"{self.task_prefix}*"

        for key in self.redis_client.scan_iter(match=pattern):
            submit_id = key.replace(self.task_prefix, "")
            task_json = self.redis_client.get(key)
            if task_json:
                all_tasks[submit_id] = self._deserialize_task(task_json)

        return all_tasks

    def get_tasks_by_date(self, task_date: date) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks for a specific date

        Args:
            task_date (date): The date to get tasks for

        Returns:
            Dict[str, Dict[str, Any]]: Tasks for the specified date
        """
        tasks = {}
        date_key = self._get_date_key(task_date)
        submit_ids = self.redis_client.smembers(date_key)

        for submit_id in submit_ids:
            task_key = self._get_task_key(submit_id)
            task_json = self.redis_client.get(task_key)
            if task_json:
                tasks[submit_id] = self._deserialize_task(task_json)

        return tasks

    def get_tasks_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks within a date range

        Args:
            start_date (date): Start date (inclusive)
            end_date (date): End date (inclusive)

        Returns:
            Dict[str, Dict[str, Any]]: Tasks within the date range
        """
        all_tasks = {}
        current_date = start_date

        while current_date <= end_date:
            tasks = self.get_tasks_by_date(current_date)
            all_tasks.update(tasks)
            current_date = current_date + timedelta(days=1)

        return all_tasks

    def get_tasks_by_status(self, status: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks with a specific status

        Args:
            status (str): The status to filter by

        Returns:
            Dict[str, Dict[str, Any]]: Tasks with the specified status
        """
        tasks = {}
        status_key = self._get_status_key(status)
        submit_ids = self.redis_client.smembers(status_key)

        for submit_id in submit_ids:
            task_key = self._get_task_key(submit_id)
            task_json = self.redis_client.get(task_key)
            if task_json:
                tasks[submit_id] = self._deserialize_task(task_json)

        return tasks

    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Clean up completed tasks older than max_age_hours

        Args:
            max_age_hours (int): Maximum age in hours for completed
                tasks to keep
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        completed_statuses = ["completed", "failed"]

        for status in completed_statuses:
            status_key = self._get_status_key(status)
            submit_ids = self.redis_client.smembers(status_key)

            for submit_id in submit_ids:
                task_key = self._get_task_key(submit_id)
                task_json = self.redis_client.get(task_key)

                if task_json:
                    task_data = self._deserialize_task(task_json)
                    completed_at = task_data.get("completed_at")

                    if completed_at and completed_at < cutoff_time:
                        # Remove task from all sets and delete task data
                        self.delete_task(submit_id)

        logger.info(
            f"Cleaned up completed tasks older than {max_age_hours} hours",
        )

    def delete_task(self, submit_id: str) -> bool:
        """
        Delete a specific task

        Args:
            submit_id (str): The task ID to delete

        Returns:
            bool: True if task was deleted, False if not found
        """
        task_key = self._get_task_key(submit_id)
        task_json = self.redis_client.get(task_key)

        if task_json:
            task_data = self._deserialize_task(task_json)
            status = task_data.get("status", "unknown")
            task_date_str = task_data.get("date")

            # Delete task data
            self.redis_client.delete(task_key)

            # Remove from index
            index_key = self._get_index_key(submit_id)
            self.redis_client.delete(index_key)

            # Remove from date set
            if task_date_str:
                try:
                    task_date = datetime.strptime(
                        task_date_str,
                        "%Y-%m-%d",
                    ).date()
                    date_key = self._get_date_key(task_date)
                    self.redis_client.srem(date_key, submit_id)
                except ValueError:
                    pass

            # Remove from status set
            status_key = self._get_status_key(status)
            self.redis_client.srem(status_key, submit_id)

            logger.info(f"Task {submit_id} deleted from Redis")
            return True

        return False

    def clear_all_tasks(self):
        """
        Clear all tasks from Redis
        """
        # Delete all task keys
        pattern = f"{self.task_prefix}*"
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)

        # Delete all index keys
        pattern = f"{self.task_index_prefix}*"
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)

        # Delete all date keys
        pattern = f"{self.task_date_prefix}*"
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)

        # Delete all status keys
        pattern = f"{self.task_status_prefix}*"
        for key in self.redis_client.scan_iter(match=pattern):
            self.redis_client.delete(key)

        logger.info("All tasks cleared from Redis")

    def get_task_count(self) -> int:
        """
        Get the total number of tasks

        Returns:
            int: Total number of tasks
        """
        pattern = f"{self.task_prefix}*"
        count = 0
        for _ in self.redis_client.scan_iter(match=pattern):
            count += 1
        return count

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Dict[str, Any]: Storage statistics
        """
        stats: Dict[str, Any] = {
            "total_tasks": 0,
            "tasks_by_status": {},
            "tasks_by_date": {},
            "redis_info": {},
        }

        # Count total tasks
        stats["total_tasks"] = self.get_task_count()

        # Count tasks by status
        for status in ["running", "completed", "failed", "pending"]:
            status_key = self._get_status_key(status)
            count = self.redis_client.scard(status_key)
            stats["tasks_by_status"][status] = count

        # Count tasks by date (last 7 days)
        for i in range(7):
            check_date = date.today() - timedelta(days=i)
            date_key = self._get_date_key(check_date)
            count = self.redis_client.scard(date_key)
            stats["tasks_by_date"][check_date.isoformat()] = count

        # Redis info
        try:
            info = self.redis_client.info()
            stats["redis_info"] = {
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
                "total_commands_processed": info.get(
                    "total_commands_processed",
                    "N/A",
                ),
            }
        except Exception as e:
            stats["redis_info"] = {"error": str(e)}

        return stats

    def rebuild_index(self) -> int:
        """
        Rebuild the task index by scanning all tasks
        Useful for fixing corrupted index or migrating from old version

        Returns:
            int: Number of tasks indexed
        """
        logger.info("Rebuilding task index...")
        index_count = 0

        pattern = f"{self.task_prefix}*"
        for key in self.redis_client.scan_iter(match=pattern):
            submit_id = key.replace(self.task_prefix, "")
            task_json = self.redis_client.get(key)

            if task_json:
                task_data = self._deserialize_task(task_json)
                task_date_str = task_data.get("date")

                if task_date_str:
                    # Update index
                    index_key = self._get_index_key(submit_id)
                    self.redis_client.setex(
                        index_key,
                        self.default_expiry,
                        task_date_str,
                    )
                    index_count += 1

        logger.info(f"Index rebuilt with {index_count} tasks")
        return index_count

    def set_task_expiry(self, submit_id: str, expiry_seconds: int):
        """
        Set custom expiry time for a specific task

        Args:
            submit_id (str): Task identifier
            expiry_seconds (int): Expiry time in seconds
        """
        task_key = self._get_task_key(submit_id)
        index_key = self._get_index_key(submit_id)

        if self.redis_client.exists(task_key):
            self.redis_client.expire(task_key, expiry_seconds)
            self.redis_client.expire(index_key, expiry_seconds)
            logger.info(
                f"Set expiry for task {submit_id} to {expiry_seconds} seconds",
            )
        else:
            logger.warning(f"Task {submit_id} not found")

    def get_redis_client(self) -> redis.Redis:
        """
        Get the underlying Redis client for advanced operations

        Returns:
            redis.Redis: Redis client instance
        """
        return self.redis_client
