<p align="center">
  <img
    src="assets/alias.png"
    alt="Alias-Agent 徽标"
    width="500"
    height="auto"
  />
</p>

<h2 align="center">Alias-Agent：即刻启动，随需定制，轻松部署</h2>

<div align="center">

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Docs](https://img.shields.io/badge/built--on-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/built--on-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

<p align="center">
<u>
开启你的独特体验: <a href="https://alias.agentscope.io/"> alias.agentscope.io</a>
</u>
</p>

</div>

[[English README]](README.md)


*Alias-Agent*（简称 *Alias*）是一个基于 [AgentScope](https://github.com/agentscope-ai/agentscope) 和 [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/) 构建的、由大语言模型驱动的智能体，旨在作为通用智能助手响应用户查询。Alias 擅长分解复杂问题、构建解决路径，并应用合适的策略来处理多样化的现实世界任务。

Alias 采用多模式运行机制，实现灵活的任务执行，包括 `通用（General）模式`、`浏览器使用（Browser Use）模式`、`深度研究（Deep Research）模式`、`金融分析（Financial Analysis）模式` 和 `数据科学（Data Science）模式`。在不同运行模式间切换时，Alias 配备了定制化的指令、专业工具集以及协调各类专家智能体的能力。这使得 Alias 能够更好地适应不同下游任务的具体需求。例如，在处理金融分析时，Alias 采用可追溯的推理链并生成可解释的结果，以增强用户对其决策的信任，同时优化报告可视化效果；在解决数据科学任务时，Alias 可以访问用户关联的数据库，并旨在促进高效的数据分析、处理和预测。

我们的目标是让 Alias 成为一个开箱即用的解决方案，用户可以轻松部署以应对各种任务，并得到基于 AgentScope 生态系统的完整智能体开发、测试和部署流程的支持。除了作为一个即用型智能体，我们还希望 Alias 成为一个基础模板，能够适应多样化场景。我们鼓励开发者在工具、提示词和智能体层面扩展和定制 Alias，以满足特定需求。

我们欢迎更多开发者加入社区，共同推动持续创新。

## 📢 最新动态
- **[2025-12]** 提供五种运行模式：通用（General）模式、浏览器使用（Browser Use）模式、深度研究（Deep Research）模式、金融分析（Financial Analysis）模式和数据科学（Data Science）模式。

- **[2025-12]** 记忆系统升级：提供用于持久化工具调用追踪的 Tool Memory 服务，以及用于个性化用户体验的 User Profiling 服务。

- **[2025-12]** 前端 UI 使用 [Spark Design](https://sparkdesign.agentscope.io/) 进行设计，具备中断控制和工件编辑功能。

- **[2025-12]** 后端基于 [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/) 重构：轻量级单节点部署、简化的用户管理以及特定模式的启动引导。


## ✨ 特性

### 🤖 适用于多样化场景的多运行模式

提供五种运行模式以应对多样化的现实世界任务：

- **通用（General）模式**：元规划器（Meta Planner），能够根据任务上下文在简单任务、规划执行、浏览器使用、深度研究和数据科学模式之间自动切换。
- **浏览器使用（Browser Use）模式**：具备多模态能力的增强型Browser Use智能体。
- **深度研究（Deep Research）模式**：采用树状结构问题/假设探索并具备以用户为中心特性的深度研究智能体。
- **金融分析（Financial Analysis）模式**: 基于假设驱动的金融分析智能体。
- **数据科学（Data Science）模式**：专用于数据科学工作流（如机器学习、数值计算和探索性数据分析）的智能体。

#### 通用（General）模式

通用模式以元规划器（Meta Planner）为特色，通过自动模式切换和全面的中断支持来编排任务执行。Meta Planner根据上下文智能地将任务路由到合适的专业智能体，同时在整个执行生命周期中保持稳健的状态保存。这使得在不同运行模式（如深度研究和数据科学）之间能够实现无缝切换，并确保即使在任务被中断或重定向时也能保持连续性。

通用模式还提供了一个开箱即用的、特定于 AgentScope 的问答智能体（[更多详情](docs/qa_agent.md)），预先配置了高频的 AgentScope 相关问答对。通过集成 RAG 和 GitHub MCP 工具，问答智能体可以动态检索最新的源代码结构、官方教程和社区讨论，并结合从私有知识库中灵活匹配的相关信息，以提供准确的答案。

#### 浏览器使用（Browser Use）模式
<p align="center">
  <img
    src="assets/browser_agent.png"
    alt="浏览器使用模式"
    width="600"
    height="auto"
  />
</p>

浏览器使用（Browser Use）模式扩展了原Browser Use智能体，使其具备全面的多模态能力，能够对视觉内容进行细粒度理解并与网页元素进行智能交互。该智能体具备高级的图像理解能力，可以从图表、图形和视觉内容中提取语义信息，包括坐标轴标签、趋势和异常值。视频理解能力使得智能体能够提取视频内容并进行推理，而自动表格填写和智能文件下载工具则简化了表单交互和文档管理。

为了处理网页浏览的动态特性，Browser Use模式实现了复杂的动态子任务管理。系统会在网页发生变化时自动更新子任务，以适应新的内容、弹窗或导航事件。这确保了即使浏览环境发生变化，智能体也能保持上下文并继续执行任务，使其对于需要持续关注和适应的复杂多步骤网页交互特别有效。

#### 深度研究（Deep Research）模式
<p align="center">
  <img
    src="assets/deep_research.png"
    alt="深度研究模式"
    width="600"
    height="auto"
  />
</p>

深度研究（Deep Research）模式引入了以用户为中心（user-centric）的增强功能，将研究任务转变为协作、透明的过程。对于研究型问题，该智能体采用预搜索模块，在生成后续问题之前收集专业、详细的信息，确保提出的问题更有价值且信息充分。这种方法通过将问题建立在全面的背景知识之上，显著提高了研究交互的质量。

该模式还采用了树状结构的研究流程，通过不断深入的信息收集来驱动研究。用户还可以动态中断深度研究过程并引导研究方向。统一的执行路径提供了一个具有可配置提示词、标准操作程序和工具集的统一代码库，使得深度研究智能体能够适应不同领域，同时保持一致的、可扩展的架构。

 #### 金融分析（Financial Analysis）模式 ([详细文档](docs/financial_analysis.md))

<p align="center">
  <img
    src="docs/figures/finance_overview.png"
    alt="金融分析模式"
    width="600"
    height="auto"
  />
</p>

在金融分析场景中，复杂的推理和可追溯的逻辑链对于建立用户对模型结论的信任至关重要。为了实现 *可解释性*、*可追溯性* 和 *可干预性*，Alias-Agent 采用了假设驱动的智能体架构，明确地将任务执行转化为“提出假设 → 收集证据 → 验证假设 → 更新状态”的循环，作为通用深度研究流程的一种变体。这种架构使得分析逻辑能够被记录、检查和迭代，系统地解决了金融领域对透明证据链和清晰、可控逻辑的需求。

金融分析模式支持树状结构搜索，通过深度层次探索将复杂的金融研究问题分解为可验证的子假设。该模式集成了金融 MCP 工具（可配置 API 密钥以便使用）并优化了报告可视化。除了生成全面的最终报告外，系统还支持可视化整个树状搜索过程，并生成优化的、用于演示的交互式 HTML 文件，使复杂的金融分析更易于理解和解释。


#### 数据科学（Data Science）模式 ([详细文档](docs/data_science.md))

<div align="center" style="margin: 20px 0;">
  <img src="docs/figures/alias-ds-overall.png" width="80%" style="max-width: 800px; height: auto;">
</div>


在数据科学（Data Science）模式下，Alias-Agent 作为一个自主的、端到端的助手，将高层次的分析问题转化为可执行的数据科学工作流。它无缝处理从数据获取、清洗到建模、可视化和叙述性报告的全流程，只需最少的人工干预，使用户能够在现实场景中高效地从意图转向洞察。

启动时，数据科学模式使用智能路由器将用户任务分配给三个核心场景之一：探索性数据分析、预测建模或精确数据计算。每个场景都由专门定制的、符合其分析意图的提示词模板驱动。在此基础上，它具备可扩展的文件过滤流水线，以快速在海量数据湖中定位相关文件。它能够稳健地将不规则的电子表格（包括合并单元格、多级标题和嵌入式注释）解析为结构化表格或语义化 JSON。它还支持多模态理解，能够对视觉内容进行总结和自然语言问答。对于探索性数据分析任务，它会自动生成交互式 HTML 报告，结合了洞察、可视化和可执行代码，以确保透明度和可复现性。

### 🧠 增强的记忆系统

- **工具记忆（长期）**：通过 ReMe 持久化存储工具调用痕迹，实现自动化的总结和使用指导。
- **用户画像（长期）**: 通过动态候选评分捕获并精炼用户行为，并通过 mem0 提升为稳定画像，与前端交互无缝集成。

### 🖥️ 提供 CLI 和全栈部署方案

#### CLI 部署
- **命令行界面**：通过 `alias_agent run` 命令直接执行，支持模式选择和配置选项。

#### 全栈部署
- **前端**：基于 [Spark Design](https://sparkdesign.agentscope.io/) 的 React 应用程序，具备运行时中断控制、工件检查器和可编辑输出。
- **后端**：基于 [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/) 的轻量级单节点部署，具有简化的用户管理和特定模式的启动引导。


## 🚀 快速开始

### 💻 安装

> Alias 需要 **Python 3.10** 或更高版本。

首先，以开发模式安装包
```bash
# From the project root directory
pip install -e .
```

这将安装 `alias_agent` 命令行工具。

### 🐳 沙盒设置（可选）

```bash
# 如果使用 colima
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

# 选项 1：从企业镜像仓库拉取
export RUNTIME_SANDBOX_REGISTRY=agentscope-registry.ap-southeast-1.cr.aliyuncs.com
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-alias:latest

# 选项 2：从 Docker Hub 拉取
docker pull agentscope/runtime-sandbox-alias:latest
```

更多详情请参考 [AgentScope Runtime 文档](https://runtime.agentscope.io/zh/sandbox/sandbox.html)。

### 🔑 API 密钥配置

```bash
# 必需：模型 API 密钥（默认：DashScope）
export DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 必需：搜索 API 密钥（用于深度研究模式）
export TAVILY_API_KEY=your_tavily_api_key_here

# 可选：金融 MCP 工具 API 密钥（用于金融分析模式）。在以下地址激活 MCP 工具：
#  https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/Qieman
# https://bailian.console.aliyun.com/tab=app#/mcp-market/detail/tendency-software
export DASHSCOPE_MCP_API_KEY=your_dashscope_api_key_here


# 可选：GitHub token（用于问答智能体访问 GitHub 仓库）
# export GITHUB_TOKEN=your_github_token

# 可选：使用其他模型（例如 OpenAI）
# 首先，在 alias/agent/run.py 的 MODEL_FORMATTER_MAPPING 中添加你的模型
# export MODEL=gpt-4
# export OPENAI_API_KEY=your_openai_api_key_here
```

### 📝 基础用法 -- CLI 部署

使用不同模式执行智能体任务：

```bash
# 通用（General）模式
alias_agent run --mode general --task "Analyze Meta stock performance in Q1 2025"

# 浏览器使用（Browser Use）模式
alias_agent run --mode browser --task "Search five latest research papers about browser-use agent"

# 深度研究（Deep Research）模式
alias_agent run --mode dr --task "Research the impact of AI on healthcare"

# 金融分析（Financial Analysis）模式
alias_agent run --mode finance --task "Analyze Tesla's Q4 2024 financial performance"

# 数据科学（Data Science）模式
alias_agent run --mode ds \
  --task "Analyze the distribution of incidents across categories in 'incident_records.csv' to identify imbalances, inconsistencies, or anomalies, and determine their root cause." \
  --files ./docs/data/incident_records.csv
```

**注意**：使用 `--files` 上传的文件会自动复制到沙盒中的 `/workspace`。生成的文件可在 `sessions_mount_dir` 的子目录中找到。

#### 启用长期记忆服务（仅限通用模式）
要在通用模式下启用长期记忆服务，您需要：
1. **首先启动记忆服务**（请参阅下面的[启动记忆服务服务器](#启动记忆服务服务器)部分）
2. **在通用模式下运行时使用 `--use_long_term_memory` 标志**：
```bash
# 启用长期记忆服务的通用模式
alias_agent run --mode general --task "Analyze Meta stock performance in Q1 2025" --use_long_term_memory
```
**重要提示**：
- 只有显式添加 `--use_long_term_memory` 标志时才会启用长期记忆（默认禁用）
- 长期记忆服务仅在**通用模式**（元规划器）中可用
- 在启动智能体之前，记忆服务必须正在运行
- 启用后，智能体将在会话开始时检索用户画像信息，以提供个性化体验

### 基础用法 -- 全栈部署

要运行具有全栈部署（前端 + 后端）的 Alias-Agent，请按照以下步骤操作：

#### 前提条件

1. **安装前端依赖**：
```bash
# 从项目根目录
cd frontend
npm install
```

2. **配置环境变量**：
```bash
# 从项目根目录，复制示例环境文件
cp .env.example .env

# 编辑 .env 并配置以下关键变量：
# - USER_PROFILING_BASE_URL: 记忆服务 URL (例如, http://localhost:6380/alias_memory_service)
# - REDIS_HOST: Redis 主机 (默认: localhost)
# - REDIS_PORT: Redis 端口 (默认: 6379)
# - BACKEND_PORT: 后端服务器端口 (默认: 8000)
# - FIRST_SUPERUSER_EMAIL: 初始管理员邮箱 (默认: alias@agentscope.com)
# - FIRST_SUPERUSER_USERNAME: 初始管理员用户名 (默认: alias)
# - FIRST_SUPERUSER_PASSWORD: 初始管理员密码 (默认: alias)
```

3. **启动 Redis**（缓存和会话管理所需）：
```bash
# 使用 Docker (推荐)
docker run -d -p 6379:6379 --name alias-redis redis:7-alpine

# 或使用本地 Redis 安装
redis-server
```

#### 启动沙盒服务器（可选但推荐）

为了获得包括代码执行和文件操作在内的完整功能，请在另一个终端中启动沙盒服务器：

```bash
# 从项目根目录
runtime-sandbox-server --extension src/alias/runtime/alias_sandbox/alias_sandbox.py
```

沙盒服务器能够在隔离的容器中安全地执行代码，这对于数据科学模式和其他需要代码执行的功能至关重要。

#### 启动后端服务器

在一个终端中，首先导出所有必需的 API 密钥（请参阅上面的 [API 密钥配置](#-api-密钥配置) 部分），然后启动后端 API 服务器：


```bash
python -m uvicorn alias.server.main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务器将：
- 自动初始化数据库（默认 SQLite，或如果配置了则使用 PostgreSQL）
- 创建初始超级用户账户（如果不存在）
- 在 `http://localhost:8000` 启动（或 `.env` 中指定的端口）

通过访问 `http://localhost:8000/api/v1/health` 来验证服务器是否正在运行。

#### 启动前端

在另一个单独的终端中，启动前端开发服务器：

```bash
# 从项目根目录
cd frontend
npm run dev
```

前端将在 `http://localhost:5173` 启动（或在 `vite.config.ts` 中指定的端口）。前端配置为将 API 请求代理到 `http://localhost:8000` 的后端服务器。


#### 启动记忆服务服务器

> **注意**：如果您想在通用模式下启用长期记忆功能，则需要记忆服务。在使用 CLI 中的 `--use_long_term_memory` 标志或在 API 请求中设置 `use_long_term_memory_service: true` 之前，请确保已启动记忆服务。

首先，以开发模式安装 Memory Service 包

```bash
# 从项目根目录
cd src/alias/memory_service
pip install -e .
```

要使用记忆服务，您有两种部署选项：

**选项 1：命令行启动**

1. 首先，将以下环境变量添加到您的 `.env` 文件中：

```bash
# Redis 配置
USER_PROFILING_REDIS_SERVER=localhost
USER_PROFILING_REDIS_PORT=6379

# Qdrant 配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_EMBEDDING_MODEL_DIMS=1536

# DashScope 配置
DASHSCOPE_EMBEDDER=text-embedding-v4
DASHSCOPE_MODEL_4_MEMORY=qwen3-max
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# User Profiling 配置
USER_PROFILING_BASE_URL=http://localhost:6382
USER_PROFILING_SERVICE_PORT=6382
```

2. 然后运行启动脚本：

```bash
# 从项目根目录
bash script/start_memory_service.sh
```

该脚本将在启动记忆服务之前自动检查并启动 Redis 和 Qdrant 服务（如果 Docker 可用则通过 Docker 启动）。

**选项 2：Docker 部署**

有关基于 Docker 的部署，请参阅[详细文档](src/alias/memory_service/docker/README.md)。

#### 访问应用程序

一旦两个服务器都运行起来：
- **前端 UI**：在浏览器中打开 `http://localhost:5173`
- **后端 API**：可在 `http://localhost:8000` 访问
- **API 文档**：可在 `http://localhost:8000/docs` (Swagger UI) 或 `http://localhost:8000/api/v1/openapi.json` (OpenAPI JSON) 访问
- **健康检查**：`http://localhost:8000/api/v1/health`

#### 默认登录凭据

首次启动后，您可以使用在 `.env` 中配置的超级用户凭据登录：
- **邮箱**：如 `FIRST_SUPERUSER_EMAIL` 所指定 (默认: `alias@agentscope.com`)
- **用户名**：如 `FIRST_SUPERUSER_USERNAME` 所指定 (默认: `alias`)
- **密码**：如 `FIRST_SUPERUSER_PASSWORD` 所指定


## ⚖️ 许可证

Alias-Agent 根据 **Apache 2.0 许可证**发布 - 详情请参阅 [LICENSE](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE) 文件。
