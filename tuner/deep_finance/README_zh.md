# 使用 AgentScope-Tuner 训练金融深度研究 Agent

## 概述

DeepFinance 是金融深度研究 Agent 的强化学习训练方案。它不依赖人工标注的「标准回答」，而是通过 **多维度奖励体系**（证据可追溯 × 分析充分性 × 可读性）驱动模型自主探索最优研究策略。

## 任务设定

### 智能体目标

给定金融研究问题（个股分析 / 行业研究 / 事件解读 / 宏观分析 / 股票检索），智能体需要：
- 调用金融工具收集真实数据
- 生成带有学术引用规范的 Markdown 研究报告
- 报告末尾以 `[TASK_COMPLETED]` 标记结束

### 智能体类型

智能体实现为 **ReActAgent**，遵循两阶段深度研究方法（定义在 `prompt/finance_analyst_prompt.md`）：

**第一阶段：先大纲后调研**
1. 理解用户问题类型
2. **先输出研究大纲**（一级/二级标题 + 每节的 Key Questions），此阶段不调用工具
3. 按大纲逐段调研，每轮调用工具后做小结

**第二阶段：深度分析与报告生成**
1. 基于真实数据生成 Markdown 格式研究报告
2. 写作中发现证据不足时允许追加 1-2 轮工具调用补充取证
3. 报告末尾添加 `[TASK_COMPLETED]` 标记

> 为什么要「先规划再执行」？如果让模型在复杂工具环境中完全自由探索，最常见的问题不是"不会调用工具"，而是"没有形成完整研究过程"——查到一个信息就开始局部分析，最后报告结构松散。通过要求先输出研究大纲，可以形成较稳定的研究展开方式，减少无效探索。

### 工具环境

智能体通过 MCP（Model Context Protocol）协议与 [Finance MCP](https://github.com/flowllm-ai/finance-mcp) 服务交互，使用 **19 个金融工具**（定义见 `prompt/tool_prompt_builder.py`）：
- **实体与计算**：提取实体、A股历史股价计算
- **通用能力**：DashScope 搜索、Python/Shell 代码执行
- **同花顺专项数据**：公司基本面、股东、财务、盈利预测、新闻公告、主力持仓等 13 项专项查询

**工具调用规范：**
- 每次最多调用 **3 个工具**，采用多轮次渐进式调研
- 每轮工具调用后先做小结，再决定下一步调研方向

### 奖励设计

奖励拆分为 **1 个核心目标 + 3 个约束项**：

| 角色 | 维度 | 代码模块 | 核心问题 |
| :--- | :--- | :--- | :--- |
| **核心目标** | 分析充分性 (RM) | `judge/finance/` | 分析是否充分？逻辑是否合理？ |
| 约束项 | 呈现质量 | `judge/presentation_quality/` | 信息是否易获取？读者体验好不好？ |
| 约束项 | 引用规范性 | `judge/grounding/` | 关键事实是否都有引用？引用是否真实？ |
| 约束项 | 引用逻辑审计 | `judge/audit/` | 引用是否真正支撑了陈述？ |

**计分方式（先抽取，再计分）**：LLM 先从报告中提取结构化信息（引用、证据关系等），再由 Python 规则计分。例如引用审计只需 LLM 判断每条引用属于 Supported / Overstated / Contradicted / Hallucinated / Irrelevant 五类之一，最终分数由规则代码统计得出。

**工具调用惩罚**（定义在 `deep_finance_judge.py`）：

| 工具调用次数 | 惩罚值 |
| :--- | :--- |
| 0 次 | -1.0 |
| 1-2 次 | -0.5 |
| ≥ 3 次 | 0.0（无惩罚） |

**默认权重**（可在 `deepfinance_tuner.sh` 中调整）：
```bash
RM_WEIGHT=0.5                        # 分析充分性（核心目标）
PRESENTATION_QUALITY_WEIGHT=0.2      # 呈现质量
GROUNDING_WEIGHT=0.1                 # 引用规范性
AUDIT_WEIGHT=0.2                     # 引用逻辑审计
```


## 代码实现

### 高级概览

实现由三部分组成：
1. **Workflow** (`run_deep_finance`)：ReActAgent + Finance MCP 工具的交互流程
2. **Judge** (`deep_finance_judge`)：多维度评估引擎，融合 OpenJudge + 规则计分
3. **入口** (`main.py`)：调用 `tune()` 启动训练

### Agent Workflow

`run_deep_finance` 实现智能体与金融工具的交互流程：

```python
async def run_deep_finance(
    task: Dict[str, Any],
    model: OpenAIChatModel,
    auxiliary_models: Dict[str, OpenAIChatModel] | None = None,
) -> WorkflowOutput:
    # 1. 提取 system prompt 和用户问题
    sys_prompt, user_query = _extract_sys_and_user(task)

    # 2. 获取 Finance MCP 工具集（进程内 singleton 懒加载）
    toolkit = await get_finance_mcp_toolkit()

    # 3. 创建 ReActAgent
    agent = ReActAgent(
        name="deep_finance_react",
        sys_prompt=sys_prompt,
        model=model,
        enable_meta_tool=False,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
    )

    # 4. 执行研究任务
    response = await agent.reply(msg=Msg("user", user_query, role="user"))

    # 5. 提取工具调用统计
    tool_stats = await extract_tool_stats_from_agent(agent, total_time)
    metrics = compute_single_tool_metrics(tool_stats)

    return WorkflowOutput(response=response_dict, metrics=metrics)
```

**关键特性：**
- MCP Toolkit 在每个 Worker 进程中以 singleton 模式懒加载，内置 jitter 防止惊群效应
- System prompt 从 `prompt/finance_analyst_prompt.md` 模板动态生成（注入当前日期和工具列表）

### Judge 函数

`deep_finance_judge` 使用 `DeepFinanceJudgeEngine` 进行多维度评估：

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

评估流程：
1. 从 response 构建对话历史，转换为 OpenJudge 格式
2. 并行运行多个 Grader（呈现质量 / 引用规范 / 引用审计）
3. 运行 Finance RM（pairwise 评估，使用独立的强模型）
4. 融合分数 + 工具调用惩罚 → 最终 reward

### 使用 `tune()` 启动训练

```python
from agentscope.tuner import tune

tune(
    workflow_func=run_deep_finance,
    judge_func=deep_finance_judge,
    config_path="config_template.yaml",
)
```

训练配置请参考 [config_template.yaml](./config_template.yaml)。完整配置详情请参考 [Trinity-RFT 配置指南](https://agentscope-ai.github.io/Trinity-RFT/en/main/tutorial/trinity_configs.html)。

## 运行方法

### 依赖

```bash
# 建议使用 conda 或 uv 管理虚拟环境
conda create -n tune_example python=3.11
conda activate tune_example

# 安装基础依赖
pip install agentscope vllm ray wandb

# 安装 OpenJudge
git clone https://github.com/agentscope-ai/OpenJudge.git
cd OpenJudge
pip install -e .
```

### 步骤 1：安装启动 Finance MCP 服务

Finance MCP 提供金融研究相关的工具集（搜索、爬虫、同花顺数据等）。

**安装：**
```bash
pip install finance-mcp
```

**启动服务（SSE 模式）：**
```bash
finance-mcp \
  config=default,ths,crawl \
  disabled_flows='["tavily_search","mock_search","react_agent"]' \
  mcp.transport=sse \
  mcp.port=8040
```

启动后服务地址为：`http://<服务器IP>:8040/sse`（本地使用 `127.0.0.1`，远程访问需替换为实际 IP）

**所需 API Keys（按需配置，添加到 `.env` 文件）：**

| 变量名 | 用途 |
|--------|------|
| `DASHSCOPE_API_KEY` | DashScope 搜索 |
| `TUSHARE_API_TOKEN` | A股历史数据 |
| `TAVILY_API_KEY` | Tavily 搜索（可选） |

### 步骤 2：准备环境变量

复制 `tuner/deep_finance/.env.example` 模板并重命名为 `.env`，放置在项目根目录下：

```bash
# ==================== .env ====================
# API keys (用于 Judge 评分与外部工具)
OPENJUDGE_API_KEY="sk-xxx"
OPENJUDGE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# 基础模型与环境路径
MODEL_PATH="/path/to/base_model"
CONDA_PATH="/path/to/conda/conda.sh"
CONDA_ENV="tune_example"

# 数据与参考答案路径
DATA_PATH="/path/to/train_data_dir"
TRAIN_REF_ANS_PATH="/path/to/train_reference_answer.json"
VAL_REF_ANS_PATH="/path/to/val_reference_answer.json"

# 集群配置 (如果是单机，WORLD_SIZE 设为 1)
WORLD_SIZE=1
MASTER_ADDR="127.0.0.1"

# Finance MCP 服务地址
FINANCE_MCP_URL="http://127.0.0.1:8040/sse"
```

### 步骤 3：一键启动训练

无需手动修改 Python 代码或 YAML 文件。启动脚本 `deepfinance_tuner.sh` 会根据环境变量**动态生成** `config_template.yaml`，并自动拉起 Ray 集群。

```bash
bash deepfinance_tuner.sh
```

**核心训练参数（可在 `deepfinance_tuner.sh` 中修改）：**

| 参数名 (Shell) | 对应 Tuner 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `GROUP_SIZE` | `repeat_times` | 4 | 每个 query rollout 的并行采样次数 |
| `MAX_ENV_STEPS` | `max_env_steps` | 10 | Agent 与环境交互的最大轮数 |
| `BATCH_SIZE` | `batch_size` | 64 | 全局 Batch Size |
| `OPENJUDGE_LLM` | `openjudge_llm` | qwen-flash | OpenJudge 评分使用的通用模型 |
| `FINANCE_JUDGE_LLM` | `finance_judge_llm` | qwen-max | 金融分析深度评价的强模型 |
| `ENGINE_NUM` | `engine_num` | Node // 2 | vLLM 异步推理引擎的实例数 |
| `GPU_PER_NODE` | `gpu_per_node` | 8 | 单节点 GPU 数量 |

## 代码结构

```
deep_finance/
├── main.py                          # 入口：定义 workflow 函数与 judge 函数
├── deep_finance_judge.py            # Judge 引擎：多 grader 融合 + reward 计算
├── config_template.yaml             # Tuner 配置模板（由 shell 脚本动态生成）
├── deepfinance_tuner.sh             # 多机分布式启动脚本
├── deepfinance_tuner_single.sh      # 单机启动脚本
├── .env.example                     # 环境变量模板
├── judge/
│   ├── finance/                     # RM: 按 domain 路由的 pairwise 评分
│   ├── presentation_quality/        # 呈现质量: 8 维规则计分
│   ├── grounding/                   # 引用规范: coverage + grounding
│   ├── audit/                       # 引用审计: 5 级判定
│   └── traj_adapter.py              # 轨迹格式归一化
├── metric_helper/
│   ├── reward_metric_helper.py      # Reward 指标聚合
│   └── tool_metric_helper.py        # 工具调用统计
└── prompt/
    ├── finance_analyst_prompt.md     # Agent system prompt（两阶段研究流程）
    └── tool_prompt_builder.py        # 工具列表文档生成（19 个金融工具）
```
