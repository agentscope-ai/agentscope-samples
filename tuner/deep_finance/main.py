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
import asyncio
import random
import logging

import argparse
from typing import Dict, Any, Optional

from agentscope.tuner import (
    tune,
    WorkflowOutput,
)
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.tool import Toolkit
from agentscope.mcp import HttpStatelessClient
from agentscope.message import Msg

from deep_finance_judge import deep_finance_judge
from metric_helper.tool_metric_helper import (
    extract_tool_stats_from_agent,
    compute_single_tool_metrics,
)
from prompt.tool_prompt_builder import get_tool_prompt_template




# MCP (finance-mcp) Toolkit cache (process-local)
_FINANCE_MCP_TOOLKIT: Optional[Toolkit] = None
_FINANCE_MCP_TOOLKIT_LOCK: asyncio.Lock = asyncio.Lock()


async def get_finance_mcp_toolkit() -> Toolkit:  # pylint: disable=too-many-statements
    """Create (once per process) and return a Toolkit backed by the finance-mcp MCP server."""
    global _FINANCE_MCP_TOOLKIT
    
    # Setup debug logger
    logger = logging.getLogger("deep_finance.finance_mcp")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] [PID:%(process)d] %(name)s: %(message)s'
        ))
        logger.addHandler(handler)
    
    pid = os.getpid()
    logger.debug(
        "[PID:%d] get_finance_mcp_toolkit called,"
        " cached=%s", pid, _FINANCE_MCP_TOOLKIT is not None,
    )
    
    if _FINANCE_MCP_TOOLKIT is not None:
        logger.debug("[PID:%d] Returning cached toolkit", pid)
        return _FINANCE_MCP_TOOLKIT

    async with _FINANCE_MCP_TOOLKIT_LOCK:
        if _FINANCE_MCP_TOOLKIT is not None:
            logger.debug("[PID:%d] Returning cached toolkit (after lock)", pid)
            return _FINANCE_MCP_TOOLKIT

        # Jitter to avoid thundering-herd when many workers start together.
        jitter_max = float(os.getenv("FINANCE_MCP_INIT_JITTER_MAX_S", "15"))
        jitter_sleep = random.uniform(0, jitter_max) if jitter_max > 0 else 0
        logger.debug("[PID:%d] Jitter sleep: %.2fs (max=%.1fs)", pid, jitter_sleep, jitter_max)
        if jitter_sleep > 0:
            await asyncio.sleep(jitter_sleep)

        transport = os.getenv("FINANCE_MCP_TRANSPORT", "sse").strip() or "sse"
        base_url = os.getenv("FINANCE_MCP_URL", "http://10.56.0.109:8040/sse")
        url = base_url

        timeout_s = 100
        sse_read_timeout_s = 1000
        max_retries = int(os.getenv("FINANCE_MCP_INIT_MAX_RETRIES", "5"))

        logger.info(
            "[PID:%d] MCP config: transport=%s, url=%s,"
            " timeout=%d, sse_read_timeout=%d,"
            " max_retries=%d",
            pid, transport, url, timeout_s,
            sse_read_timeout_s, max_retries,
        )

        headers: Dict[str, str] = {}
        auth_token = os.getenv("FINANCE_MCP_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        toolkit = Toolkit()

        # Create tool group before registering MCP client (required for non-"basic" group names)
        toolkit.create_tool_group(
            group_name="finance-mcp",
            description=(
                "Finance MCP tools for stock analysis,"
                " financial data retrieval, and market research"
            ),
            active=True,  # Make it active so tools are included in JSON schema
        )
        logger.debug("[PID:%d] Created tool group 'finance-mcp'", pid)

        # Construct client with best-effort compatibility across AgentScope versions.
        client_kwargs: Dict[str, Any] = {
            "name": "finance-mcp",
            "transport": transport,
            "url": url,
        }
        if headers:
            client_kwargs["headers"] = headers

        logger.debug("[PID:%d] Creating HttpStatelessClient with kwargs: %s", pid, client_kwargs)
        try:
            client = HttpStatelessClient(
                **client_kwargs,
                timeout=timeout_s,
                sse_read_timeout=sse_read_timeout_s,
            )
            logger.debug(
                "[PID:%d] HttpStatelessClient created"
                " successfully (with timeout args)", pid,
            )
        except TypeError as te:
            logger.warning(
                "[PID:%d] HttpStatelessClient TypeError"
                " (fallback without timeout): %s", pid, te,
            )
            client = HttpStatelessClient(**client_kwargs)
            logger.debug(
                "[PID:%d] HttpStatelessClient created"
                " successfully (without timeout args)", pid,
            )

        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    "[PID:%d] Attempt %d/%d: Calling"
                    " client.list_tools()...",
                    pid, attempt, max_retries,
                )
                
                # First test list_tools directly
                tools_list = await client.list_tools()
                logger.info("[PID:%d] Attempt %d: list_tools returned %d tools: %s",
                            pid, attempt, len(tools_list), [t.name for t in tools_list])
                
                if len(tools_list) == 0:
                    raise ValueError(
                        "list_tools returned empty list"
                        " - MCP server may not have tools registered"
                    )
                
                logger.debug(
                    "[PID:%d] Attempt %d: Calling"
                    " toolkit.register_mcp_client()...",
                    pid, attempt,
                )
                await toolkit.register_mcp_client(client, group_name="finance-mcp")
                
                _FINANCE_MCP_TOOLKIT = toolkit
                schemas = toolkit.get_json_schemas()
                logger.info("[PID:%d] finance-mcp toolkit ready: transport=%s url=%s tools=%d",
                            pid, transport, url, len(schemas))
                logger.debug(
                    "[PID:%d] Registered tool schemas: %s",
                    pid,
                    [s.get('function', {}).get('name')
                     for s in schemas],
                )
                return toolkit
                
            except Exception as e:
                import traceback
                last_err = e
                backoff = min(2 ** (attempt - 1), 16)
                sleep_s = backoff + random.uniform(0, 0.5)
                logger.warning(
                    "[PID:%d] Attempt %d/%d FAILED: %s",
                    pid, attempt, max_retries, repr(e),
                )
                logger.debug("[PID:%d] Full traceback:\n%s", pid, traceback.format_exc())
                if attempt < max_retries:
                    logger.debug("[PID:%d] Retrying in %.1fs...", pid, sleep_s)
                    await asyncio.sleep(sleep_s)

        # If we got here, init failed after retries.
        logger.error(
            "[PID:%d] All %d attempts failed."
            " Last error: %s",
            pid, max_retries, repr(last_err),
        )
        raise RuntimeError(
            f"Failed to initialize finance-mcp toolkit"
            f" for {url}: {last_err!r}",
        ) from last_err

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
    """DeepFinance workflow (Route B skeleton)."""
    import time
    
    assert (
        auxiliary_models is None or len(auxiliary_models) == 0
    ), "No auxiliary models are used in this workflow (for now)."

    sys_prompt, user_query = _extract_sys_and_user(task)
    toolkit = await get_finance_mcp_toolkit()

    agent = ReActAgent(
        name="deep_finance_react",
        sys_prompt=sys_prompt,
        model=model,
        enable_meta_tool=False,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
    )

    start_time = time.time()
    response = await agent.reply(msg=Msg("user", user_query, role="user"))
    total_time = time.time() - start_time

    # Extract tool_stats and compute metrics
    tool_stats = await extract_tool_stats_from_agent(agent, total_time)
    metrics = compute_single_tool_metrics(tool_stats)
    
    # Extract response content, convert to dict for cross-process serialization safety
    response_content = response.content if hasattr(response, 'content') else str(response)
    if hasattr(response_content, 'model_dump'):
        response_content = response_content.model_dump()
    elif not isinstance(response_content, (str, list, dict, type(None))):
        response_content = str(response_content)
    
    # ========== Save article to jsonl file ==========
    # Get trajectory_save_dir from task.workflow_args
    workflow_args = task.get("workflow_args", {})
    trajectory_save_dir = workflow_args.get("trajectory_save_dir")
    
    # Add detailed logging and error handling
    task_id = task.get("task_id") or task.get("id") or "unknown"
    
    # Fall back to default backup path if trajectory_save_dir is None
    if trajectory_save_dir is None:
        trajectory_save_dir = os.path.join(
            os.path.dirname(__file__), 
            "trajectory", 
            "backup"
        )
        logging.warning(
            "[ArticleSaver] trajectory_save_dir is None! "
            "task_id=%s, workflow_args keys=%s. "
            "Falling back to backup dir: %s",
            task_id, list(workflow_args.keys()), trajectory_save_dir
        )
    else:
        logging.info(
            "[ArticleSaver] Saving article to: %s"
            " (task_id=%s)",
            trajectory_save_dir, task_id,
        )

    # Build response dict (for judge consumption)
    # Use dict instead of Msg object to ensure metadata transfers correctly across processes
    response_dict = {
        "content": response_content,
        "role": getattr(response, "role", "assistant"),
        "metadata": {
            "tool_stats": tool_stats,
            "task_id": task.get("task_id"),
            "query": user_query,
        }
    }
    
    return WorkflowOutput(response=response_dict, metrics=metrics)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DeepFinance training entry (tuner style).")

    # Dataset
    p.add_argument(
        "--dataset_path", type=str, default="./data",
        help="Path to DeepFinance dataset directory.",
    )
    p.add_argument(
        "--split", type=str, default="train",
        help="Dataset split, e.g. train/validation/test.",
    )
    p.add_argument("--total_epochs", type=int, default=4, help="Total number of epochs to run.")

    # Model (aligned with config.yaml)
    p.add_argument(
        "--config_path", type=str,
        default="tuner/deep_finance/config_template.yaml",
        help="Yaml config file path.",
    )
    p.add_argument(
        "--model_path", type=str,
        default="/path/to/base_model",
        help="Base model path for tuning.",
    )
    p.add_argument(
        "--inference_engine_num", type=int, default=4,
        help="Number of vllm inference model instances.",
    )
    # Algorithm (aligned with config.yaml)
    p.add_argument(
        "--algorithm_type", type=str,
        default="multi_step_grpo",
        help="Algorithm type for training.",
    )
    p.add_argument(
        "--group_size", type=int, default=8,
        help=("Group size for GRPO algorithm"
              " (corresponds to repeat_times in config.yaml)."),
    )
    p.add_argument("--batch_size", type=int, default=32, help="Batch size for each step.")

    return p


def main() -> None:
    args = _build_arg_parser().parse_args()

    # Default dataset path: ./data (same as learn_to_ask style)
    config_path = args.config_path

    # Load all settings (model, dataset, algorithm, cluster, etc.) from config.yaml
    tune(
        workflow_func=run_deep_finance,
        judge_func=deep_finance_judge,
        config_path=str(config_path),
    )


if __name__ == "__main__":
    main()

