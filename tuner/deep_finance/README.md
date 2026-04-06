# DeepFinance: 基于 AgentScope Tuner 的金融深度研究 Agent

## 概述

DeepFinance 是一个基于 **AgentScope Tuner** 框架构建的金融深度研究 Agent 强化学习训练方案。其核心目标是：通过 GRPO（Group Relative Policy Optimization）强化学习算法，训练大语言模型（LLM）自主调用金融工具、收集多源数据、进行交叉验证，并最终生成结构化、有据可查的专业投资研究报告。

与传统 SFT 微调不同，DeepFinance 不依赖人工标注的「标准回答」来监督训练，而是设计了一套 **多维度奖励体系** 作为 RL 训练信号。借助 AgentScope Tuner 强大的分布式调度能力，模型在「写报告」的过程中自行探索最优策略，并通过 5 个正交维度的打分反馈来持续改进。

**训练闭环**：

```plain
金融问题 → Agent 调用工具收集数据 → 生成研究报告 → 多维度 Judge 评分 → 经验回传 → GRPO 策略更新 → 下一轮生成
```

-----

## 核心架构 (Pipeline)

DeepFinance 现已全面迁移至 **AgentScope Tuner**，实现了推理采样（Rollout）、奖励计算（Judge）和模型更新（Trainer）的分布式解耦，通过 Ray 极大提升了多机多卡的吞吐效率。

整个训练流水线由以下核心模块组成：

```plain
┌─────────────────────────────────────────────────────────────┐
│                  AgentScope Tuner 训练框架                   │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────┐               │
│  │  Explorer    │───>│  Workflow (ReAct)    │               │
│  │ (分布式 Rollout)│   │  调用 EnvService 交互  │               │
│  └──────┬───────┘    └──────────────────────┘               │
│         │                                                   │
│         v                                                   │
│  ┌──────────────┐    ┌──────────────────────┐               │
│  │    Judge     │───>│ Finance + OpenJudge  │               │
│  │ (多维度打分)   │   │ RM/呈现/事实/审计/EBTU │               │
│  └──────┬───────┘    └──────────────────────┘               │
│         │                                                   │
│         v                                                   │
│  ┌──────────────┐    ┌──────────────────────┐               │
│  │ Experience   │───>│       Trainer        │               │
│  │ Buffer       │    │ (GRPO 多机多卡优化)    │               │
│  └──────────────┘    └──────────┬───────────┘               │
│                                 │                           │
│  ┌──────────────┐               │                           │
│  │ Synchronizer │<──────────────┘                           │
│  │ (动态模型同步) │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

-----

## Workflow 设计

### 两阶段深度研究流程

Agent 的 System Prompt 要求遵循两阶段研究方法：

**第一阶段：先大纲后调研**
1. 理解用户问题类型（个股分析/行业研究/事件解读/宏观分析/股票检索）
2. **先输出研究大纲**（一级/二级标题 + 每节的 Key Questions），此阶段不调用工具
3. 按大纲逐段调研，每轮调用工具后做小结

**第二阶段：深度分析与报告生成**
1. 当数据充分后，基于真实数据生成 Markdown 格式研究报告
2. 写作中发现证据不足时允许追加 1-2 轮工具调用补充取证
3. 报告末尾添加 `[TASK_COMPLETED]` 标记

### 引用规范
Agent 被要求使用学术论文风格的引用标注：
* 所有关键事实句句末必须添加引用编号 `[n]`
* 报告末尾必须包含 `## References` 小节
* 引用必须可追溯到实际工具返回的数据，禁止伪造

-----

## 工具体系

DeepFinance 集成了 **19 个金融工具**，通过 MCP（Model Context Protocol）协议与 EnvService 交互，覆盖金融研究的完整数据需求。工具类别包括：
* **实体与计算**：提取实体、A股历史股价计算
* **通用能力**：Dashscope 搜索、Python/Shell 代码执行
* **同花顺专项数据**：公司基本面、股东、财务、盈利预测、新闻公告、主力持仓等 13 项专项查询

**工具调用规范：**
* 每次最多调用 **3 个工具**，采用多轮次渐进式调研
* Agent 必须先搜索确认信息，再进行深度查询
* 每轮工具调用后先做小结，再决定下一步调研方向

-----

## 奖励设计（Reward Design）

我们在 `deep_finance_judge.py` 中设计了 **5 个正交维度** 的评分器（Grader），通过独立的 Judge 引擎并发评估，最终计算得出 `JudgeOutput`。

### 5 个评分维度总览

| 维度 | 名称 | 评估对象 | 核心问题 |
| :--- | :--- | :--- | :--- |
| **分析充分性** | RM Gallery | 报告整体质量 | 分析是否充分？逻辑是否合理？ |
| **呈现质量** | PresentationQuality | 报告排版与结构 | 读者体验好不好？信息是否易获取？ |
| **引用规范性** | Grounding | 引用的覆盖与真实性 | 关键事实是否都有引用？引用是否真实？ |
| **引用逻辑审计** | Audit | 引用的逻辑蕴含关系 | 引用是否真正支撑了对应的陈述？有没有夸大或捏造？ |
| **可追溯性审计** | EBTU | 证据优先可追溯性 | 报告生成的内容是否能完美追溯到工具返回的底层证据？ |

**默认权重配置（可在 shell 脚本中调整）：**
```bash
RM_WEIGHT=0.5                        # 分析充分性
PRESENTATION_QUALITY_WEIGHT=0.25     # 呈现质量
GROUNDING_WEIGHT=0.1                 # 引用规范性
AUDIT_WEIGHT=0.2                     # 引用逻辑审计
EBTU_WEIGHT=0.0                      # EBTU 证据优先可追溯性审计
```
*(注：此外还包含针对零工具调用的硬性规则惩罚)*

-----

## Quick Start

### 1. 环境准备

安装 AgentScope 及相关依赖：
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

### 2. 准备环境变量

复制一份配置文件模板并重命名为 `.env`，将其放置在项目根目录下：

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

# 其它配置
FINANCE_MCP_URL="http://127.0.0.1:8080"
```

### 3. 一键启动训练

无需手动修改 Python 代码或 YAML 文件。我们的启动脚本 `deepfinance_tuner.sh` 会根据环境变量和脚本内的设定，**动态生成** `config_template.yaml` 供 AgentScope Tuner 消费，并自动拉起 Ray 集群。

```bash
# 直接运行启动脚本
bash deepfinance_tuner.sh
```

**核心训练参数对照表（可在 `deepfinance_tuner.sh` 中修改）：**

| 参数名 (Shell) | 对应 Tuner 参数 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `GROUP_SIZE` | `repeat_times` | 4 | 每个 query rollout 的并行采样次数 |
| `MAX_ENV_STEPS` | `max_env_steps` | 10 | Agent 与环境交互的最大轮数 |
| `BATCH_SIZE` | `batch_size` | 64 | 全局 Batch Size |
| `OPENJUDGE_LLM` | `openjudge_llm` | qwen-flash | OpenJudge 评分使用的通用模型 |
| `FINANCE_JUDGE_LLM` | `finance_judge_llm` | qwen-max | 专门用于评价金融分析深度的强模型 |
| `ENGINE_NUM` | `engine_num` | Node // 2 | vLLM 异步推理引擎的实例数 |
| `GPU_PER_NODE` | `gpu_per_node` | 8 | 单节点 GPU 数量 |

-----

