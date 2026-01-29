# -*- coding: utf-8 -*-
"""
DeepFinance (Tuner style) - main entry

This file follows the "tuner main.py" style:
- Define an async workflow function: workflow_func(task, model, auxiliary_models) -> WorkflowOutput
- Define an async judge function: judge_func(task, response, auxiliary_models) -> JudgeOutput
- Configure DatasetConfig / TunerModelConfig / AlgorithmConfig
- Call tune(...)

Notes
-----
- This version is Route-B oriented: workflow is a ReActAgent-based loop and will later be connected
  to AgentScope tools/toolkits. (Per your request, tools integration is intentionally left as TODO.)
- The current judge is a placeholder that returns 0 reward. You'll later replace it with your
  OpenJudge-based DeepFinance judge (ported to tuner signature).

Usage
-----
python main_deep_finance.py \\
  --dataset_path /path/to/dataset_deep_finance \\
  --model_path /path/to/base_model \\
  --split train
"""

from __future__ import annotations

import os

# Load environment variables from .env file
from dotenv import load_dotenv
_env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    ".env"
)
if os.path.exists(_env_path):
    load_dotenv(_env_path)
    print(f"Loaded environment variables from: {_env_path}")

import argparse
from typing import Dict, Any

from agentscope.tuner import (
    tune,
    DatasetConfig,
    WorkflowOutput,
    JudgeOutput,
    TunerModelConfig,
    AlgorithmConfig,
)
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg

from _deep_finance_judge import DeepFinanceJudgeEngine, DeepFinanceJudgeConfig
from prompt.tool_prompt_builder import get_tool_prompt_template




# Prompt template cache
_PROMPT_TEMPLATE_CACHE: str | None = None
_TOOL_PROMPT_CACHE: str | None = None


def _load_prompt_templates() -> tuple[str, str]:
    """Load and cache prompt templates."""
    global _PROMPT_TEMPLATE_CACHE, _TOOL_PROMPT_CACHE
    
    if _PROMPT_TEMPLATE_CACHE is None:
        prompt_file = os.path.join(os.path.dirname(__file__), "prompt", "finance_analyst_prompt.md")
        with open(prompt_file, "r", encoding="utf-8") as f:
            _PROMPT_TEMPLATE_CACHE = f.read()
    
    if _TOOL_PROMPT_CACHE is None:
        _TOOL_PROMPT_CACHE = get_tool_prompt_template()
    
    return _PROMPT_TEMPLATE_CACHE, _TOOL_PROMPT_CACHE


def _build_system_prompt() -> str:
    """Build system prompt with current date and tool list."""
    from datetime import datetime
    prompt_template, tool_prompt = _load_prompt_templates()
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = prompt_template.replace("{current_date}", current_date)
    system_prompt = system_prompt.replace("{tool_list}", tool_prompt)
    
    return system_prompt


# Process-local lazy judge engine (created on first judge call)
_DEEPFINANCE_JUDGE_ENGINE: DeepFinanceJudgeEngine | None = None

def _get_deepfinance_judge_engine() -> DeepFinanceJudgeEngine:
    global _DEEPFINANCE_JUDGE_ENGINE
    if _DEEPFINANCE_JUDGE_ENGINE is None:
        cfg = DeepFinanceJudgeConfig.from_env()
        _DEEPFINANCE_JUDGE_ENGINE = DeepFinanceJudgeEngine(cfg)
    return _DEEPFINANCE_JUDGE_ENGINE

def _extract_sys_and_user(task: Dict[str, Any]) -> tuple[str, str]:
    """
    Extract system prompt and user query for DeepFinance tasks.

    System prompt:
      - First tries to find from task["init_messages"] with role="system"
      - Falls back to loading from finance_analyst_prompt.md template

    User query:
      - First tries to find from task["init_messages"] with role="user"
      - Falls back to task["query"], task["question"], etc.
    """
    sys_prompt = ""
    user_query = ""

    init_messages = task.get("init_messages")
    if isinstance(init_messages, list):
        # Find the first system prompt and the last user query
        for m in init_messages:
            if isinstance(m, dict) and m.get("role") == "system" and not sys_prompt:
                sys_prompt = str(m.get("content", "") or "")
        for m in reversed(init_messages):
            if isinstance(m, dict) and m.get("role") == "user":
                user_query = str(m.get("content", "") or "")
                break

    if not sys_prompt:
        sys_prompt = str(task.get("system_prompt", "") or "")

    # Common query keys
    if not user_query:
        for k in ("query", "question", "main_query", "prompt"):
            if k in task and task[k]:
                user_query = str(task[k])
                break

    # Use finance_analyst_prompt.md template as system prompt (like ajet version)
    if not sys_prompt:
        sys_prompt = _build_system_prompt()

    return sys_prompt, user_query


async def run_deep_finance(
    task: Dict[str, Any],
    model: OpenAIChatModel,
    auxiliary_models: Dict[str, OpenAIChatModel] | None = None,
) -> WorkflowOutput:
    """
    DeepFinance workflow (Route B skeleton).
    TODO: attach AgentScope tools/toolkits to the ReActAgent.
    """
    assert (
        auxiliary_models is None or len(auxiliary_models) == 0
    ), "No auxiliary models are used in this workflow (for now)."

    sys_prompt, user_query = _extract_sys_and_user(task)

    agent = ReActAgent(
        name="deep_finance_react",
        sys_prompt=sys_prompt,
        model=model,
        enable_meta_tool=True,
        formatter=OpenAIChatFormatter(),
        # TODO(Route B): pass toolkit=... once tools are ready.
        # toolkit=your_toolkit,
    )

    response = await agent.reply(
        msg=Msg("user", user_query, role="user"),
    )

    # If you want to pass trajectory/stats to the judge later, prefer attaching to response.metadata.
    # Many AgentScope message classes allow arbitrary fields; if yours doesn't, you can instead
    # store runtime info in task["_runtime"] (dict) and read it in judge_func.
    #
    # Example (enable later):
    # response.metadata = response.metadata or {}
    # response.metadata["task_id"] = task.get("task_id")

    return WorkflowOutput(response=response)


async def deep_finance_judge(
    task: Dict[str, Any],
    response: Msg,
    auxiliary_models: Dict[str, OpenAIChatModel] | None = None,
) -> JudgeOutput:
    """
    DeepFinance judge (presentation_quality only).

    Reads best-effort trajectory from:
      - response.metadata["conversation_history"] (if provided by workflow)
    Falls back to minimal messages otherwise.

    Notes:
      - RM / grounding / tool-penalty are DISABLED in this phase.
    """
    _ = auxiliary_models  # not used

    engine = _get_deepfinance_judge_engine()
    reward, metrics = await engine.evaluate_one(task=task, response=response)
    return JudgeOutput(reward=reward, metrics=metrics)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DeepFinance training entry (tuner style).")

    # Dataset
    p.add_argument("--dataset_path", type=str, default="/mnt/data_cpfs/taoshuchang.tsc/deepresearch/astune_sample/agentscope-samples/tuner/deep_finance/data", help="Path to DeepFinance dataset directory. Defaults to ./data")
    p.add_argument("--split", type=str, default="train", help="Dataset split, e.g. train/validation/test.")
    p.add_argument("--total_epochs", type=int, default=4, help="Total number of epochs to run.")

    # Model (aligned with config.yaml)
    p.add_argument("--model_path", type=str, default="/mnt/data_cpfs/taoshuchang.tsc/models/Qwen3-8B", help="Base model path for tuning.")
    p.add_argument("--max_model_len", type=int, default=24576, help="Maximum token length for both input and output.")
    p.add_argument("--max_tokens", type=int, default=16384, help="Maximum tokens generated in response.")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--inference_engine_num", type=int, default=4, help="Number of vllm inference model instances.")
    p.add_argument("--tensor_parallel_size", type=int, default=1, help="Tensor parallel size for each model instance.")

    # Algorithm (aligned with config.yaml)
    p.add_argument("--algorithm_type", type=str, default="multi_step_grpo", help="Algorithm type for training.")
    p.add_argument("--group_size", type=int, default=8, help="Group size for GRPO algorithm (corresponds to repeat_times in config.yaml).")
    p.add_argument("--learning_rate", type=float, default=1e-6)
    p.add_argument("--batch_size", type=int, default=32, help="Batch size for each step.")

    return p


def main() -> None:
    from pathlib import Path
    config_path = Path(__file__).parent / "config.yaml"
    args = _build_arg_parser().parse_args()

    # Default dataset path: ./data (same as learn_to_ask style)
    dataset_path = args.dataset_path or os.path.join(os.path.dirname(__file__), "data")

    # ==================== DEBUG: Data Preview ====================
    print("\n" + "="*60)
    print("DEBUG: Data Loading Preview")
    print("="*60)
    
    # Preview dataset
    from datasets import load_dataset
    print(f"\n[Dataset Path]: {dataset_path}")
    print(f"[Split]: {args.split}")
    
    try:
        ds = load_dataset(dataset_path, split=args.split)
        print(f"[Total Samples]: {len(ds)}")
        
        if len(ds) > 0:
            sample = ds[0]
            print(f"\n[Sample 0 Keys]: {list(sample.keys())}")
            print(f"[Sample 0 task_id]: {sample.get('task_id', 'N/A')}")
            print(f"[Sample 0 query]: {sample.get('query', 'N/A')[:100]}..." if len(sample.get('query', '')) > 100 else f"[Sample 0 query]: {sample.get('query', 'N/A')}")
            print(f"[Sample 0 domain]: {sample.get('domain', 'N/A')}")
            print(f"[Sample 0 split]: {sample.get('split', 'N/A')}")
            
            # Test _extract_sys_and_user
            sys_prompt, user_query = _extract_sys_and_user(sample)
            print(f"\n[Extracted sys_prompt length]: {len(sys_prompt)} chars")
            print(f"[Extracted user_query]: {user_query[:100]}..." if len(user_query) > 100 else f"[Extracted user_query]: {user_query}")
            print(f"[sys_prompt preview (first 200 chars)]:\n{sys_prompt[:200]}...")
    except Exception as e:
        print(f"[ERROR loading dataset]: {e}")
    
    print("\n" + "="*60)
    print("DEBUG: End of Preview")
    print("="*60 + "\n")
    # ==================== END DEBUG ====================

    dataset = DatasetConfig(
        path=dataset_path,
        split=args.split,
        total_epochs=args.total_epochs,
    )

    tuner_model = TunerModelConfig(
        model_path=args.model_path,
        max_model_len=args.max_model_len,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        inference_engine_num=args.inference_engine_num,
        tensor_parallel_size=args.tensor_parallel_size,
    )

    algorithm = AlgorithmConfig(
        algorithm_type=args.algorithm_type,
        group_size=args.group_size,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
    )

    tune(
        workflow_func=run_deep_finance,
        judge_func=deep_finance_judge,
        train_dataset=dataset,
        model=tuner_model,
        algorithm=algorithm,        
        config_path=str(config_path),  # For cluster, explorer, trainer details
    )


if __name__ == "__main__":
    main()

"""
python main.py 

"""