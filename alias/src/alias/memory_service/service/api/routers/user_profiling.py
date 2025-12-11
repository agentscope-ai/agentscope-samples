# -*- coding: utf-8 -*-
"""
User profiling API endpoints
"""

import asyncio
import uuid
from fastapi import APIRouter

from alias.memory_service.models.user_profiling import (
    UserProfilingAddRequest,
    UserProfilingClearRequest,
    UserProfilingRetrieveRequest,
    UserProfilingRetrieveResponse,
    UserProfilingShowAllRequest,
    UserProfilingShowAllResponse,
    UserProfilingRecordActionRequest,
    UserProfilingDirectAddProfileRequest,
    UserProfilingDirectAddProfileResponse,
    UserProfilingDirectDeleteByPidRequest,
    UserProfilingDirectDeleteByPidResponse,
    UserProfilingDirectUpdateProfileRequest,
    UserProfilingDirectUpdateProfileResponse,
    UserProfilingShowAllUserProfilesRequest,
    UserProfilingShowAllUserProfilesResponse,
    UserProfilingResponseSubmitId,
    UserProfilingDirectConfirmProfileRequest,
    UserProfilingDirectConfirmProfileResponse,
    UserProfilingShowAllUserProfilesData,
)
from alias.memory_service.service.core.exceptions import (
    MemoryServiceError,
    EmptyQueryError,
)
from alias.memory_service.service.api.dependencies import (
    get_memory_service,
)
from alias.memory_service.service.core.task_manager import (
    UserProfilingTaskManager,
)
from alias.memory_service.profiling_utils.logging_utils import setup_logging
from alias.memory_service.profiling_utils import get_messages_by_session_id

logger = setup_logging()
router = APIRouter(prefix="/alias_memory_service", tags=["user_profiling"])

# Task manager instance
task_manager = UserProfilingTaskManager()


@router.post("/user_profiling/add")
async def add_memory(request: UserProfilingAddRequest):
    """
    Send source content to the memory service, the content will be processed
    by the memory service and stored. It submits a background task to the task
    manager, and returns the submit_id.

    Args:
        request (dict): uid, content

    Raises:
        UserProfilingServiceError: if the request is invalid

    Returns:
        dict: status, submit_id
    """
    try:
        submit_id = str(uuid.uuid4())

        async def background_add_memory():
            try:
                memory_service = get_memory_service()
                result = await memory_service.add_memory(
                    request.uid,
                    request.content,
                )
                task_manager.update_task_status(
                    submit_id,
                    "completed",
                    result=result,
                )
                logger.info(
                    f"Background add_memory completed for submit_id: "
                    f"{submit_id}, result: {result}",
                )
            except Exception as e:
                error_msg = str(e)
                task_manager.update_task_status(
                    submit_id,
                    "failed",
                    error=error_msg,
                )
                logger.error(
                    f"Background add_memory failed for submit_id: "
                    f"{submit_id}, error: {error_msg}",
                )

        task = asyncio.create_task(background_add_memory())
        task_manager.add_task(submit_id, task, "add_memory")

        return UserProfilingResponseSubmitId(
            status="submit success",
            submit_id=submit_id,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_memory: {e}")
        raise MemoryServiceError(
            f"Failed to add memory: {str(e)}",
            "ADD_MEMORY_ERROR",
        ) from e


@router.post("/user_profiling/clear")
async def clear_memory(
    request: UserProfilingClearRequest,
) -> UserProfilingResponseSubmitId:
    """Clear all memory for a user"""
    logger.info(f"clear_memory request received: {request}")
    try:
        submit_id = str(uuid.uuid4())

        async def background_clear_memory():
            try:
                memory_service = get_memory_service()
                await memory_service.clear_memory(request.uid)
                task_manager.update_task_status(submit_id, "completed")
                logger.info(
                    f"Background clear_memory completed for submit_id: "
                    f"{submit_id}",
                )
            except Exception as e:
                error_msg = str(e)
                task_manager.update_task_status(
                    submit_id,
                    "failed",
                    error=error_msg,
                )
                logger.error(
                    f"Background clear_memory failed for submit_id: "
                    f"{submit_id}, error: {error_msg}",
                )

        task = asyncio.create_task(background_clear_memory())
        task_manager.add_task(submit_id, task, "clear_memory")

        return UserProfilingResponseSubmitId(
            status="submit success",
            submit_id=submit_id,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in clear_memory: {e}")
        raise MemoryServiceError(
            f"Failed to clear memory: {str(e)}",
            "CLEAR_MEMORY_ERROR",
        ) from e


@router.post("/user_profiling/retrieve")
async def retrieve_memory(
    request: UserProfilingRetrieveRequest,
) -> UserProfilingRetrieveResponse:
    """Retrieve memory based on query"""
    logger.info(f"retrieve_memory request received: {request}")
    try:
        if not request.query.strip():
            raise EmptyQueryError()

        memory_service = get_memory_service()
        result = await memory_service.retrieve(
            request.uid,
            request.query,
            limit=request.limit,
            threshold=request.threshold,
        )
        return UserProfilingRetrieveResponse(
            status="success",
            uid=request.uid,
            query=request.query,
            data=result,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_memory: {e}")
        raise MemoryServiceError(
            f"Failed to retrieve memory: {str(e)}",
            "RETRIEVE_MEMORY_ERROR",
        ) from e


@router.post("/user_profiling/show_all_user_profiles")
async def show_all_user_profiles(
    request: UserProfilingShowAllUserProfilesRequest,
) -> UserProfilingShowAllUserProfilesResponse:
    """Show all user profiles for a user"""
    logger.info(f"show_all_user_profiles request received: {request}")
    try:
        memory_service = get_memory_service()
        result = await memory_service.show_all_user_profiles(request.uid)
        return UserProfilingShowAllUserProfilesResponse(
            status="success",
            data=result,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in show_all_user_profiles: {e}")
        raise MemoryServiceError(
            f"Failed to show all user profiles: {str(e)}",
            "SHOW_ALL_USER_PROFILES_ERROR",
        ) from e


def _validate_result_serializable(result: dict) -> None:
    """
    Validate that the result dictionary is serializable
    (no coroutines present)

    Args:
        result: The result dictionary to validate

    Raises:
        ValueError: If coroutines are found in the result
    """
    for key, value in result.items():
        if hasattr(value, "__await__"):
            logger.error(
                f"Found coroutine in endpoint result[{key}]: {value}",
            )
            raise ValueError(
                f"Coroutine found in endpoint result[{key}]",
            )
        if isinstance(value, list):
            for i, item in enumerate(value):
                if hasattr(item, "__await__"):
                    logger.error(
                        f"Found coroutine in endpoint result"
                        f"[{key}][{i}]: {item}",
                    )
                    raise ValueError(
                        f"Coroutine found in endpoint result" f"[{key}][{i}]",
                    )


@router.post("/user_profiling/show_all")
async def show_all_memory(
    request: UserProfilingShowAllRequest,
) -> UserProfilingShowAllResponse:
    """Show all memory for a user"""
    logger.info(f"show_all_memory request received: {request}")
    try:
        memory_service = get_memory_service()
        result = await memory_service.show_all_memory(request.uid)

        logger.info(f"show_all_memory endpoint result type: {type(result)}")
        logger.info(f"show_all_memory endpoint result: {result}")

        # Ensure the result is serializable
        if isinstance(result, dict):
            _validate_result_serializable(result)

        response = UserProfilingShowAllResponse(status="success", data=result)
        logger.info(f"show_all_memory endpoint response: {response}")
        return response
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in show_all_memory: {e}")
        raise MemoryServiceError(
            f"Failed to show all memory: {str(e)}",
            "SHOW_ALL_MEMORY_ERROR",
        ) from e


@router.post("/record_action")
async def record_action(
    request: UserProfilingRecordActionRequest,
) -> UserProfilingResponseSubmitId:
    """Record user action"""
    logger.info(f"record_action request received: {request}")
    try:
        submit_id = str(uuid.uuid4())

        async def background_record_action():
            try:
                action_value = (
                    request.action_type.value
                    if request.action_type
                    else request.action
                )
                message_id = request.message_id or request.action_message_id
                logger.info(
                    f"Starting background_record_action for submit_id: "
                    f"{submit_id}, action_type: {action_value}, "
                    f"session_id: {request.session_id}",
                )
                session_content = await get_messages_by_session_id(
                    request.session_id,
                )
                logger.info(
                    f"session_id: {request.session_id}, "
                    f"Retrieved session_content length: "
                    f"{len(session_content) if session_content else 0}",
                )
                if not session_content:
                    if request.data.get("session_content") is not None:
                        session_content = request.data["session_content"]
                        logger.info(
                            f"Using session_content from request data: "
                            f"{session_content}",
                        )
                    else:
                        session_content = []
                        logger.error(
                            "No session_content found in request data and "
                            "get_messages_by_session_id returned empty list",
                        )
                if action_value == "TASK_STOP":
                    memory_type = "tool_memory"
                else:
                    memory_type = "user_profiling"
                memory_service = get_memory_service(memory_type)
                result = await memory_service.record_action(
                    uid=request.uid,
                    action=action_value,
                    session_id=request.session_id,
                    reference_time=request.reference_time,
                    action_message_id=message_id,
                    data=request.data,
                    session_content=session_content,
                )
                task_manager.update_task_status(
                    submit_id,
                    "completed",
                    result=result,
                )
                logger.info(
                    f"Background record_action completed for submit_id: "
                    f"{submit_id}",
                )
            except Exception as e:
                import traceback

                error_msg = str(e)
                full_traceback = traceback.format_exc()
                task_manager.update_task_status(
                    submit_id,
                    "failed",
                    error=error_msg,
                )
                logger.error(
                    f"Background record_action failed for submit_id: "
                    f"{submit_id}",
                )
                logger.error(f"Error details: {error_msg}")
                logger.error(f"Full traceback:\n{full_traceback}")
                logger.error(
                    f"Request context: uid={request.uid}, "
                    f"action_type={request.action_type}, "
                    f"session_id={request.session_id}, "
                    f"message_id={request.message_id}",
                )

        task = asyncio.create_task(background_record_action())
        task_manager.add_task(submit_id, task, "record_action")

        return UserProfilingResponseSubmitId(
            status="submit success",
            submit_id=submit_id,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in record_action: {e}")
        raise MemoryServiceError(
            f"Failed to record action: {str(e)}",
            "RECORD_ACTION_ERROR",
        ) from e


@router.post("/user_profiling/direct_add_profile")
async def direct_add_profile(
    request: UserProfilingDirectAddProfileRequest,
) -> UserProfilingDirectAddProfileResponse:
    """
    Direct add profile to the memory service

    Args:
        request (UserProfilingDirectAddProfileRequest): uid, content,
            profiling_id
    """
    logger.info(f"direct_add_profile request received: {request}")
    try:
        memory_service = get_memory_service()
        result = await memory_service.direct_add_profile(
            request.uid,
            request.content,
        )
        return UserProfilingDirectAddProfileResponse(
            status="success",
            uid=request.uid,
            pid=result["results"][0]["id"],
            data=result,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in direct_add_profile: {e}",
            exc_info=True,
        )
        raise MemoryServiceError(
            f"Failed to direct add profile: {str(e)}",
            "DIRECT_ADD_PROFILE_ERROR",
        ) from e


@router.post("/user_profiling/direct_delete_by_profiling_id")
async def direct_delete_by_profiling_id(
    request: UserProfilingDirectDeleteByPidRequest,
) -> UserProfilingDirectDeleteByPidResponse:
    """
    Direct delete profile by profiling_id

    Args:
        request (UserProfilingDirectDeleteByPidRequest): uid, pid
    """
    try:
        memory_service = get_memory_service()
        result = await memory_service.delete_by_profiling_id(
            request.uid,
            request.pid,
        )
        return UserProfilingDirectDeleteByPidResponse(
            status="success",
            uid=request.uid,
            pid=request.pid,
            data=result,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in direct_delete_by_pid: {e}")
        raise MemoryServiceError(
            f"Failed to direct delete by pid: {str(e)}",
            "DIRECT_DELETE_BY_PID_ERROR",
        ) from e


@router.post("/user_profiling/direct_update_profile")
async def direct_update_profile(
    request: UserProfilingDirectUpdateProfileRequest,
) -> UserProfilingDirectUpdateProfileResponse:
    """
    Direct update profile by pid

    Args:
        request (UserProfilingDirectUpdateProfileRequest): uid, pid,
            content_before, content_after
    """
    logger.info(f"direct_update_profile request received: {request}")
    try:
        memory_service = get_memory_service()
        result = await memory_service.direct_update_profile(
            request.uid,
            request.pid,
            request.content_before,
            request.content_after,
        )
        return UserProfilingDirectUpdateProfileResponse(
            status="success",
            uid=request.uid,
            pid=request.pid,
            data=result,
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in direct_update_by_pid: {e}")
        raise MemoryServiceError(
            f"Failed to direct update by pid: {str(e)}",
            "DIRECT_UPDATE_BY_PID_ERROR",
        ) from e


@router.post("/user_profiling/direct_confirm_profile")
async def direct_confirm_profile(
    request: UserProfilingDirectConfirmProfileRequest,
) -> UserProfilingDirectConfirmProfileResponse:
    """
    Direct confirm profile by pid

    Args:
        request (UserProfilingDirectConfirmProfileRequest): uid, pid
    """
    logger.info(f"direct_confirm_profile request received: {request}")
    try:
        memory_service = get_memory_service()
        result = await memory_service.direct_confirm_profile(
            request.uid,
            request.pid,
        )
        return UserProfilingDirectConfirmProfileResponse(
            status=result["status"],
            data=UserProfilingShowAllUserProfilesData(**result["data"]),
        )
    except MemoryServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in direct_confirm_profile: {e}")
        raise MemoryServiceError(
            f"Failed to direct confirm profile: {str(e)}",
            "DIRECT_CONFIRM_PROFILE_ERROR",
        ) from e
