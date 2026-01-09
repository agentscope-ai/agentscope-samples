<p align="center">
  <img
    src="assets/alias.png"
    alt="Alias-Agent Logo"
    width="500"
    height="auto"
  />
</p>

<h2 align="center">Alias-Agent: Start It Now, Extend It Your Way, Deploy All with Ease</h2>

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Docs](https://img.shields.io/badge/built--on-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/built--on-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

<p align="center">
<u>
Unlock your unique experience at <a href="https://alias.agentscope.io/"> alias.agentscope.io</a>
</u>
</p>

</div>

[[中文README]](README_ZH.md)

*Alias-Agent* (short for *Alias*) is an LLM-empowered agent built on [AgentScope](https://github.com/agentscope-ai/agentscope) and [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/), designed to serve as a general-purpose intelligent assistant for responding to user queries. Alias excels at decomposing complicated problems, constructing roadmaps, and applying appropriate strategies to tackle diverse real-world tasks.

Alias employs a multi-mode operational mechanism for flexible task execution, including `General`, `Browser Use`, `Deep Research`, `Financial Analysis`, and `Data Science`. When switching between different operational modes, Alias is equipped with tailored instructions, specialized tool sets, and the capability to orchestrate various expert agents. This allows Alias to better adapt to the specific requirements of diverse downstream tasks. For example, when handling financial analysis, Alias employs traceable reasoning chains and generates explainable results to increase user trust in its decision-making, along with optimized report visualizations; When resolving data science tasks, Alias can access user-associated databases and is designed to facilitate efficient data analysis, processing, and prediction.

We aim for Alias to serve as an out-of-the-box solution that users can readily deploy for various tasks, supported by a comprehensive pipeline for agent development, testing, and deployment based on the AgentScope ecosystem. Beyond being a ready-to-use agent, we also envision Alias as a foundational template that can be adapted for diverse scenarios. Developers are encouraged to extend and customize Alias at the tool, prompt, and agent levels to meet specific requirements.

We welcome more developers to join the community and contribute to ongoing innovation.

## 📢 News
- **[2025-12]** Five operational modes available: General, Browser Use, Deep Research, Financial Analysis, and Data Science modes.

- **[2025-12]** Memory system upgrades: Tool Memory service for persistent tool invocation traces and User Profiling service for personalized user experiences.

- **[2025-12]** Frontend UI is designed with [Spark Design](https://sparkdesign.agentscope.io/) implementation, featuring interrupt controls and artifact editing capabilities.

- **[2025-12]** Backend refactoring on [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/): lightweight single-node deployment, simplified user management, and mode-specific bootstrapping.


## ✨ Features

### 🤖 Various Operational Modes for Diverse Scenarios

It provides five operational modes for diverse real-world tasks:

- **General**: Meta Planner capable of auto-switching among easy-task, planning-execution, browser use, deep research, and data science modes based on task context.
- **Browser Use**: Enhanced browser-use agent with multimodal capabilities.
- **Deep Research**: Deep Research agent with tree-structure question/hypothesis exploration and user-centric features.
- **Financial Analysis**: Hypothesis-driven financial analysis agent.
- **Data Science**: Specialized agent for data science workflows, such as machine learning, numerical computation, and exploratory data analysis.

#### General Mode

The General mode features the Meta Planner, which orchestrates task execution with automatic mode switching and comprehensive interrupt support. The Meta Planner intelligently routes tasks to appropriate specialized agents based on context, while maintaining robust state preservation throughout the execution lifecycle. This enables seamless transitions between different operational modes (such as deep research and data science) and ensures continuity even when tasks are interrupted or redirected.

The general mode also provides an out-of-the-box AgentScope-specific QA Agent ([more details](docs/qa_agent.md)), pre-configured with high-frequency AgentScope-related Q&A pairs. By integrating RAG and GitHub MCP tools, the QA agent can dynamically retrieve the latest source code structure, official tutorial, and community discussions, and combine them with relevant information flexibly matched from a private knowledge base to deliver accurate answers.

#### Browser Use Mode
<p align="center">
  <img
    src="assets/browser_agent.png"
    alt="Browser Use Mode"
    width="600"
    height="auto"
  />
</p>

The Browser Use mode extends the browser-use agent with comprehensive multimodal capabilities, enabling fine-grained understanding of visual content and intelligent interaction with web elements. The agent features advanced image understanding that can extract semantic meaning from charts, graphs, and visual content, including axis labels, trends, and outliers. Video comprehension capabilities allow the agent to extract and reason over video content, while automated table filling and intelligent file download tools streamline form interactions and document management.

To handle the dynamic nature of web browsing, the Browser Use mode implements sophisticated dynamic subtask management. The system automatically updates subtasks as web pages change, adapting to new content, pop-ups, or navigation events. This ensures the agent can maintain context and continue task execution even when the browsing environment evolves, making it particularly effective for complex multi-step web interactions that require sustained attention and adaptation.

#### Deep Research Mode
<p align="center">
  <img
    src="assets/deep_research.png"
    alt="Deep Research Mode"
    width="600"
    height="auto"
  />
</p>

The Deep Research mode introduces user-centric enhancements that transform research tasks into collaborative, transparent processes. For research-type questions, the agent employs a pre-search module that gathers professional, detailed information before generating follow-up questions, ensuring that inquiries are more valuable and well-informed. This approach significantly improves the quality of research interactions by grounding questions in comprehensive background knowledge.

This mode also features a tree-structure research process that is driven by diving deeper and deeper by information gathering. Users can also dynamically interrupt the deep research process and steer the research direction. The consolidated execution path provides a unified codebase with configurable prompts, SOPs, and toolkits, allowing the Deep Research agent to adapt to different domains while maintaining a consistent, extensible architecture.

 #### Financial Analysis Mode ([Detailed Docs](docs/financial_analysis.md))

<p align="center">
  <img
    src="docs/figures/finance_overview.png"
    alt="Financial Analysis Mode"
    width="600"
    height="auto"
  />
</p>

In financial analysis scenarios, complex reasoning and traceable logic chains are crucial for building user trust in model conclusions. To achieve *explainability*, *traceability*, and *intervenability*, Alias-Agent adopts a hypothesis-driven agent architecture that explicitly transforms task execution into a “propose hypothesis → collect evidence → verify hypothesis → update state” loop, as a variant of the general deep research process. This architecture enables analysis logic to be recorded, examined, and iterated upon, systematically addressing the financial domain's need for transparent evidence chains and clear, controllable logic.

The Financial Analysis mode supports tree-structured search, decomposing complex financial research questions into verifiable sub-hypotheses through deep hierarchical exploration. This mode integrates with financial MCP tools (API keys can be configured for easy use) and optimizes report visualization. In addition to generating comprehensive final reports, the system supports visualization of the entire tree search process and produces interactive HTML files optimized for presentation, making complex financial analyses more accessible and interpretable.


#### Data Science Mode ([Detailed Docs](docs/data_science.md))

<div align="center" style="margin: 20px 0;">
  <img src="docs/figures/alias-ds-overall.png" width="80%" style="max-width: 800px; height: auto;">
</div>


In Data Science mode, Alias-Agent serves as an autonomous, end-to-end assistant that transforms high-level analytical questions into executable data science workflows. It seamlessly handles the full pipeline from data acquisition and cleaning to modeling, visualization, and narrative reporting with minimal human intervention, enabling users to move efficiently from intent to insight in real-world scenarios.

At startup, the Data Science mode uses an intelligent router to assign the user's task to one of three core scenarios: Exploratory Data Analysis (EDA), Predictive Modeling, or Exact Data Computation. Each scenario is driven by a dedicated prompt template tailored to its analytical intent. Built on this foundation, it features a scalable file filtering pipeline to quickly locate relevant files in massive data lakes. It robustly parses irregular spreadsheets, including merged cells, multi-level headers, and embedded notes, into structured tables or semantic JSON. It also supports multimodal understanding, enabling summarization and natural-language question answering about visual content. For EDA tasks, it automatically generates interactive HTML reports that combine insights, visualizations, and executable code to ensure transparency and reproducibility.

### 🧠 Enhanced Memory System

- **Tool Memory (Long-term)**: Persistent storage for tool invocation traces via ReMe, enabling automated summarization and usage guidance.
- **User Profiling (Long-term)**: Captures and refines user behavior through dynamic candidate scoring and promotion to stable profiles via mem0, seamlessly integrated with frontend interactions.

### 🖥️ CLI & Full-Stack Deployment Available

#### CLI Deployment
- **Command-Line Interface**: Direct execution via `alias_agent run` command with mode selection and configuration options.

#### Full-Stack Deployment
- **Frontend**: [Spark Design](https://sparkdesign.agentscope.io/)-based React application with runtime interrupt controls, artifact inspectors, and editable outputs.
- **Backend**: Lightweight single-node deployment on [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/) with simplified user management and mode-specific bootstrapping.


## 🚀 Quickstart

### 💻 Installation

> Alias requires **Python 3.10** or higher.

First, install the package in development mode
```bash
# From the project root directory
pip install -e .
```

This installs the `alias_agent` command-line tool.

### 🐳 Sandbox Setup (Optional)

```bash
# If using colima
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

# Option 1: Pull from enterprise registry
export RUNTIME_SANDBOX_REGISTRY=agentscope-registry.ap-southeast-1.cr.aliyuncs.com
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-alias:latest

# Option 2: Pull from Docker Hub
docker pull agentscope/runtime-sandbox-alias:latest
```

More details can refer to [AgentScope Runtime documentation](https://runtime.agentscope.io/en/sandbox/sandbox.html).

### 🔑 API Keys Configuration

```bash
# Required: Model API key (default: DashScope)
export DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Required: Search API key (for Deep Research mode)
export TAVILY_API_KEY=your_tavily_api_key_here

# Optional: Finance MCP Tools API key (for Financial Analysis mode). Activate MCP tools at:
#  https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/Qieman
# https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/tendency-software
export DASHSCOPE_MCP_API_KEY=your_dashscope_api_key_here


# Optional: GitHub token (for QA Agent to access GitHub repositories)
# export GITHUB_TOKEN=your_github_token

# Optional: Using other models (e.g., OpenAI)
# First, add your model to MODEL_FORMATTER_MAPPING in alias/agent/run.py
# export MODEL=gpt-4
# export OPENAI_API_KEY=your_openai_api_key_here
```

### 📝 Basic Usage -- CLI Deployment

Execute an agent task with different modes:

```bash
# General mode
alias_agent run --mode general --task "Analyze Meta stock performance in Q1 2025"

# Browser Use mode
alias_agent run --mode browser --task "Search five latest research papers about browser-use agent"

# Deep Research mode
alias_agent run --mode dr --task "Research the impact of AI on healthcare"

# Financial Analysis mode
alias_agent run --mode finance --task "Analyze Tesla's Q4 2024 financial performance"

# Data Science mode
alias_agent run --mode ds \
  --task "Analyze the distribution of incidents across categories in 'incident_records.csv' to identify imbalances, inconsistencies, or anomalies, and determine their root cause." \
  --files ./docs/data/incident_records.csv
```

**Note**: Files uploaded with `--files` are automatically copied to `/workspace` in the sandbox. Generated files are available in `sessions_mount_dir` subdirectories.

#### Enable Long-Term Memory Service (General Mode Only)
To enable the long-term memory service in General mode, you need to:
1. **Start the Memory Service first** (see [Start the Memory Service Server](#start-the-memory-service-server) section below)
2. **Use the `--use_long_term_memory` flag** when running in General mode:
```bash
# General mode with long-term memory service enabled
alias_agent run --mode general --task "Analyze Meta stock performance in Q1 2025" --use_long_term_memory
```
**Important**:
- Long-term memory is only enabled when the `--use_long_term_memory` flag is explicitly provided (disabled by default)
- The long-term memory service is only available in **General mode** (meta-planner)
- The memory service must be running before starting the agent
- When enabled, the agent will retrieve user profiling information at session start to provide personalized experiences

### Basic Usage -- Full-Stack Deployment

To run Alias-Agent with the full-stack deployment (frontend + backend), follow these steps:

#### Prerequisites

1. **Install Frontend Dependencies**:
```bash
# From the project root directory
cd frontend
npm install
```

2. **Configure Environment Variables**:
```bash
# From the project root directory, copy the example environment file
cp .env.example .env

# Edit .env and configure the following key variables:
# - USER_PROFILING_BASE_URL: Memory Service URL (e.g., http://localhost:6380/alias_memory_service)
# - REDIS_HOST: Redis host (default: localhost)
# - REDIS_PORT: Redis port (default: 6379)
# - BACKEND_PORT: Backend server port (default: 8000)
# - FIRST_SUPERUSER_EMAIL: Initial admin email (default: alias@agentscope.com)
# - FIRST_SUPERUSER_USERNAME: Initial admin username (default: alias)
# - FIRST_SUPERUSER_PASSWORD: Initial admin password (default: alias)
```

3. **Start Redis** (required for caching and session management):
```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 --name alias-redis redis:7-alpine

# Or using local Redis installation
redis-server
```

#### Start the Sandbox Server (Optional but Recommended)

For full functionality including code execution and file operations, start the sandbox server in another terminal:

```bash
# From the project root directory
runtime-sandbox-server --extension src/alias/runtime/alias_sandbox/alias_sandbox.py
```

The sandbox server enables secure code execution in isolated containers, which is essential for Data Science mode and other features that require code execution.

#### Start the Backend Server

In a terminal, first export all required API Keys (see [API Keys Configuration](#-api-keys-configuration) section above) and then start the backend API server:


```bash
python -m uvicorn alias.server.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend server will:
- Automatically initialize the database (SQLite by default, or PostgreSQL if configured)
- Create the initial superuser account (if not exists)
- Start on `http://localhost:8000` (or the port specified in `.env`)

Verify the server is running by visiting `http://localhost:8000/api/v1/health`.

#### Start the Frontend

In a separate terminal, start the frontend development server:

```bash
# From the project root directory
cd frontend
npm run dev
```

The frontend will start on `http://localhost:5173` (or the port specified in `vite.config.ts`). The frontend is configured to proxy API requests to the backend server at `http://localhost:8000`.


#### Start the Memory Service Server

> **Note**: The Memory Service is required if you want to enable long-term memory features in General mode. Make sure to start the Memory Service before using the `--use_long_term_memory` flag in CLI or setting `use_long_term_memory_service: true` in API requests.

First install the Memory Service package in development mode

```bash
# From the project root directory
cd src/alias/memory_service
pip install -e .
```

To use the Memory Service, you have two deployment options:

**Option 1: Command Line Startup**

1. First, add the following environment variables to your `.env` file:

```bash
# Redis Configuration
USER_PROFILING_REDIS_SERVER=localhost
USER_PROFILING_REDIS_PORT=6379

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_EMBEDDING_MODEL_DIMS=1536

# DashScope Configuration
DASHSCOPE_EMBEDDER=text-embedding-v4
DASHSCOPE_MODEL_4_MEMORY=qwen3-max
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# User Profiling Configuration
USER_PROFILING_BASE_URL=http://localhost:6382
USER_PROFILING_SERVICE_PORT=6382
```

2. Then run the startup script:

```bash
# From the project root directory
bash script/start_memory_service.sh
```

The script will automatically check and start Redis and Qdrant services (via Docker if available) before starting the memory service.

**Option 2: Docker Deployment**

For Docker-based deployment, please refer to the detailed documentation at [Detailed Docs](src/alias/memory_service/docker/README.md).

#### Access the Application

Once both servers are running:
- **Frontend UI**: Open `http://localhost:5173` in your browser
- **Backend API**: Available at `http://localhost:8000`
- **API Documentation**: Available at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/api/v1/openapi.json` (OpenAPI JSON)
- **Health Check**: `http://localhost:8000/api/v1/health`

#### Default Login Credentials

After the first startup, you can log in with the superuser credentials configured in `.env`:
- **Email**: As specified in `FIRST_SUPERUSER_EMAIL` (default: `alias@agentscope.com`)
- **Username**: As specified in `FIRST_SUPERUSER_USERNAME` (default: `alias`)
- **Password**: As specified in `FIRST_SUPERUSER_PASSWORD`


## ⚖️ License

Alias-Agent is released under the **Apache 2.0 License** – see the [LICENSE](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE) file for details.
