#!/bin/bash
set -e
#===============================================================================
# DeepFinance Training Script (AgentScope Tuner) - 单机版
# 基于 OpenJudge FinanceCompositionEvaluator 的训练脚本
#===============================================================================

#===============================================================================
# 1. 配置区域 - 用户只需修改这里
#===============================================================================
export DEBUG_TOOL_RESULT=1
export DEBUG_REWARD=1


SUFFIX="deepfinance_single"     # 实验后缀，影响日志和实验名称
PREFIX="agentscopetuner_sing"             # 实验前缀，影响日志文件夹
PROJECT_NAME="AgentScope-DeepFinance" # 项目名称


# OpenJudge 模型配置
OPENJUDGE_LLM='qwen-flash'            # OpenJudge 评分模型
FINANCE_JUDGE_LLM='qwen-max'
JUDGE_CONCURRENCY=6

# 奖励权重配置
RM_WEIGHT=0.5                         # Finance 评估权重
PRESENTATION_QUALITY_WEIGHT=0.2       # 报告呈现质量
GROUNDING_WEIGHT=0.1                  # 引用规范性评估
AUDIT_WEIGHT=0.2                      # 引用逻辑审计

# 单机 GPU 配置
GPU_PER_NODE=8                        # 本机 GPU 数量

# 训练参数配置
GROUP_SIZE=4                          # repeat_times，每个 query rollout 次数
BATCH_SIZE=64                         # 每步样本数
TRAIN_BATCH_SIZE=64                   # trainer batch size
TOTAL_EPOCHS=300                      # 总 epoch 数
MAX_ENV_STEPS=10                      # 每个样本step轮数
MAX_MODEL_LEN=40960                   # 最大模型长度（模型支持的最大值）
MAX_RESPONSE_TOKENS=8000              # 最大响应 token 数

# GPU 分配策略：一半用于推理(explorer)，一半用于训练(trainer)
TOTAL_GPU=${GPU_PER_NODE}
HALF_GPU=$((TOTAL_GPU / 2))

# 自适应计算 tensor_parallel_size 和 engine_num
if [ $HALF_GPU -ge 8 ]; then
    TENSOR_PARALLEL_SIZE=8
else
    TENSOR_PARALLEL_SIZE=$HALF_GPU
fi

ENGINE_NUM=$((HALF_GPU / TENSOR_PARALLEL_SIZE))
EXPLORER_GPU=$((ENGINE_NUM * TENSOR_PARALLEL_SIZE))
TRAINER_GPU=$((TOTAL_GPU - EXPLORER_GPU))

RUNNER_PER_MODEL=8                    # 每模型并行 runner 数
MAX_TIMEOUT=1200                      # 单次 rollout 超时秒数
GPU_MEMORY_UTILIZATION=0.8            # GPU 内存利用率

# Trainer 配置
SAVE_INTERVAL=10                      # checkpoint 保存间隔
SEQ_PARALLEL_SIZE=${TRAINER_GPU}      # 序列并行度，必须 ≤ TRAINER_GPU

# MCP 配置
FINANCE_MCP_TRANSPORT="sse"
FINANCE_MCP_INIT_JITTER_MAX_S=15
FINANCE_MCP_INIT_MAX_RETRIES=5

#===============================================================================
# 2. 路径配置
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# 从 .env 加载 API Keys、模型路径、数据路径等
ENV_FILE="${REPO_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "\033[32m已从 $ENV_FILE 加载环境变量\033[0m"
else
    echo -e "\033[31m错误: 找不到 .env 文件: $ENV_FILE\033[0m"
    exit 1
fi

# 激活 conda 环境
CONDA_ENV=${CONDA_ENV:-tune_example}
if [ -n "${CONDA_PATH}" ] && [ -f "${CONDA_PATH}" ]; then
    source "${CONDA_PATH}"
    conda activate "${CONDA_ENV}"
    echo -e "\033[32m已激活 conda 环境: ${CONDA_ENV}\033[0m"
    
    export PATH="${CONDA_PREFIX}/bin:$PATH"
    export PYTHONPATH="${CONDA_PREFIX}/lib/python3.11/site-packages:${PYTHONPATH:-}"
    echo -e "\033[32m已设置 PATH: ${CONDA_PREFIX}/bin\033[0m"
else
    echo -e "\033[31m错误: 找不到 conda.sh: ${CONDA_PATH}\033[0m"
    echo -e "\033[31m请在 .env 文件中配置 CONDA_PATH\033[0m"
    exit 1
fi

# 日志和配置文件路径
CURRENT_TIME=$(date "+%Y%m%d_%H%M%S")
LOG_DIR="${SCRIPT_DIR}/logs/${PREFIX}"
TRAIN_LOG="${LOG_DIR}/train_${SUFFIX}_${CURRENT_TIME}.log"

# 配置文件路径
CONFIG_TEMPLATE="${SCRIPT_DIR}/config_template.yaml"
CONFIG_FILE="${SCRIPT_DIR}/yaml/${SUFFIX}.yaml"
CHECKPOINT_DIR="${SCRIPT_DIR}/checkpoints/${SUFFIX}"
DATA_PATH="${SCRIPT_DIR}/data"
DATA_SPLIT="train"

# 测试集评估配置
EVAL_INTERVAL=10                           # 每 10 步评估一次测试集

#===============================================================================
# 3. 动态生成配置文件
#===============================================================================
mkdir -p "$(dirname "${CONFIG_FILE}")"
mkdir -p "${CHECKPOINT_DIR}"
mkdir -p "${LOG_DIR}"

if [ ! -f "${CONFIG_TEMPLATE}" ]; then
    echo -e "\033[31m错误: 配置模板不存在: ${CONFIG_TEMPLATE}\033[0m"
    exit 1
fi

# 单机模式固定 NODE_NUM=1
NODE_NUM=1

sed -e "s|{{PROJECT_NAME}}|${PROJECT_NAME}|g" \
    -e "s|{{EXPERIMENT_NAME}}|${SUFFIX}|g" \
    -e "s|{{CHECKPOINT_DIR}}|${CHECKPOINT_DIR}|g" \
    -e "s|{{MODEL_PATH}}|${MODEL_PATH}|g" \
    -e "s|{{NODE_NUM}}|${NODE_NUM}|g" \
    -e "s|{{GPU_PER_NODE}}|${GPU_PER_NODE}|g" \
    -e "s|{{GROUP_SIZE}}|${GROUP_SIZE}|g" \
    -e "s|{{BATCH_SIZE}}|${BATCH_SIZE}|g" \
    -e "s|{{TRAIN_BATCH_SIZE}}|${TRAIN_BATCH_SIZE}|g" \
    -e "s|{{TOTAL_EPOCHS}}|${TOTAL_EPOCHS}|g" \
    -e "s|{{MAX_MODEL_LEN}}|${MAX_MODEL_LEN}|g" \
    -e "s|{{MAX_ENV_STEPS}}|${MAX_ENV_STEPS}|g" \
    -e "s|{{MAX_RESPONSE_TOKENS}}|${MAX_RESPONSE_TOKENS}|g" \
    -e "s|{{DATA_PATH}}|${DATA_PATH}|g" \
    -e "s|{{DATA_SPLIT}}|${DATA_SPLIT}|g" \
    -e "s|{{VAL_DATA_PATH}}|${VAL_DATA_PATH}|g" \
    -e "s|{{EVAL_INTERVAL}}|${EVAL_INTERVAL}|g" \
    -e "s|{{ENGINE_NUM}}|${ENGINE_NUM}|g" \
    -e "s|{{TENSOR_PARALLEL_SIZE}}|${TENSOR_PARALLEL_SIZE}|g" \
    -e "s|{{RUNNER_PER_MODEL}}|${RUNNER_PER_MODEL}|g" \
    -e "s|{{MAX_TIMEOUT}}|${MAX_TIMEOUT}|g" \
    -e "s|{{GPU_MEMORY_UTILIZATION}}|${GPU_MEMORY_UTILIZATION}|g" \
    -e "s|{{SAVE_INTERVAL}}|${SAVE_INTERVAL}|g" \
    -e "s|{{SEQ_PARALLEL_SIZE}}|${SEQ_PARALLEL_SIZE}|g" \
    -e "s|{{OPENAI_API_KEY}}|${OPENAI_API_KEY}|g" \
    -e "s|{{OPENAI_BASE_URL}}|${OPENAI_BASE_URL}|g" \
    -e "s|{{RM_BASE_URL}}|${RM_BASE_URL}|g" \
    -e "s|{{RM_API_KEY}}|${RM_API_KEY}|g" \
    -e "s|{{OPENJUDGE_BASE_URL}}|${OPENJUDGE_BASE_URL}|g" \
    -e "s|{{OPENJUDGE_API_KEY}}|${OPENJUDGE_API_KEY}|g" \
    -e "s|{{OPENJUDGE_LLM}}|${OPENJUDGE_LLM}|g" \
    -e "s|{{OPENJUDGE_CONCURRENCY}}|${OPENJUDGE_CONCURRENCY}|g" \
    -e "s|{{FINANCE_MCP_URL}}|${FINANCE_MCP_URL}|g" \
    -e "s|{{FINANCE_MCP_TRANSPORT}}|${FINANCE_MCP_TRANSPORT}|g" \
    -e "s|{{FINANCE_MCP_INIT_JITTER_MAX_S}}|${FINANCE_MCP_INIT_JITTER_MAX_S}|g" \
    -e "s|{{FINANCE_MCP_INIT_MAX_RETRIES}}|${FINANCE_MCP_INIT_MAX_RETRIES}|g" \
    -e "s|{{TRAJECTORY_SAVE_DIR}}|${TRAJECTORY_SAVE_DIR}|g" \
    -e "s|{{TRAIN_REF_ANS_PATH}}|${TRAIN_REF_ANS_PATH}|g" \
    -e "s|{{VAL_REF_ANS_PATH}}|${VAL_REF_ANS_PATH}|g" \
    "${CONFIG_TEMPLATE}" > "${CONFIG_FILE}"

echo "配置文件已生成: ${CONFIG_FILE}"

#===============================================================================
# 4. 导出环境变量（供 Judge 和 MCP 使用）
#===============================================================================
# Judge 配置
export OPENJUDGE_LLM
export FINANCE_JUDGE_LLM
export OPENJUDGE_CONCURRENCY="${JUDGE_CONCURRENCY}"
export FINANCE_RM_WEIGHT="${RM_WEIGHT}"
export JUDGE_PRESENTATION_QUALITY_WEIGHT="${PRESENTATION_QUALITY_WEIGHT}"
export JUDGE_GROUNDING_WEIGHT="${GROUNDING_WEIGHT}"
export JUDGE_AUDIT_WEIGHT="${AUDIT_WEIGHT}"

# Judge 参考答案路径（从 .env 映射）
export JUDGE_TRAIN_REF_ANS_PATH="${TRAIN_REF_ANS_PATH}"
export JUDGE_VAL_REF_ANS_PATH="${VAL_REF_ANS_PATH}"
export TRAJECTORY_SAVE_DIR="${TRAJECTORY_SAVE_DIR}/${SUFFIX}"

# MCP 配置
export FINANCE_MCP_TRANSPORT
export FINANCE_MCP_INIT_JITTER_MAX_S
export FINANCE_MCP_INIT_MAX_RETRIES

# Wandb 配置
export WANDB_API_KEY="local-2b9fa8923648c12f05be05815e48e5f5c2205a9c"
export WANDB_BASE_URL="http://8.130.26.137:8083"
export WANDB_PROJECT="tuner"
export WANDB_NAME="${SUFFIX}"

# NCCL 配置（调试模式）
export NCCL_TIMEOUT=1800
export NCCL_DEBUG=WARN
export NCCL_IB_TIMEOUT=23
export NCCL_ASYNC_ERROR_HANDLING=1

#===============================================================================
# 5. 工具函数
#===============================================================================
print_green() {
    echo -e "\033[32m$1\033[0m"
}

log() {
    echo -e "\033[0;32m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m \033[0;34m[INFO]\033[0m $1"
}

#===============================================================================
# 6. 主流程（单机模式）
#===============================================================================
log "单机训练模式: ${SUFFIX}"
log "GPU 数量: ${GPU_PER_NODE}"

# 【重要】设置 Ray 运行时环境变量
export RAY_RUNTIME_ENV_CONDA="${CONDA_ENV}"
PYTHON_PATH=$(which python)
print_green "当前 Python 路径: ${PYTHON_PATH}"
print_green "CONDA_PREFIX: ${CONDA_PREFIX}"

echo "=== 配置确认 ==="
echo "  MODEL_PATH: ${MODEL_PATH}"
echo "  FINANCE_MCP_URL: ${FINANCE_MCP_URL}"
echo "  OpenJudge LLM: ${OPENJUDGE_LLM}"
echo "  Finance Judge LLM: ${FINANCE_JUDGE_LLM}"
echo "  RM Weight: ${RM_WEIGHT}"
echo "  Presentation Quality: ${PRESENTATION_QUALITY_WEIGHT}"
echo "  Grounding: ${GROUNDING_WEIGHT}"
echo "  Audit: ${AUDIT_WEIGHT}"
echo "  Config File: ${CONFIG_FILE}"
echo "  测试集路径: ${VAL_DATA_PATH}"
echo "  测试集评估间隔: 每 ${EVAL_INTERVAL} 步"
echo ""
echo "=== GPU 分配 ==="
echo "  总 GPU 数: ${TOTAL_GPU}"
echo "  Explorer GPU: ${EXPLORER_GPU} (engine_num=${ENGINE_NUM}, tensor_parallel_size=${TENSOR_PARALLEL_SIZE})"
echo "  Trainer GPU: ${TRAINER_GPU}"

# 清理并启动 Ray
ray stop --force 2>/dev/null || true
sleep 3

print_green "Starting Ray single-node cluster..."
ray start --head --num-gpus ${GPU_PER_NODE}
sleep 5

print_green "==================================="
print_green "Training Configuration"
print_green "GPU Count: ${GPU_PER_NODE}"
print_green "Log: ${TRAIN_LOG}"
print_green "==================================="

cd "${SCRIPT_DIR}"
python main.py --config_path="${CONFIG_FILE}" 2>&1 | tee "${TRAIN_LOG}"
