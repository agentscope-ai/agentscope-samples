# -*- coding: utf-8 -*-
import os
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter

_DEFAULT_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "built_in_prompt",
)
PROMPT_DS_BASE_PATH = os.getenv(
    "PROMPT_DS_BASE_PATH",
    _DEFAULT_PROMPT_PATH,
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
