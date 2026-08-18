# Xquik MCP Discovery

This sample shows how to connect AgentScope's MCP client to Xquik's remote MCP server and inspect X workflow endpoints with the read-only `explore` tool.

## Sample Structure

```
.
├── __init__.py               # Enables package-based test discovery
├── README.md                 # Documentation
├── main.py                   # Entry point
├── test_main.py              # Offline configuration and query tests
└── requirements.txt          # Dependencies
```

## Overview

The sample demonstrates a minimal AgentScope MCP integration for a hosted, authenticated MCP server:

- Connects to `https://xquik.com/mcp` with an `Authorization: Bearer <token>` header.
- Enables only the read-only `explore` MCP tool.
- Searches the Xquik API catalogue for methods, paths, categories, or summaries that match a query.
- Prints the matching endpoint method, path, category, summary, and free/paid status.

No write or publish operations are executed. The sample does not call Xquik's live `xquik` execution tool.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An Xquik API key

### Installation

```bash
pip install -r requirements.txt
```

### Setup

```bash
export XQUIK_API_KEY="your-api-key"
```

The sample fixes the remote URL to `https://xquik.com/mcp` so the API key is never sent to a configurable origin.

### Usage

Search for endpoints related to trends:

```bash
python main.py trends
```

Search for endpoints related to monitoring:

```bash
python main.py monitors
```

If no query is provided, the sample searches for `radar`.

### Tests

Run the offline tests from the repository root:

```bash
python -m unittest -v functionality.xquik_mcp_discovery.test_main
```

## Features

- Uses AgentScope's `MCPClient` and `HttpMCPConfig`.
- Keeps the MCP connection stateless.
- Restricts the remote server to the read-only `explore` tool.
- Reads configuration only from environment variables.

Xquik is an independent third-party service. It is not affiliated with X Corp. "Twitter" and "X" are trademarks of X Corp.
