# Browser Use Agent Pro

A powerful, standalone browser automation agent built on top of [AgentScope](https://github.com/agentscope-ai/agentscope) and [Playwright MCP](https://github.com/microsoft/playwright-mcp). This agent provides intelligent web automation capabilities through natural language instructions.

Browser Use Agent Pro excels at automating a wide range of web-based tasks, including web research, form automation, e-commerce operations, content management, testing, and workflow automation.

## ✨ Key Features

- **Multimodal Understanding**
  - Image understanding: Analyze and interact with visual elements on web pages
  - Video understanding: Extract frames, transcribe audio, and analyze video content
  - Form filling: Automatically fill web forms based on natural language instructions
  - File Download: Locate and trigger file downloads from web pages

- **Task Decomposition and Management**
  - Automatic task decomposition: Break down complex tasks into manageable subtasks
  - Subtask tracking: Monitor and manage progress through multiple subtasks
  - Dynamic subtask revision: Adapt and refine subtasks based on execution results
  - Task completion validation: Verify when subtasks and overall tasks are completed

- **Advanced Reasoning**
  - Pure reasoning: Plan actions without page observation
  - Observation-based reasoning: Analyze page content before making decisions
  - Chunked observation: Process large page snapshots in manageable chunks

- **Memory Management**
  - Automatic memory summarization: Condense conversation history when it exceeds limits
  - Tool output filtering: Clean and filter verbose tool execution results


## 📋 Requirements

- Python 3.10+
- Node.js and npx (for playwright-mcp)
- DASHSCOPE_API_KEY environment variable

The playwright-mcp server will automatically handle browser installation when first run via `npx @playwright/mcp@latest`. No manual browser installation is required.

## 💻 Installation

1. Install dependencies:
```bash
# From the project root directory
pip install -r requirements.txt
```

2. Ensure Node.js and npx are installed (required for playwright-mcp):
```bash
# Check if npx is available
npx --version
```

3. Set up environment variables:
```bash
export DASHSCOPE_API_KEY="your-api-key"
export MODEL="qwen3-max"  # or "qwen-vl-max" for vision model
```

## 🚀 Basic Usage

Run the Browser Use Agent Pro with a task, optionally configure the start URL:

```bash
# From the project root directory
python main.py "Find the latest stock price of Alibaba Group" "https://www.google.com"
```

## ℹ️ Note

This is a standalone version extracted from the [Alias-Agent](https://github.com/agentscope-ai/agentscope-samples/tree/main/alias) project. It now uses standard agentscope components (ReActAgent, Toolkit) with local Playwright MCP clients.
