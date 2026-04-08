# Training Financial Deep Research Agent with RL using AgentScope-Tuner

## Overview

DeepFinance is a reinforcement learning training framework for financial deep research agents. Instead of relying on human-annotated "gold answers", it drives the model to autonomously explore optimal research strategies through a **multi-dimensional reward system** (evidence traceability × analytical sufficiency × readability).

## Task Setting

### Agent Goal

Given a financial research question (stock analysis / industry research / event interpretation / macro analysis / stock screening), the agent must:
- Call financial tools to collect real-world data
- Generate a Markdown research report with academic-style citations
- End the report with the `[TASK_COMPLETED]` marker

### Agent Type

The agent is implemented as a **ReActAgent**, following a two-phase deep research methodology (defined in `prompt/finance_analyst_prompt.md`):

**Phase 1: Outline First, Then Investigate**
1. Identify the query type
2. **Output a research outline first** (section headings + key questions per section) — no tool calls at this stage
3. Investigate section by section, summarizing after each round of tool calls

**Phase 2: Deep Analysis and Report Generation**
1. Generate a Markdown-format research report based on real data
2. If evidence gaps are found during writing, allow 1–2 additional rounds of tool calls
3. Append `[TASK_COMPLETED]` at the end of the report

> Why "plan first, then execute"? Letting the model freely explore in a complex tool environment typically leads not to "failing to call tools", but to "failing to form a complete research process" — the model grabs one piece of data and immediately starts local analysis, resulting in a loosely structured report. Requiring an outline first helps develop a stable research workflow and reduces ineffective exploration.

### Tool Environment

The agent communicates with the [Finance MCP](https://github.com/flowllm-ai/finance-mcp) service via MCP (Model Context Protocol), using **19 financial tools** (defined in `prompt/tool_prompt_builder.py`):
- **Entity & Computation**: entity extraction, A-share historical price calculation
- **General Capabilities**: DashScope search, Python/Shell code execution
- **THS Specialized Data**: company fundamentals, shareholders, financials, earnings forecasts, news & announcements, institutional holdings, and 13 other specialized queries

**Tool Call Conventions:**
- Up to **3 tools** per call, using multi-round progressive investigation
- Summarize after each round of tool calls before deciding the next investigation direction

### Reward Design

The reward is split into **1 core objective + 3 constraints**:

| Role | Dimension | Code Module | Core Question |
| :--- | :--- | :--- | :--- |
| **Core** | Analytical Sufficiency (RM) | `judge/finance/` | Is the analysis thorough? Is the logic sound? |
| Constraint | Presentation Quality | `judge/presentation_quality/` | Is information easy to access? Good reader experience? |
| Constraint | Citation Grounding | `judge/grounding/` | Are key facts cited? Are citations real? |
| Constraint | Citation Audit | `judge/audit/` | Do citations truly support the claims? |

**Scoring (Extract First, Then Score)**: The LLM first extracts structured information from the report (citations, evidence relationships, etc.), then Python rules compute the scores. For example, the Audit grader only requires the LLM to classify each citation as Supported / Overstated / Contradicted / Hallucinated / Irrelevant, and the final score is computed by rule-based code.

**Tool Call Penalty** (defined in `deep_finance_judge.py`):

| Tool Calls | Penalty |
| :--- | :--- |
| 0 calls | -1.0 |
| 1–2 calls | -0.5 |
| ≥ 3 calls | 0.0 (no penalty) |

**Default Weights** (configurable in `deepfinance_tuner.sh`):
```bash
RM_WEIGHT=0.5                        # Analytical sufficiency (core objective)
PRESENTATION_QUALITY_WEIGHT=0.2      # Presentation quality
GROUNDING_WEIGHT=0.1                 # Citation grounding
AUDIT_WEIGHT=0.2                     # Citation audit
```


## Code Implementation

### High-Level Overview

The implementation consists of three main components:
1. **Workflow** (`run_deep_finance`): ReActAgent + Finance MCP tool interaction loop
2. **Judge** (`deep_finance_judge`): Multi-dimensional evaluation engine, combining OpenJudge + rule-based scoring
3. **Entry** (`main.py`): Calls `tune()` to launch training

### Agent Workflow

`run_deep_finance` implements the agent–tool interaction loop:

```python
async def run_deep_finance(
    task: Dict[str, Any],
    model: OpenAIChatModel,
    auxiliary_models: Dict[str, OpenAIChatModel] | None = None,
) -> WorkflowOutput:
    # 1. Extract system prompt and user query
    sys_prompt, user_query = _extract_sys_and_user(task)

    # 2. Get Finance MCP toolkit (process-local singleton, lazily loaded)
    toolkit = await get_finance_mcp_toolkit()

    # 3. Create ReActAgent
    agent = ReActAgent(
        name="deep_finance_react",
        sys_prompt=sys_prompt,
        model=model,
        enable_meta_tool=False,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
    )

    # 4. Execute research task
    response = await agent.reply(msg=Msg("user", user_query, role="user"))

    # 5. Extract tool call statistics
    tool_stats = await extract_tool_stats_from_agent(agent, total_time)
    metrics = compute_single_tool_metrics(tool_stats)

    return WorkflowOutput(response=response_dict, metrics=metrics)
```

**Key Features:**
- MCP Toolkit is lazily loaded as a singleton per worker process, with built-in jitter to prevent thundering herd
- System prompt is dynamically generated from `prompt/finance_analyst_prompt.md` (injecting current date and tool list)

### Judge Function

`deep_finance_judge` uses `DeepFinanceJudgeEngine` for multi-dimensional evaluation:

```python
async def deep_finance_judge(
    task: Dict[str, Any],
    response: Any,
    auxiliary_models: Dict[str, ChatModelBase] | None = None,
) -> JudgeOutput:
    engine = _get_judge_engine()
    reward, metrics = await engine.evaluate_one(task=task, response=response)
    return JudgeOutput(reward=reward, metrics=metrics)
```

Evaluation flow:
1. Build conversation history from response, convert to OpenJudge format
2. Run multiple graders in parallel (Presentation Quality / Citation Grounding / Citation Audit)
3. Run Finance RM (pairwise evaluation using a dedicated stronger model)
4. Fuse scores + tool call penalty → final reward

### Launch Training with `tune()`

```python
from agentscope.tuner import tune

tune(
    workflow_func=run_deep_finance,
    judge_func=deep_finance_judge,
    config_path="config_template.yaml",
)
```

For training configuration, refer to [config_template.yaml](./config_template.yaml). For full configuration details, see the [Trinity-RFT Configuration Guide](https://agentscope-ai.github.io/Trinity-RFT/en/main/tutorial/trinity_configs.html).

## How to Run

### Dependencies

```bash
# Recommended: use conda or uv to manage virtual environments
conda create -n tune_example python=3.11
conda activate tune_example

# Install core dependencies
pip install agentscope vllm ray wandb

# Install OpenJudge
git clone https://github.com/agentscope-ai/OpenJudge.git
cd OpenJudge
pip install -e .
```

### Step 1: Install and Start Finance MCP Service

Finance MCP provides the financial tool suite (search, web crawling, THS data, etc.).

**Install:**
```bash
pip install finance-mcp
```

**Start the service (SSE mode):**
```bash
finance-mcp \
  config=default,ths,crawl \
  disabled_flows='["tavily_search","mock_search","react_agent"]' \
  mcp.transport=sse \
  mcp.port=8040
```

The service will be available at: `http://<server_IP>:8040/sse` (use `127.0.0.1` for local, replace with actual IP for remote access)

**Required API Keys (configure as needed in `.env`):**

| Variable | Purpose |
|----------|---------|
| `DASHSCOPE_API_KEY` | DashScope search |
| `TUSHARE_API_TOKEN` | China A-share historical data |
| `TAVILY_API_KEY` | Tavily search (optional) |

### Step 2: Configure Environment Variables

Copy `tuner/deep_finance/.env.example`, rename it to `.env`, and place it in the project root:

```bash
# ==================== .env ====================
# API keys (for Judge scoring and external tools)
OPENJUDGE_API_KEY="sk-xxx"
OPENJUDGE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# Base model and environment paths
MODEL_PATH="/path/to/base_model"
CONDA_PATH="/path/to/conda/conda.sh"
CONDA_ENV="tune_example"

# Data and reference answer paths
DATA_PATH="/path/to/train_data_dir"
TRAIN_REF_ANS_PATH="/path/to/train_reference_answer.json"
VAL_REF_ANS_PATH="/path/to/val_reference_answer.json"

# Cluster config (set WORLD_SIZE to 1 for single-machine)
WORLD_SIZE=1
MASTER_ADDR="127.0.0.1"

# Finance MCP service URL
FINANCE_MCP_URL="http://127.0.0.1:8040/sse"
```

### Step 3: Launch Training

No need to manually edit Python or YAML files. The launch script `deepfinance_tuner.sh` dynamically generates `config_template.yaml` and automatically starts the Ray cluster.

```bash
bash deepfinance_tuner.sh
```

**Key training parameters (configurable in `deepfinance_tuner.sh`):**

| Shell Parameter | Tuner Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| `GROUP_SIZE` | `repeat_times` | 4 | Parallel rollout samples per query |
| `MAX_ENV_STEPS` | `max_env_steps` | 10 | Max agent-environment interaction rounds |
| `BATCH_SIZE` | `batch_size` | 64 | Global batch size |
| `OPENJUDGE_LLM` | `openjudge_llm` | qwen-flash | General model for OpenJudge scoring |
| `FINANCE_JUDGE_LLM` | `finance_judge_llm` | qwen-max | Stronger model for financial analysis depth evaluation |
| `ENGINE_NUM` | `engine_num` | Node // 2 | Number of vLLM async inference engines |
| `GPU_PER_NODE` | `gpu_per_node` | 8 | GPUs per node |

## Code Structure

```
deep_finance/
├── main.py                          # Entry: defines workflow and judge functions
├── deep_finance_judge.py            # Judge engine: multi-grader fusion + reward computation
├── config_template.yaml             # Tuner config template (dynamically generated by shell script)
├── deepfinance_tuner.sh             # Multi-node distributed launch script
├── deepfinance_tuner_single.sh      # Single-machine launch script
├── .env.example                     # Environment variable template
├── judge/
│   ├── finance/                     # RM: domain-routed pairwise evaluation
│   ├── presentation_quality/        # Presentation: 8-dimension rule-based scoring
│   ├── grounding/                   # Grounding: coverage + authenticity
│   ├── audit/                       # Audit: 5-level verdict classification
│   └── traj_adapter.py              # Trajectory format normalization
├── metric_helper/
│   ├── reward_metric_helper.py      # Reward metrics aggregation
│   └── tool_metric_helper.py        # Tool call statistics
└── prompt/
    ├── finance_analyst_prompt.md     # Agent system prompt (two-phase research flow)
    └── tool_prompt_builder.py        # Tool documentation generator (19 financial tools)
```
