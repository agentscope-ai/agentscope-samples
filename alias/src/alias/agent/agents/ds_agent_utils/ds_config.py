# -*- coding: utf-8 -*-
import os
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter

PROMPT_DS_BASE_PATH = os.getenv(
    "PROMPT_DS_BASE_PATH",
    "alias/agent/agents/ds_agent_utils/built_in_prompt",
)

VL_MODEL_NAME = os.getenv("VISION_MODEL", "qwen-vl-max")
MODEL_CONFIG_NAME = os.getenv("MODEL", "qwen3-max")

MODEL_FORMATTER_MAPPING = {
    "qwen3-max": [
        DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen3-max-preview",
            stream=True,
        ),
        DashScopeChatFormatter(),
    ],
    "qwen-vl-max": [
        DashScopeChatModel(
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen-vl-max-latest",
            stream=True,
        ),
        DashScopeChatFormatter(),
    ],
}
