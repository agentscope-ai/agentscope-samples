#!/bin/bash
set -e  
#===============================================================================
# 1. 配置区域 - 用户只需修改这里
#===============================================================================
SUFFIX="newjudge"     # 实验后缀，影响所有日志和实验名称
PREFIX="ajet_newjudge"                        # 实验前缀，影响日志和实验所在文件夹

# OpenJudge 模型配置
OPENJUDGE_LLM='qwen-flash'        # OpenJudge 评分模型
RM_LLM='qwen-max'                 # RM Gallery 评分模型
JUDGE_CONCURRENCY=10

# 奖励权重配置
RM_WEIGHT=0.5
PRESENTATION_QUALITY_WEIGHT=0.25
GROUNDING_WEIGHT=0.25

# 训练参数配置
NUM_REPEAT=4        # group size，每个query rollout NUM_REPEAT次
TRAIN_BATCH_SIZE=32  # 训练batchsize
NUM_STEPS=6         # 每个样本step轮数
DEEPFINANCE_TOOL_RESULT_MAX_CHARS=10000

# Env Service URL 配置
ENV_SERVICE_URL="http://127.0.0.1:8080"  # 环境服务地址

# 主目录（需要更改）
export AJET_ROOT="/mnt/data_cpfs/taoshuchang.tsc/deepresearch/AgentJet_new"

NNODES=${WORLD_SIZE}

# 涉密的配置（API_KEY以及模型、数据位置）从.env读取
cd ${AJET_ROOT}
source .venv/bin/activate

# API密钥配置 - 从 .env 文件加载
ENV_FILE="${AJET_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "\033[32m已从 $ENV_FILE 加载环境变量\033[0m"
else
    echo -e "\033[31m警告: 找不到 .env 文件: $ENV_FILE\033[0m"
fi

#===============================================================================
# 2. 动态生成配置文件 (从yaml template生成yaml)
#===============================================================================
# 修改：配置文件生成路径，现在动态生成到 yaml 目录下
CONFIG_TEMPLATE="tutorial/example_deep_finance/deep_finance.yaml"
CONFIG_FILE="${AJET_ROOT}/tutorial/example_deep_finance/yaml/${SUFFIX}.yaml"
mkdir -p $(dirname ${CONFIG_FILE})

sed -e "s|{{SUFFIX}}|${SUFFIX}|g" \
    -e "s|{{PREFIX}}|${PREFIX}|g" \
    -e "s|{{MODEL_PATH}}|${MODEL_PATH}|g" \
    -e "s|{{NNODES}}|${NNODES}|g" \
    -e "s|{{RM_WEIGHT}}|${RM_WEIGHT}|g" \
    -e "s|{{PRESENTATION_QUALITY_WEIGHT}}|${PRESENTATION_QUALITY_WEIGHT}|g" \
    -e "s|{{GROUNDING_WEIGHT}}|${GROUNDING_WEIGHT}|g" \
    -e "s|{{OPENJUDGE_LLM}}|${OPENJUDGE_LLM}|g" \
    -e "s|{{RM_LLM}}|${RM_LLM}|g" \
    -e "s|{{JUDGE_CONCURRENCY}}|${JUDGE_CONCURRENCY}|g" \
    -e "s|{{NUM_REPEAT}}|${NUM_REPEAT}|g" \
    -e "s|{{NUM_STEPS}}|${NUM_STEPS}|g" \
    -e "s|{{TRAIN_BATCH_SIZE}}|${TRAIN_BATCH_SIZE}|g" \
    -e "s|{{TRAIN_DATA_PATH}}|${TRAIN_DATA_PATH}|g" \
    -e "s|{{VAL_DATA_PATH}}|${VAL_DATA_PATH}|g" \
    -e "s|{{TRAIN_REF_ANS_PATH}}|${TRAIN_REF_ANS_PATH}|g" \
    -e "s|{{VAL_REF_ANS_PATH}}|${VAL_REF_ANS_PATH}|g" \
    -e "s|{{CKPT_SAVE_PATH}}|${CKPT_SAVE_PATH}|g" \
    -e "s|{{ENV_SERVICE_URL}}|${ENV_SERVICE_URL}|g" \
    ${AJET_ROOT}/${CONFIG_TEMPLATE} > ${CONFIG_FILE}

echo "配置文件已生成: ${CONFIG_FILE}"
echo "参数确认: RM=${RM_WEIGHT}, PresentationQuality=${PRESENTATION_QUALITY_WEIGHT}, Grounding=${GROUNDING_WEIGHT}, OpenJudge=${OPENJUDGE_LLM}, RM_LLM=${RM_LLM}"

#===============================================================================
# 3. 环境配置
#===============================================================================
# MongoDB 缓存配置
CACHE_TYPE="mongodb"
MONGO_URI="mongodb://${ADDR}:27117/"
MONGO_DB_NAME="finworld_cache"
MONGO_COLLECTION_NAME="tool_cache"
export CACHE_TYPE MONGO_URI MONGO_DB_NAME MONGO_COLLECTION_NAME

# DeepFinance MCP 配置
DEEPFINANCE_MCP_CONFIG="${AJET_ROOT}/tutorial/example_deep_finance/config/mcp_finance_tool_generated.json"

# 动态生成 MCP 配置文件
mkdir -p $(dirname ${DEEPFINANCE_MCP_CONFIG})
cat > ${DEEPFINANCE_MCP_CONFIG} << EOF
{
    "mcpServers": {
      "flowllm": {
        "transport": "sse",
        "url": "http://${ADDR}:${MCP_PORT}/sse",
        "timeout": 600,
        "sse_read_timeout": 1200
      }
    }
}
EOF
export DEEPFINANCE_MCP_CONFIG  DEEPFINANCE_TOOL_RESULT_MAX_CHARS

# 其他服务配置
HF_ENDPOINT="https://hf-mirror.com"
ES_HOSTS="http://11.160.132.46:8200"
export HF_ENDPOINT ES_HOSTS 

# log 文件位置
CURRENT_TIME=$(date "+%Y%m%d_%H%M%S")
LOG_DIR="${AJET_ROOT}/logs/${PREFIX}"
MASTER_IP_FILE="${LOG_DIR}/master-ip_${SUFFIX}.log"
ENV_SERVICE_LOG="${LOG_DIR}/env_service_${SUFFIX}_${CURRENT_TIME}.log"
TRAIN_LOG="${LOG_DIR}/train_${SUFFIX}_${CURRENT_TIME}.log"
env_log_prefix="${SUFFIX}__${CURRENT_TIME}"
# 多机训练参数配置
GPUS_PER_NODE=8
EXPECTED_WORKERS=$WORLD_SIZE


#===============================================================================
# 4. 工具函数 以及 NCCL 配置（固定）
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

check_gpu_resources() {
    gpu_count=$(ray status 2>/dev/null | grep -A 10 "Resources" | grep "GPU" | awk '{print $1}' | cut -d'/' -f2)
    if [ -z "$gpu_count" ]; then echo 0; else printf "%.0f" "$gpu_count"; fi
}


export NCCL_TIMEOUT=1800
export NCCL_DEBUG=WARN
export NCCL_IB_TIMEOUT=23
export NCCL_ASYNC_ERROR_HANDLING=1

#===============================================================================
# 5. 工具envservice 环境变量
#===============================================================================

export PYTHONPATH="${AJET_ROOT}:${PYTHONPATH}"
export RAY_CLUSTER_MODE="multi_node"
export DEEPFINANCE_PATH="${ENV_SERVICE_ROOT}" # AgentJet 内部可能使用此路径
export DEEPFINANCE_SCRIPT="source /mnt/data/taoshuchang.tsc/anaconda3/etc/profile.d/conda.sh && conda activate finworld_1209  && cd ${ENV_SERVICE_ROOT} && DEEPFINANCE_TOOL_RESULT_MAX_CHARS=${DEEPFINANCE_TOOL_RESULT_MAX_CHARS} DEEPFINANCE_MCP_CONFIG=${DEEPFINANCE_MCP_CONFIG} CACHE_TYPE=${CACHE_TYPE} MONGO_URI=${MONGO_URI} MONGO_DB_NAME=${MONGO_DB_NAME} MONGO_COLLECTION_NAME=${MONGO_COLLECTION_NAME} python -m env_service.env_service --env finworld --portal 0.0.0.0 --port 8080"


#===============================================================================
# 6. 主流程
#===============================================================================
log "开始多机多卡训练: ${SUFFIX}"
log "节点数: ${NNODES}, 每节点GPU数: ${GPUS_PER_NODE}"
mkdir -p ${LOG_DIR}
mkdir -p $(dirname ${CONFIG_FILE})

#===============================================================================
#  6.1 Master 节点启动流程
#===============================================================================
if [[ $HOSTNAME == *"-master-"* ]]; then
    print_green "==> This is MASTER node: $HOSTNAME"

    #---------------------------------------------------------------------------
    # 6.1.1 清理和初始化 Ray
    #---------------------------------------------------------------------------
    rm -f "$MASTER_IP_FILE"
    ray stop --force || true
    sleep 3

    #---------------------------------------------------------------------------
    # 6.1.2 启动 Ray Head
    #---------------------------------------------------------------------------
    print_green "Starting Ray head node at $MASTER_ADDR"
    ray start --head --node-ip-address $MASTER_ADDR --num-gpus 8
    sleep 10
    echo $MASTER_ADDR > $MASTER_IP_FILE

    #---------------------------------------------------------------------------
    # 6.1.3 启动训练任务
    #---------------------------------------------------------------------------
    print_green "Starting training job..."
    source .venv/bin/activate
    export RAY_ADDRESS="ray://localhost:10001"

    print_green "==================================="
    print_green "Training Configuration"
    print_green "Total GPUs: $((NNODES * GPUS_PER_NODE))"
    print_green "Log: ${TRAIN_LOG}"
    print_green "==================================="

    # 启动训练任务（最核心）
    python ajet/launcher.py \
        --with-deepfinance \
        --conf ${CONFIG_FILE} \
        --backbone="verl" \
        --prefix=${env_log_prefix} \
        2>&1 | tee ${TRAIN_LOG}
    

#===============================================================================
# 6.2 Worker 节点启动流程
#===============================================================================
else
    print_green "==> This is WORKER node: $HOSTNAME"
    while [ ! -f $MASTER_IP_FILE ]; do sleep 5; done
    MASTER_ADDR=$(cat $MASTER_IP_FILE)
    ray stop || true
    ray start --address $MASTER_ADDR:6379 --num-gpus 8
    while true; do sleep 60; done
fi