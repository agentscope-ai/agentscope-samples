# Memory Service

Alias Memory Service - A memory service for user profiling and tool memory management.

## Overview

This service provides memory management capabilities including user profiling and tool memory storage, built with FastAPI and supporting multiple storage backends (Redis, Qdrant).

## Quick Start

### Installation

```bash
pip install -e .
```

### Configuration

Before running the service, you need to create a `.env` file in the project root directory. You can use the example file as a reference:

```bash
cp docker/.env.example .env
```

Then edit `.env` and configure the required environment variables (API keys, database connections, etc.).

### Running the Service

```bash
cd service
uvicorn main:app --host 0.0.0.0 --port 6380
```

## API Documentation

For detailed API documentation, please refer to the [API documentation](./docs/) folder:
- [API Documentation (English)](./docs/API_DOCUMENTATION_EN.md)
- [API Documentation (Chinese)](./docs/API_DOCUMENTATION.md)

## Docker Deployment

For Docker deployment instructions, please refer to the [Docker README](./docker/README.md).

## User Profiling Memory

The user profiling system is built on **mem0** and collects and processes user behavior data from the frontend to build comprehensive user profiles. The memory is generated through various user actions such as session collection, tool usage, feedback (like/dislike), edits, and chat interactions.

The system consists of three memory pools that work together to build and maintain user profiles:

### Memory Pools

1. **Candidate Pool**: Temporarily stores user preference memories as candidates. Each candidate is scored based on:
   - **Visit count**: How frequently the memory is accessed
   - **Time decay**: Recency of access (more recent = higher score)
   - Scores are computed using a weighted formula: `0.7 * time_score + 0.3 * visit_score`

2. **User Profiling Pool**: Stores confirmed user profile memories. These are stable, validated user preferences and characteristics extracted from user interactions.

3. **User Info Pool**: Stores basic user information facts extracted from conversations, such as personal details, preferences, and background information.

### Evolving Mechanism: Candidate to Formal Profiling

New user interactions are stored in the candidate pool and scored based on visit count and recency. When a candidate's score exceeds a dynamic threshold (calculated as `0.95 * (1 - 1/n)` where n is the number of candidates), it is automatically promoted to the user profiling pool. This ensures only high-quality, frequently-accessed preferences are promoted.

## Tool Memory

Tool Memory is built on **ReMe** and manages tool execution history and provides usage guidelines based on historical performance:

- **Storage**: Uses ReMe backend to store tool call results, including tool name, input parameters, output results, execution status, and time cost.

- **Automatic Summarization**: Implements threshold-based summarization:
  - **Time threshold**: Triggers summary when time since last summary exceeds threshold (default: 300s)
  - **Count threshold**: Triggers summary when unsummarized tool calls exceed threshold (default: 5 calls)

- **Retrieval**: Provides tool usage guidelines and best practices by querying historical tool execution patterns, helping agents make better tool selection decisions.

## Project Structure

- `basememory.py` - Base memory interface
- `memory_base/` - Core memory implementations
- `models/` - Data models
- `profiling_utils/` - Utility functions
- `service/` - FastAPI service application
- `docs/` - API documentation
- `docker/` - Docker deployment files

## References

- [mem0](https://github.com/mem0ai/mem0) - Universal memory layer for AI Agents
- [ReMe](https://github.com/agentscope-ai/ReMe) - Tool memory management system

