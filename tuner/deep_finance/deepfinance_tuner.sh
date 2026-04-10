#!/bin/bash
set -e
#===============================================================================
# DeepFinance Training Script (AgentScope Tuner)
# Training script based on OpenJudge FinanceCompositionEvaluator
#===============================================================================

#===============================================================================
# 1. Configuration - Only modify this section
#===============================================================================
export DEBUG_TOOL_RESULT=1
export DEBUG_REWARD=1

#===============================================================================
# Ray debug mode configuration
#===============================================================================

SUFFIX="deepfinance"     # Experiment suffix, affects logs and experiment name
PREFIX="agentscopetuner"             # Experiment prefix, affects log directory
PROJECT_NAME="AgentScope-DeepFinance" # Project name

# OpenJudge model configuration
OPENJUDGE_LLM='qwen-flash'            # OpenJudge scoring model
FINANCE_JUDGE_LLM='qwen-max'
JUDGE_CONCURRENCY=6

# Reward weight configuration
RM_WEIGHT=0.5                         # Finance evaluation weight
PRESENTATION_QUALITY_WEIGHT=0.2       # Report presentation quality
GROUNDING_WEIGHT=0.1                  # Citation compliance evaluation
AUDIT_WEIGHT=0.2                      # Citation logic audit

# Cluster configuration (from environment variables)
NODE_NUM=${WORLD_SIZE:-1}             # Number of nodes, from WORLD_SIZE env var, default 1
GPU_PER_NODE=8                        # GPUs per node

# Training parameter configuration
GROUP_SIZE=4                          # repeat_times, rollout count per query
BATCH_SIZE=64                         # Samples per step
TRAIN_BATCH_SIZE=64                   # Trainer batch size (must be divisible by trainer_gpu_num)
TOTAL_EPOCHS=300                        # Total epochs
MAX_ENV_STEPS=10                      # Max interaction steps per sample
MAX_MODEL_LEN=40000                   # Max model length
MAX_RESPONSE_TOKENS=8000              # Max response tokens

# GPU allocation strategy: half for inference (explorer), half for training (trainer)
# Ensure trainer_gpu_num is divisible by gpu_per_node (when trainer_gpu > gpu_per_node)
TOTAL_GPU=$((NODE_NUM * GPU_PER_NODE))
HALF_GPU=$((TOTAL_GPU / 2))

# Adaptive computation of tensor_parallel_size and engine_num
# tensor_parallel_size max is 8, but cannot exceed half_gpu
if [ $HALF_GPU -ge 8 ]; then
    TENSOR_PARALLEL_SIZE=8
else
    TENSOR_PARALLEL_SIZE=$HALF_GPU
fi

# engine_num = half_gpu / tensor_parallel_size
ENGINE_NUM=$((HALF_GPU / TENSOR_PARALLEL_SIZE))

# Validate allocation correctness
EXPLORER_GPU=$((ENGINE_NUM * TENSOR_PARALLEL_SIZE))
TRAINER_GPU=$((TOTAL_GPU - EXPLORER_GPU))
# Only when trainer_gpu > gpu_per_node, ensure divisibility
# Because when trainer_gpu <= gpu_per_node, trainer only needs 1 node
if [ $TRAINER_GPU -gt $GPU_PER_NODE ]; then
    if [ $((TRAINER_GPU % GPU_PER_NODE)) -ne 0 ]; then
        # Reduce engine_num until trainer_gpu is divisible
        while [ $ENGINE_NUM -gt 0 ] && [ $((TRAINER_GPU % GPU_PER_NODE)) -ne 0 ]; do
            ENGINE_NUM=$((ENGINE_NUM - 1))
            EXPLORER_GPU=$((ENGINE_NUM * TENSOR_PARALLEL_SIZE))
            TRAINER_GPU=$((TOTAL_GPU - EXPLORER_GPU))
        done
    fi
fi

RUNNER_PER_MODEL=4                    # Parallel runners per model (reduced to lower CPU memory pressure)
MAX_TIMEOUT=1200                      # Single rollout timeout in seconds
GPU_MEMORY_UTILIZATION=0.8            # GPU memory utilization
export RAY_CGRAPH_get_timeout=1800  # 30 minutes

# Trainer configuration
SAVE_INTERVAL=10                      # Checkpoint save interval
SEQ_PARALLEL_SIZE=8                   # Sequence parallelism degree

# MCP configuration
FINANCE_MCP_TRANSPORT="sse"
FINANCE_MCP_INIT_JITTER_MAX_S=15
FINANCE_MCP_INIT_MAX_RETRIES=5

#===============================================================================
# 2. Path configuration
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# Load API Keys, model paths, data paths, etc. from .env
ENV_FILE="${REPO_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "\033[32mLoaded environment variables from $ENV_FILE\033[0m"
else
    echo -e "\033[31mError: .env file not found: $ENV_FILE\033[0m"
    exit 1
fi

# Activate conda environment
CONDA_ENV=${CONDA_ENV:-tune_example}
if [ -n "${CONDA_PATH}" ] && [ -f "${CONDA_PATH}" ]; then
    source "${CONDA_PATH}"
    conda activate "${CONDA_ENV}"
    echo -e "\033[32mActivated conda environment: ${CONDA_ENV}\033[0m"

    # [Important] Ensure Ray child processes use the correct Python interpreter
    # Add conda env bin dir to PATH and export
    export PATH="${CONDA_PREFIX}/bin:$PATH"
    export PYTHONPATH="${CONDA_PREFIX}/lib/python3.11/site-packages:${PYTHONPATH:-}"
    echo -e "\033[32mPATH set: ${CONDA_PREFIX}/bin\033[0m"
else
    echo -e "\033[31mError: conda.sh not found: ${CONDA_PATH}\033[0m"
    echo -e "\033[31mPlease configure CONDA_PATH in .env file\033[0m"
    exit 1
fi

# Log and config file paths
CURRENT_TIME=$(date "+%Y%m%d_%H%M%S")
LOG_DIR="${SCRIPT_DIR}/logs/${PREFIX}"
MASTER_IP_FILE="${LOG_DIR}/master_ip_${SUFFIX}.txt"
TRAIN_LOG="${LOG_DIR}/train_${SUFFIX}_${CURRENT_TIME}.log"

# Config file paths
CONFIG_TEMPLATE="${SCRIPT_DIR}/config_template.yaml"
CONFIG_FILE="${SCRIPT_DIR}/yaml/${SUFFIX}.yaml"
CHECKPOINT_DIR="${SCRIPT_DIR}/checkpoints/${SUFFIX}"
DATA_PATH="${SCRIPT_DIR}/data"
DATA_SPLIT="train"

# Test set evaluation configuration
EVAL_INTERVAL=10                           # Evaluate test set every 10 steps

#===============================================================================
# 3. Dynamically generate config file
#===============================================================================
mkdir -p "$(dirname "${CONFIG_FILE}")"
mkdir -p "${CHECKPOINT_DIR}"
mkdir -p "${LOG_DIR}"

if [ ! -f "${CONFIG_TEMPLATE}" ]; then
    echo -e "\033[31mError: Config template not found: ${CONFIG_TEMPLATE}\033[0m"
    exit 1
fi

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

echo "Config file generated: ${CONFIG_FILE}"

#===============================================================================
# 4. Export environment variables (for Judge and MCP)
#===============================================================================
# Judge configuration
export OPENJUDGE_LLM
export FINANCE_JUDGE_LLM
export OPENJUDGE_CONCURRENCY="${JUDGE_CONCURRENCY}"
export FINANCE_RM_WEIGHT="${RM_WEIGHT}"
export JUDGE_PRESENTATION_QUALITY_WEIGHT="${PRESENTATION_QUALITY_WEIGHT}"
export JUDGE_GROUNDING_WEIGHT="${GROUNDING_WEIGHT}"
export JUDGE_AUDIT_WEIGHT="${AUDIT_WEIGHT}"

# Judge reference answer paths (mapped from .env)
export JUDGE_TRAIN_REF_ANS_PATH="${TRAIN_REF_ANS_PATH}"
export JUDGE_VAL_REF_ANS_PATH="${VAL_REF_ANS_PATH}"
export TRAJECTORY_SAVE_DIR="${TRAJECTORY_SAVE_DIR}/${SUFFIX}"

# MCP configuration
export FINANCE_MCP_TRANSPORT
export FINANCE_MCP_INIT_JITTER_MAX_S
export FINANCE_MCP_INIT_MAX_RETRIES

# Wandb configuration
export WANDB_API_KEY="local-2b9fa8923648c12f05be05815e48e5f5c2205a9c"
export WANDB_BASE_URL="http://8.130.26.137:8083"
export WANDB_PROJECT="tuner"
export WANDB_NAME="${SUFFIX}"

# NCCL configuration (debug mode)
export NCCL_TIMEOUT=1800
export NCCL_DEBUG=WARN                     # Only show warnings and errors
# export NCCL_DEBUG_SUBSYS=ALL             # Show all subsystem logs (disabled)
export NCCL_IB_TIMEOUT=23
export NCCL_ASYNC_ERROR_HANDLING=1

#===============================================================================
# 5. Utility functions
#===============================================================================
print_green() {
    echo -e "\033[32m$1\033[0m"
}

log() {
    echo -e "\033[0;32m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m \033[0;34m[INFO]\033[0m $1"
}

check_workers() {
    local status_output=$(ray status 2>/dev/null)
    if [ -z "$status_output" ]; then echo 0; return; fi
    local node_count=$(echo "$status_output" | grep -E "^[[:space:]]*1[[:space:]]+node_" | wc -l)
    if [ "$node_count" -gt 0 ]; then echo $node_count; return; fi
    echo $(echo "$status_output" | grep -o "node_[0-9a-f]\+" | sort -u | wc -l)
}

#===============================================================================
# 6. Main flow
#===============================================================================
log "Starting training: ${SUFFIX}"
log "Nodes: ${NODE_NUM}, GPUs per node: ${GPU_PER_NODE}"

# Check MASTER_ADDR for multi-node training
if [ "${NODE_NUM}" -gt 1 ] && [ -z "${MASTER_ADDR}" ]; then
    echo -e "\033[31mError: Multi-node training requires MASTER_ADDR environment variable\033[0m"
    exit 1
fi

# [Important] Set Ray runtime env vars to ensure all workers use correct Python
export RAY_RUNTIME_ENV_CONDA="${CONDA_ENV}"
# Explicitly specify Python interpreter path to prevent Ray workers from using system default
PYTHON_PATH=$(which python)
print_green "Current Python path: ${PYTHON_PATH}"
print_green "CONDA_PREFIX: ${CONDA_PREFIX}"

echo "=== Configuration Summary ==="
echo "  MODEL_PATH: ${MODEL_PATH}"
echo "  FINANCE_MCP_URL: ${FINANCE_MCP_URL}"
echo "  OpenJudge LLM: ${OPENJUDGE_LLM}"
echo "  Finance Judge LLM: ${FINANCE_JUDGE_LLM}"
echo "  RM Weight: ${RM_WEIGHT}"
echo "  Presentation Quality: ${PRESENTATION_QUALITY_WEIGHT}"
echo "  Grounding: ${GROUNDING_WEIGHT}"
echo "  Audit: ${AUDIT_WEIGHT}"
echo "  Config File: ${CONFIG_FILE}"
echo "  Test set path: ${VAL_DATA_PATH}"
echo "  Test set eval interval: every ${EVAL_INTERVAL} steps"
echo ""
echo "=== GPU Allocation ==="
echo "  Total GPUs: ${TOTAL_GPU}"
echo "  Explorer GPU: ${EXPLORER_GPU} (engine_num=${ENGINE_NUM}, tensor_parallel_size=${TENSOR_PARALLEL_SIZE})"
echo "  Trainer GPU: ${TRAINER_GPU} (must be divisible by ${GPU_PER_NODE}: $((TRAINER_GPU % GPU_PER_NODE)) == 0 ✓)"

#===============================================================================
# 6.1 Master node startup
#===============================================================================
if [ "${NODE_NUM}" -gt 1 ]; then
    if [[ "$HOSTNAME" == *"-master-"* ]]; then
        print_green "==> This is MASTER node: $HOSTNAME"

        # Clean up and initialize Ray
        rm -f "${MASTER_IP_FILE}"
        ray stop --force || true
        sleep 3

        # Start Ray Head
        print_green "Starting Ray head node at ${MASTER_ADDR}"
        ray start --head --node-ip-address "${MASTER_ADDR}" --num-gpus ${GPU_PER_NODE}
        sleep 10
        echo "${MASTER_ADDR}" > "${MASTER_IP_FILE}"

        # Wait for worker nodes
        log "Waiting for worker nodes to join..."
        while true; do
            CURRENT_NODES=$(check_workers)
            if [ "${CURRENT_NODES}" -ge "${NODE_NUM}" ]; then
                print_green "All nodes joined (${CURRENT_NODES}/${NODE_NUM})"
                break
            fi
            log "Current nodes: ${CURRENT_NODES}/${NODE_NUM}"
            sleep 10
        done

        # Start training
        print_green "==================================="
        print_green "Training Configuration"
        print_green "Total GPUs: $((NODE_NUM * GPU_PER_NODE))"
        print_green "Log: ${TRAIN_LOG}"
        print_green "==================================="

        cd "${SCRIPT_DIR}"
        python main.py --config_path="${CONFIG_FILE}" 2>&1 | tee "${TRAIN_LOG}"

    #===============================================================================
    # 6.2 Worker node startup
    #===============================================================================
    else
        print_green "==> This is WORKER node: $HOSTNAME"
        print_green "[Worker] Using Python: $(which python)"
        print_green "[Worker] CONDA_PREFIX: ${CONDA_PREFIX}"

        while [ ! -f "${MASTER_IP_FILE}" ]; do sleep 5; done
        sleep 3  # Wait for filesystem sync
        # Flush distributed filesystem cache to avoid stale file handle
        ls -la "$(dirname "${MASTER_IP_FILE}")" > /dev/null 2>&1 || true
        MASTER_ADDR=$(cat "${MASTER_IP_FILE}")
        ray stop || true
        ray start --address "${MASTER_ADDR}:6379" --num-gpus ${GPU_PER_NODE}
        while true; do sleep 60; done
    fi

#===============================================================================
# 6.3 Single-node mode
#===============================================================================
else
    log "Single-node training mode"
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
fi
