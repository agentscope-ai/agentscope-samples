# User Profiling Service API Documentation

## Overview

User Profiling Service is a standalone service for user profiling functionality, providing user memory management, behavior recording, and task management capabilities. The service is built on FastAPI and supports asynchronous operations and background task processing.

**Service Information:**
- Service Name: User Profiling Service
- Version: 0.1.0
- Base URL: `http://localhost:8000`

## Authentication and Error Handling

### Error Response Format

All error responses follow a unified format:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Error description",
  "details": {
    "errors": [
      {
        "field": "field_path",
        "message": "field_error_message",
        "type": "error_type"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

### Common Error Codes

| Error Code | Status Code | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400/422 | Request data validation failed |
| `MISSING_REQUIRED_FIELD` | 400 | Missing required field |
| `EMPTY_STRING_FIELD` | 400 | Field is empty string |
| `USER_NOT_FOUND` | 404 | User not found |
| `TASK_NOT_FOUND` | 404 | Task not found |
| `MEMORY_SERVICE_ERROR` | 503 | Memory service error |
| `SERVICE_UNAVAILABLE` | 503 | Service unavailable |
| `INTERNAL_SERVER_ERROR` | 500 | Internal server error |

## API Endpoints

### 1. Health Check

#### GET /health

Check service health status.

**Response Example:**
```json
{
  "status": "healthy",
  "service": "user_profiling_service",
  "mem0_available": true,
  "memory_utils_available": true
}
```

### 2. Memory Management

#### POST /alias_memory_service/user_profiling/add

Send content to the memory service, which will be processed and stored. Submits a background task and returns submit_id.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "content": [
    {
      "role": "user",
      "content": "User message content"
    },
    {
      "role": "assistant",
      "content": "Assistant response content"
    }
  ]
}
```

**Response Example:**
```json
{
  "status": "submit success",
  "submit_id": "uuid-string"
}
```

#### POST /alias_memory_service/user_profiling/clear

Clear all memory for a specific user.

**Request Parameters:**
```json
{
  "uid": "user_id"
}
```

**Response Example:**
```json
{
  "status": "submit success",
  "submit_id": "uuid-string"
}
```

#### POST /alias_memory_service/user_profiling/retrieve

Retrieve relevant information from the memory service.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "query": "query content"
}
```

**Response Example:**
```json
{
  "status": "success",
  "uid": "user_id",
  "query": "query content",
  "data": {
    "candidates": {
      "results": [
        {
          "id": "b904ba2c-3f87-4050-981e-b5fe5afe1ad0",
          "memory": "Likes watching sci-fi movies",
          "hash": "904b4e33b7721425dee845bff17b08fa",
          "metadata": null,
          "score": 0.5977808,
          "created_at": "2025-07-20T23:11:00.221851-07:00",
          "updated_at": null,
          "user_id": "test_user_basic"
        }
      ],
      "relations": null
    },
    "profiling": {},
    "user_info": {}
  }
}
```

**Response Field Descriptions:**
- `candidates`: Search results from memory retrieval
  - `results`: List of memory entries matching the query
    - `id`: Unique identifier for the memory entry
    - `memory`: Memory content text
    - `hash`: Hash value of the memory content
    - `metadata`: Metadata information (can be null)
    - `score`: Relevance score (0-1, higher is more relevant)
    - `created_at`: Creation timestamp
    - `updated_at`: Update timestamp (can be null)
    - `user_id`: User ID
  - `relations`: Relation information (can be null)
- `profiling`: Profiling data
- `user_info`: User information

#### POST /alias_memory_service/user_profiling/show_all

Display all memory for a user.

**Request Parameters:**
```json
{
  "uid": "user_id"
}
```

**Response Example:**
```json
{
  "status": "success",
  "uid": "user_id",
  "data": {
    "results": [
      {
        "id": "b904ba2c-3f87-4050-981e-b5fe5afe1ad0",
        "memory": "Likes watching sci-fi movies",
        "hash": "904b4e33b7721425dee845bff17b08fa",
        "metadata": null,
        "score": 0.5977808,
        "created_at": "2025-07-20T23:11:00.221851-07:00",
        "updated_at": null,
        "user_id": "test_user_basic"
      }
    ],
    "relations": null
  }
}
```

#### POST /alias_memory_service/user_profiling/show_all_user_profiles

Display all user profiles for a user.

**Request Parameters:**
```json
{
  "uid": "user_id"
}
```

**Response Example:**
```json
{
  "status": "success",
  "data": [
    {
      "pid": "profile_id",
      "uid": "user_id",
      "content": "Profile content text",
      "metadata": {
        "session_id": "session_id",
        "is_confirmed": 0
      }
    }
  ]
}
```

**Response Field Descriptions:**
- `pid`: Profile ID
- `uid`: User ID
- `content`: Profile content
- `metadata`: Profile metadata
  - `session_id`: Session ID (can be null)
  - `is_confirmed`: Confirmation status (0: not confirmed, 1: confirmed)

### 3. Tool Memory

#### POST /alias_memory_service/tool_memory/retrieve

Retrieve tool memory based on query. This endpoint is used to retrieve memories related to tool usage.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "query": "web_search,write_file"
}
```

**Response Example:**
```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "id": "memory_id",
        "memory": "Tool usage information",
        "score": 0.8
      }
    ],
    "relations": null
  }
}
```

### 4. Action Recording

#### POST /alias_memory_service/record_action

Record user actions, supporting multiple action types. This endpoint submits a background task and returns submit_id.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "session_id": "session_id",
  "action_type": "LIKE",
  "message_id": "message_id",
  "reference_time": "2024-01-01T12:00:00",
  "data": {}
}
```

**Supported Action Types:**

**Feedback Actions:**
- `LIKE` - Like
- `DISLIKE` - Dislike
- `CANCEL_LIKE` - Cancel like
- `CANCEL_DISLIKE` - Cancel dislike

**Collection Actions:**
- `COLLECT_TOOL` - Collect tool
- `UNCOLLECT_TOOL` - Uncollect tool
- `COLLECT_SESSION` - Collect session
- `UNCOLLECT_SESSION` - Uncollect session

**Chat Actions:**
- `START_CHAT` - Start chat
- `FOLLOWUP_CHAT` - Follow-up chat
- `BREAK_CHAT` - Break chat

**Edit Actions:**
- `EDIT_ROADMAP` - Edit roadmap
- `EDIT_FILE` - Edit file
- `EXECUTE_SHELL_COMMAND` - Execute shell command
- `BROWSER_OPERATION` - Browser operation

**Task Actions:**
- `TASK_STOP` - Task stop (stores in tool_memory)

**Note:** The `action_type` field can be either an enum value (string) or you can use the legacy `action` field for backward compatibility. The `data` field can contain action-specific data structures:
- For feedback/collection actions: `ChangeRecord` with `previous` and `current` fields
- For chat actions: `QueryRecord` with `query` field
- For operation actions: `OperationRecord` with `operation_type` and `operation_data` fields
- For roadmap editing: `Roadmap` with `content` and `metadata` fields

**Response Example:**
```json
{
  "status": "submit success",
  "submit_id": "uuid-string"
}
```

### 5. Direct Profile Operations

#### POST /alias_memory_service/user_profiling/direct_add_profile

Directly add user profile.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "content": "Profile content text"
}
```

**Response Example:**
```json
{
  "status": "success",
  "uid": "user_id",
  "pid": "profile_id",
  "data": {
    "results": [
      {
        "id": "profile_id",
        "memory": "Profile content text",
        "user_id": "user_id"
      }
    ]
  }
}
```

#### POST /alias_memory_service/user_profiling/direct_delete_by_profiling_id

Delete profile by Profiling ID.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "pid": "Profiling ID"
}
```

**Response Example:**
```json
{
  "status": "success",
  "uid": "user_id",
  "pid": "Profiling ID",
  "data": {
    "deleted": true
  }
}
```

#### POST /alias_memory_service/user_profiling/direct_update_profile

Update profile by Profiling ID.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "pid": "Profiling ID",
  "content_before": "original profiling content",
  "content_after": "updated profiling content"
}
```

**Response Example:**
```json
{
  "status": "success",
  "uid": "user_id",
  "pid": "Profiling ID",
  "data": {
    "updated": true
  }
}
```

#### POST /alias_memory_service/user_profiling/direct_confirm_profile

Confirm profile by Profiling ID.

**Request Parameters:**
```json
{
  "uid": "user_id",
  "pid": "Profiling ID"
}
```

**Response Example:**
```json
{
  "status": "success",
  "data": {
    "pid": "profile_id",
    "uid": "user_id",
    "content": "Profile content text",
    "metadata": {
      "session_id": "session_id",
      "is_confirmed": 1
    }
  }
}
```

### 6. Task Management

#### GET /alias_memory_service/task_status/{submit_id}

Get status of a specific task.

**Path Parameters:**
- `submit_id`: Task submission ID

**Response Example:**
```json
{
  "submit_id": "uuid-string",
  "status": "completed",
  "data": {
    "status": "completed",
    "result": {},
    "created_at": "2024-01-01T12:00:00",
    "completed_at": "2024-01-01T12:05:00"
  }
}
```

#### GET /alias_memory_service/all_tasks

Get all tracked tasks (for debugging/monitoring).

**Response Example:**
```json
{
  "status": "success",
  "data": {
    "task-id-1": {
      "status": "completed",
      "result": {},
      "created_at": "2024-01-01T12:00:00"
    },
    "task-id-2": {
      "status": "running",
      "created_at": "2024-01-01T12:10:00"
    }
  }
}
```

#### GET /alias_memory_service/tasks_by_date/{date_str}

Get all tasks for a specific date.

**Path Parameters:**
- `date_str`: Date string in YYYY-MM-DD format

**Response Example:**
```json
{
  "status": "success",
  "date": "2024-01-01",
  "data": [
    {
      "submit_id": "uuid-string",
      "status": "completed",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

#### GET /alias_memory_service/tasks_by_date_range

Get all tasks within a date range.

**Query Parameters:**
- `start_date`: Start date in YYYY-MM-DD format (required)
- `end_date`: End date in YYYY-MM-DD format (required)

**Response Example:**
```json
{
  "status": "success",
  "start_date": "2024-01-01",
  "end_date": "2024-01-07",
  "data": [
    {
      "submit_id": "uuid-string",
      "status": "completed",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

#### GET /alias_memory_service/storage_stats

Get storage statistics for task files.

**Response Example:**
```json
{
  "status": "success",
  "data": {
    "total_tasks": 100,
    "completed_tasks": 95,
    "failed_tasks": 3,
    "running_tasks": 2,
    "storage_size_mb": 15.5
  }
}
```

## Task Status

Possible task statuses include:

- `running` - Task is running
- `completed` - Task completed
- `failed` - Task failed

## Usage Examples

### Python Client Example

```python
import asyncio
import aiohttp
import json

async def add_memory(uid: str, content: list):
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8000/alias_memory_service/user_profiling/add"
        data = {
            "uid": uid,
            "content": content
        }

        async with session.post(url, json=data) as response:
            result = await response.json()
            return result

async def retrieve_memory(uid: str, query: str):
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8000/alias_memory_service/user_profiling/retrieve"
        data = {
            "uid": uid,
            "query": query
        }

        async with session.post(url, json=data) as response:
            result = await response.json()
            return result

async def check_task_status(submit_id: str):
    async with aiohttp.ClientSession() as session:
        url = f"http://localhost:8000/alias_memory_service/task_status/{submit_id}"

        async with session.get(url) as response:
            result = await response.json()
            return result

async def record_action(uid: str, session_id: str, action_type: str):
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8000/alias_memory_service/record_action"
        data = {
            "uid": uid,
            "session_id": session_id,
            "action_type": action_type
        }

        async with session.post(url, json=data) as response:
            result = await response.json()
            return result

# Usage example
async def main():
    # Add memory
    content = [
        {"role": "user", "content": "I like sci-fi movies"},
        {"role": "assistant", "content": "Sci-fi movies are interesting! Which one do you like best?"}
    ]

    result = await add_memory("user123", content)
    submit_id = result["submit_id"]

    # Check task status
    while True:
        status = await check_task_status(submit_id)
        if status["status"] in ["completed", "failed"]:
            print(f"Task completed, status: {status['status']}")
            break
        await asyncio.sleep(5)

    # Retrieve memory
    retrieve_result = await retrieve_memory("user123", "What type of movies do I like")
    print(f"Retrieved memories: {retrieve_result}")

# Run example
asyncio.run(main())
```

### cURL Examples

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Add memory
curl -X POST "http://localhost:8000/alias_memory_service/user_profiling/add" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123",
    "content": [
      {"role": "user", "content": "I like sci-fi movies"},
      {"role": "assistant", "content": "Sci-fi movies are interesting!"}
    ]
  }'

# Retrieve memory
curl -X POST "http://localhost:8000/alias_memory_service/user_profiling/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123",
    "query": "What type of movies do I like"
  }'

# Show all memory
curl -X POST "http://localhost:8000/alias_memory_service/user_profiling/show_all" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123"
  }'

# Show all user profiles
curl -X POST "http://localhost:8000/alias_memory_service/user_profiling/show_all_user_profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123"
  }'

# Record action
curl -X POST "http://localhost:8000/alias_memory_service/record_action" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123",
    "session_id": "session_id",
    "action_type": "LIKE",
    "message_id": "message_id"
  }'

# Retrieve tool memory
curl -X POST "http://localhost:8000/alias_memory_service/tool_memory/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user123",
    "query": "web_search,write_file"
  }'

# Check task status
curl -X GET "http://localhost:8000/alias_memory_service/task_status/{submit_id}"

# Get all tasks
curl -X GET "http://localhost:8000/alias_memory_service/all_tasks"

# Get tasks by date
curl -X GET "http://localhost:8000/alias_memory_service/tasks_by_date/2024-01-01"

# Get tasks by date range
curl -X GET "http://localhost:8000/alias_memory_service/tasks_by_date_range?start_date=2024-01-01&end_date=2024-01-07"

# Get storage stats
curl -X GET "http://localhost:8000/alias_memory_service/storage_stats"
```

## Important Notes

1. **Asynchronous Operations**: Most memory operations (add, clear, record_action) are asynchronous and return a `submit_id`, which should be used to query completion status through the task status interface.

2. **Error Handling**: All interfaces have comprehensive error handling mechanisms and return detailed error information.

3. **Data Validation**: All requests undergo data validation to ensure required fields exist and are in the correct format.

4. **Session Management**: Action recording functionality requires valid session IDs to retrieve session content.

5. **Memory Service Dependency**: The service depends on the mem0ai memory service, ensure this service is available.

6. **Logging**: All operations are logged to log files for debugging and monitoring purposes.

7. **Tool Memory**: The `TASK_STOP` action type stores data in tool_memory instead of user_profiling memory.

8. **Profile Confirmation**: Use `direct_confirm_profile` to mark a profile as confirmed (is_confirmed=1).

## Deployment Instructions

The service runs on `0.0.0.0:8000` by default and can be started with:

```bash
python main.py
```

Or using uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Or set the port via environment variable:

```bash
export USER_PROFILING_SERVICE_PORT=8000
uvicorn main:app --host 0.0.0.0 --port $USER_PROFILING_SERVICE_PORT
```

The service supports CORS and can be accessed from any origin.
