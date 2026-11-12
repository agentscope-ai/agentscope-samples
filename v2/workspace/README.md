# AgentScope 2.0 Workspace Backends

This example demonstrates how to create a workspace-backed agent and switch
between the supported workspace backends:

| Backend         | Class                    | Requirements                       |
| --------------- | ------------------------ | ---------------------------------- |
| Local           | `LocalWorkspace`         | None (runs out of the box)         |
| Docker          | `DockerWorkspace`        | A running Docker daemon            |
| OpenSandbox     | `OpenSandboxWorkspace`   | An OpenSandbox account / API key   |

## 🌳 Sample Structure

```
.
├── README.md                 # Documentation
├── main.py                   # Entry point
└── workspace/                # Local backend working directory (created on demand)
```

## 📖 Overview

In AgentScope 2.0, a *workspace* provides an agent with:

* **Filesystem tools** (`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, ...)
  bound to a backend, and
* **Skills** and **MCP tools** seeded from the workspace.

The three built-in backends share one interface, so switching between them is
a one-line change. The local backend is the easiest way to get started, while
the Docker and OpenSandbox backends provide isolation and reproducibility.

## 🚀 Getting Started

### Prerequisites

* Python 3.10 or higher
* `agentscope` 2.0 installed (`pip install agentscope`)
* For the `docker` backend: a running Docker daemon
* For the `opensandbox` backend: an OpenSandbox account (set the SDK
  environment variables, e.g. `OPENSANDBOX_API_KEY`)

### Usage

```bash
# Local backend (no extra dependency)
python main.py --backend local

# Docker backend
python main.py --backend docker

# OpenSandbox backend
python main.py --backend opensandbox
```

## 🛠️ Features

* Backend-agnostic agent wiring via the shared workspace interface
* One-line backend switch between local / Docker / OpenSandbox
* Demonstrates `list_tools`, `get_instructions`, and the async context-manager lifecycle
