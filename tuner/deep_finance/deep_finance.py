# -*- coding: utf-8 -*-
"""DeepFinance Workflow - AgentScope Tuner 版本

基于 agentscope tuner 框架的 DeepFinance workflow 函数。
"""

import os
import time
import threading
from typing import Dict, Any, List, Optional
from loguru import logger

from agentscope.tuner import WorkflowOutput
from agentscope.model import ChatModelBase
from agentscope.message import Msg

from metric_helper import compute_single_tool_metrics, extract_tool_stats_from_agent


# 创建信号量，允许同时运行的线程数
sem = threading.Semaphore(int(os.environ.get("DEEP_FINANCE_CONCURRENCY", "30")))

# 默认最大步骤数
DEFAULT_MAX_STEPS = int(os.environ.get("DEEP_FINANCE_MAX_STEPS", "20"))


def _extract_text_content(content) -> str:
    """统一提取纯文本内容（兼容多模态格式）"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # 多模态格式: [{'type': 'text', 'text': '...'}]
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "".join(texts)
    return str(content)


async def deep_finance_workflow(
    task: Dict[str, Any],
    model: ChatModelBase,
    auxiliary_models: Dict[str, ChatModelBase] | None = None,
) -> WorkflowOutput:
    """
    DeepFinance Workflow 函数（AgentScope Tuner 风格）
    
    Args:
        task: 任务信息字典，包含 init_messages, main_query, task_id 等
        model: 主训练模型
        auxiliary_models: 辅助模型（可选）
    
    Returns:
        WorkflowOutput: 包含 reward, response, metrics
    """
    from agentscope.agent import ReActAgent
    from agentscope.formatter import DashScopeChatFormatter
    from agentscope.memory import InMemoryMemory
    
    _ = auxiliary_models  # 当前未使用
    
    # 1. 提取任务信息
    init_messages = task.get("init_messages", [])
    task_id = task.get("task_id", "unknown")
    main_query = task.get("main_query", task.get("query", ""))
    max_steps = task.get("max_steps", DEFAULT_MAX_STEPS)
    
    # 分离 System Prompt 和 User Messages
    if len(init_messages) >= 2:
        first_msg, user_msgs = init_messages[0], init_messages[1:]
    else:
        first_msg = {"content": "You're a helpful assistant."}
        user_msgs = init_messages
    
    sys_prompt = first_msg.get("content", "You're a helpful assistant.")
    
    # 2. 初始化对话历史（OpenAI 格式）
    conversation_history: List[Dict[str, Any]] = [
        {"role": "system", "content": sys_prompt},
    ]
    conversation_history.extend(user_msgs)
    
    # 3. 初始化 Agent
    agent = ReActAgent(
        name="DeepFinance",
        sys_prompt=sys_prompt,
        model=model,
        formatter=DashScopeChatFormatter(),
        memory=InMemoryMemory(),
        toolkit=None,
        print_hint_msg=False,
    )
    agent.set_console_output_enabled(False)
    
    # 4. 构造初始输入
    agent_input = []
    for m in user_msgs:
        agent_input.append(Msg(
            name=m.get("name", "user"),
            content=m.get("content", ""),
            role=m.get("role", "user")
        ))
    
    # 5. 执行多轮对话
    step = 0
    final_response = None
    workflow_start_time = time.time()
    
    for step in range(max_steps):
        # Agent 推理
        _start = time.time()
        reply_message = await agent(agent_input)
        _elapsed = time.time() - _start
        
        # 提取文本内容
        content_text = _extract_text_content(reply_message.content)
        
        # 更新对话历史
        conversation_history.append({
            "role": "assistant",
            "content": content_text
        })
        
        final_response = reply_message
        
        # 简单终止检查：如果没有工具调用，则结束
        # 注：完整版本需要与 env 交互，这里简化处理
        if not getattr(reply_message, 'tool_calls', None):
            break
        
        # 准备下一轮输入（简化版本）
        agent_input = []
    
    # 6. 从 agent 提取工具统计
    workflow_total_time = time.time() - workflow_start_time
    tool_stats = await extract_tool_stats_from_agent(agent, total_time=workflow_total_time)
    
    # 7. 计算 metrics（工具统计）
    workflow_metrics = compute_single_tool_metrics(tool_stats)
    workflow_metrics["workflow/total_steps"] = float(step + 1)
    workflow_metrics["workflow/total_time"] = workflow_total_time
    
    logger.info(f"任务完成 (Task ID: {task_id}): 步骤={step + 1}")
    
    # 8. 构建 response dict（供 judge 使用）
    # 使用 dict 格式，确保可序列化，兼容框架传递
    response_dict = {
        "content": _extract_text_content(final_response.content) if final_response else "",
        "role": getattr(final_response, "role", "assistant") if final_response else "assistant",
        "metadata": {
            "conversation_history": conversation_history,
            "tool_stats": tool_stats,
            "task_id": task_id,
            "query": main_query,
        }
    }
    
    # 9. 返回结果
    return WorkflowOutput(
        reward=None,  # reward 由 judge 计算
        response=response_dict,
        metrics=workflow_metrics,
    )
