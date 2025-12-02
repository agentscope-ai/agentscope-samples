# -*- coding: utf-8 -*-
"""
Task management API endpoints
"""

from datetime import datetime

from fastapi import APIRouter

from alias.memory_service.service.core.exceptions import (
    UserProfilingServiceError,
    TaskNotFoundError,
    ValidationError,
)
from alias.memory_service.service.core.task_manager import (
    UserProfilingTaskManager,
)
from alias.memory_service.profiling_utils.logging_utils import setup_logging

logger = setup_logging()
router = APIRouter(prefix="/alias_memory_service", tags=["tasks"])

# Task manager instance
task_manager = UserProfilingTaskManager()


@router.get("/task_status/{submit_id}")
async def get_task_status(submit_id: str):
    """Get the status of a background task by submit_id"""
    try:
        status = task_manager.get_task_status(submit_id)
        if status is None:
            raise TaskNotFoundError(submit_id)
        return {
            "submit_id": submit_id,
            "status": status["status"],
            "data": status,
        }
    except UserProfilingServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_task_status: {e}")
        raise UserProfilingServiceError(
            f"Failed to get task status: {str(e)}",
            "GET_TASK_STATUS_ERROR",
        ) from e


@router.get("/all_tasks")
async def get_all_tasks():
    """Get all tracked tasks (for debugging/monitoring)"""
    try:
        # Clean up old completed tasks first
        task_manager.cleanup_completed_tasks()

        all_tasks = {}
        for submit_id in task_manager.tasks:
            all_tasks[submit_id] = task_manager.get_task_status(submit_id)

        return {"status": "success", "data": all_tasks}
    except UserProfilingServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_all_tasks: {e}")
        raise UserProfilingServiceError(
            f"Failed to get all tasks: {str(e)}",
            "GET_ALL_TASKS_ERROR",
        ) from e


@router.get("/tasks_by_date/{date_str}")
async def get_tasks_by_date(date_str: str):
    """Get all tasks for a specific date (format: YYYY-MM-DD)"""
    try:
        task_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        tasks = task_manager.get_tasks_by_date(task_date)
        return {"status": "success", "date": date_str, "data": tasks}
    except ValueError as exc:
        raise ValidationError(
            "Invalid date format. Use YYYY-MM-DD",
            "date_format",
        ) from exc
    except UserProfilingServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_tasks_by_date: {e}")
        raise UserProfilingServiceError(
            f"Failed to get tasks by date: {str(e)}",
            "GET_TASKS_BY_DATE_ERROR",
        ) from e


@router.get("/tasks_by_date_range")
async def get_tasks_by_date_range(start_date: str, end_date: str):
    """Get all tasks within a date range (format: YYYY-MM-DD)"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            raise ValidationError(
                "Start date must be before end date",
                "date_range",
            )

        tasks = task_manager.get_tasks_by_date_range(start, end)
        return {
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "data": tasks,
        }
    except ValueError as exc:
        raise ValidationError(
            "Invalid date format. Use YYYY-MM-DD",
            "date_format",
        ) from exc
    except UserProfilingServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_tasks_by_date_range: {e}")
        raise UserProfilingServiceError(
            f"Failed to get tasks by date range: {str(e)}",
            "GET_TASKS_BY_DATE_RANGE_ERROR",
        ) from e


@router.get("/storage_stats")
async def get_storage_stats():
    """Get storage statistics for task files"""
    try:
        stats = task_manager.get_storage_stats()
        return {"status": "success", "data": stats}
    except UserProfilingServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_storage_stats: {e}")
        raise UserProfilingServiceError(
            f"Failed to get storage stats: {str(e)}",
            "GET_STORAGE_STATS_ERROR",
        ) from e
