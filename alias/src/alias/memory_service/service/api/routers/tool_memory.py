# -*- coding: utf-8 -*-
"""
User profiling API endpoints
"""
from fastapi import APIRouter

from alias.memory_service.models.user_profiling import (
    UserProfilingRetrieveRequest,
)
from alias.memory_service.profiling_utils.logging_utils import setup_logging
from alias.memory_service.service.api.dependencies import (
    get_memory_service,
    validate_request_data,
)
from alias.memory_service.service.core.exceptions import (
    EmptyQueryError,
)
from alias.memory_service.service.core.task_manager import (
    UserProfilingTaskManager,
)

logger = setup_logging()
router = APIRouter(prefix="/alias_memory_service", tags=["tool_memory"])

# Task manager instance
task_manager = UserProfilingTaskManager()


@router.post("/tool_memory/retrieve")
async def retrieve_memory(request: dict):
    """
    Retrieve memory based on query
    examples:
    curl -X POST \\
      "http://localhost:8000/alias_memory_service/tool_memory/retrieve" \\
      -H "Content-Type: application/json" \\
      -d '{
        "uid": "user123",
        "query": "web_search,write_file"
      }'
    """
    logger.info(f"retrieve tool memory request received: {request}")
    validate_request_data(
        request,
        ["uid", "query"],
        none_empty_string_fields=["query"],
    )
    request_obj = UserProfilingRetrieveRequest(**request)

    if not request_obj.query.strip():
        raise EmptyQueryError()

    memory_service = get_memory_service(memory_type="tool_memory")
    result = await memory_service.retrieve(request_obj.uid, request_obj.query)
    return {"status": "success", "data": result}
