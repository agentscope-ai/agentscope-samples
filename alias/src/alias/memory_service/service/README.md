# User Profiling Service

A FastAPI-based service for user profiling functionality with memory management.

## Project Structure

```
service/
├── app/                          # FastAPI application layer
│   ├── __init__.py
│   ├── main.py                   # FastAPI app creation
│   ├── server.py                 # Server configuration
│   └── handlers.py               # Exception handlers
├── api/                          # API layer
│   ├── __init__.py
│   ├── dependencies.py           # FastAPI dependencies
│   └── routers/
│       ├── __init__.py
│       ├── tasks.py              # Task management endpoints
│       └── user_profiling.py     # User profiling endpoints
├── core/                         # Core business logic
│   ├── __init__.py
│   ├── service.py                # Main service class
│   ├── task_manager.py           # Task management
│   └── exceptions.py             # Custom exceptions
├── config/                       # Configuration management
│   ├── __init__.py
│   ├── settings.py               # Main configuration
│   └── redis_config.py           # Redis-specific config
├── main.py                       # Main entry point
└── pyproject.toml
```

## Architecture

### App Layer (`app/`)
- **Purpose**: Pure FastAPI application setup and configuration
- **Files**:
  - `main.py`: FastAPI app creation and configuration
  - `server.py`: Server setup, middleware, and router inclusion
  - `handlers.py`: Exception handlers for the application

### API Layer (`api/`)
- **Purpose**: API endpoints, dependencies, and request/response handling
- **Files**:
  - `dependencies.py`: FastAPI dependencies and service initialization
  - `routers/`: API endpoint definitions
    - `user_profiling.py`: User profiling related endpoints
    - `tasks.py`: Task management endpoints

### Core Layer (`core/`)
- **Purpose**: Business logic, services, and domain models
- **Files**:
  - `service.py`: Main service class for user profiling operations
  - `task_manager.py`: Redis-based task management
  - `exceptions.py`: Custom exception classes

### Config Layer (`config/`)
- **Purpose**: All configuration-related code
- **Files**:
  - `settings.py`: Main configuration settings
  - `redis_config.py`: Redis-specific configuration

## Benefits of This Structure

1. **Separation of Concerns**: Clear separation between web framework code and business logic
2. **Testability**: Core business logic can be tested independently of FastAPI
3. **Maintainability**: Easier to locate and modify specific functionality
4. **Scalability**: Clean architecture allows for easy extension
5. **Clean Architecture**: Follows established patterns for enterprise applications

## Usage

### Running the Service

```bash
# Using uvicorn directly
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000

# Using environment variable for port
export USER_PROFILING_SERVICE_PORT=8000
uvicorn main:app --workers 4 --host 0.0.0.0 --port $USER_PROFILING_SERVICE_PORT
```

### API Endpoints

- **Health Check**: `GET /health`
- **User Profiling**: `/alias_memory_service/user_profiling/*`
- **Task Management**: `/alias_memory_service/user_profiling/task_status/*`

## Configuration

The service uses environment variables for configuration. See `config/settings.py` and `config/redis_config.py` for available options.

## Dependencies

- FastAPI
- Redis (for task management)
- Mem0 (for memory operations)
- Pydantic (for data validation)
