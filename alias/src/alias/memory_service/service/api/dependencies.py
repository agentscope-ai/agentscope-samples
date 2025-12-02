# -*- coding: utf-8 -*-
"""
Dependencies and service initialization for user profiling service
"""

from alias.memory_service.service.core.exceptions import (
    MissingRequiredFieldError,
    EmptyStringFieldError,
    ServiceUnavailableError,
)
from alias.memory_service.profiling_utils.logging_utils import setup_logging
from alias.memory_service.tool_memory import ToolMemory

logger = setup_logging()

# Check if memory service is available
try:
    from alias.memory_service.user_profiling_memory import (
        AsyncUserProfilingMemory,
        create_memory_config_with_collection,
    )

    MEM0_AVAILABLE = True
except ImportError:
    logger.warning(
        "AsyncUserProfilingMemory not available. "
        "Please check if user_profiling_memory is existing",
    )
    MEM0_AVAILABLE = False

# Check if memory utils are available
try:
    import importlib.util

    spec = importlib.util.find_spec("alias.memory_service.profiling_utils")
    MEMORY_UTILS_AVAILABLE = spec is not None
except ImportError:
    logger.warning("Memory utils not available")
    MEMORY_UTILS_AVAILABLE = False

# Global memory service instances
memory_service_user_profiling = None
memory_service_tool_memory = None
user_profiling_config = None
candidate_pool_config = None


def get_memory_service(memory_type: str = "user_profiling"):
    """
    Get or initialize memory service instance

    Args:
        memory_type: Type of memory service ("user_profiling" or "tool_memory")

    Returns:
        Memory service instance

    Raises:
        ServiceUnavailableError: If memory service is not available
    """
    global memory_service_user_profiling
    global memory_service_tool_memory
    global user_profiling_config
    global candidate_pool_config

    if not MEM0_AVAILABLE:
        raise ServiceUnavailableError("Memory service (mem0ai)")

    if memory_type == "user_profiling":
        if memory_service_user_profiling is None:
            if user_profiling_config is None:
                user_profiling_config = create_memory_config_with_collection(
                    "user_profiling_pool",
                    persist_history=True,
                )
            if candidate_pool_config is None:
                candidate_pool_config = create_memory_config_with_collection(
                    "candidate_pool",
                    persist_history=True,
                )
            memory_service_user_profiling = AsyncUserProfilingMemory(
                user_profiling_config,
                candidate_pool_config,
            )
        return memory_service_user_profiling
    elif memory_type == "tool_memory":
        if memory_service_tool_memory is None:
            memory_service_tool_memory = ToolMemory()
        return memory_service_tool_memory
    else:
        raise ServiceUnavailableError(
            f"Memory service for {memory_type} not available",
        )


def validate_request_data(
    request_data: dict,
    required_fields: list,
    none_empty_string_fields: list | None = None,
) -> None:
    """
    Validate request data for required fields

    Args:
        request_data: Request data dictionary
        required_fields: List of required field names
        none_empty_string_fields: List of fields that should not be empty
            strings

    Raises:
        MissingRequiredFieldError: If a required field is missing
        EmptyStringFieldError: If a field is an empty string
    """
    if none_empty_string_fields is None:
        none_empty_string_fields = []
    for field in required_fields:
        if field not in request_data or request_data[field] is None:
            raise MissingRequiredFieldError(field)
    for field in none_empty_string_fields:
        if field in request_data and request_data[field] == "":
            raise EmptyStringFieldError(field)
