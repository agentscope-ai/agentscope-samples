"""
DeepFinance Tool Metrics Helper

Specialized module for extracting tool-related statistics from ReActAgent.

Metrics directory structure:
- tool_stats/           Overall statistics (success rate, cache hit rate, etc.)
"""

from typing import Dict, Any
import numpy as np


async def extract_tool_stats_from_agent(agent: Any, total_time: float = 0.0) -> Dict[str, Any]:
    """
    从 ReActAgent 的 memory 中提取工具调用统计信息。
    
    Args:
        agent: ReActAgent 实例
        total_time: workflow 总执行时间（秒）
    
    Returns:
        tool_stats 字典
    """
    import logging
    import os
    
    # DEBUG 模式：设置环境变量 DEBUG_TOOL_RESULT=1 开启

    logger = logging.getLogger("tool_metric_helper")
    
    tool_stats = {
        'total_calls': 0,
        'success_calls': 0,
        'total_errors': 0,
        'cache_hits': 0,
        'cache_misses': 0,
    }
    
    try:
        memory_msgs = await agent.memory.get_memory()
        
        # DEBUG: 打印 memory 消息结构
        
        for msg in memory_msgs:
            # 提取 tool_use blocks
            tool_uses = msg.get_content_blocks("tool_use") if hasattr(msg, 'get_content_blocks') else []
            for tool_use in tool_uses:
                tool_stats['total_calls'] += 1
            
            # 提取 tool_result blocks 判断成功/失败
            tool_results = msg.get_content_blocks("tool_result") if hasattr(msg, 'get_content_blocks') else []
            for tool_result in tool_results:
                is_error = tool_result.get('is_error', False) if isinstance(tool_result, dict) else getattr(tool_result, 'is_error', False)
                if is_error:
                    tool_stats['total_errors'] += 1
                else:
                    tool_stats['success_calls'] += 1
                
    except Exception as e:
        logging.warning(f"Failed to extract tool stats from memory: {e}")
    
    return tool_stats


def compute_single_tool_metrics(tool_stats: Dict[str, Any], prefix: str = "") -> Dict[str, float]:
    """
    从单个 tool_stats 字典计算 metrics（用于单次 workflow 输出）。
    
    Args:
        tool_stats: 单个 tool_stats 字典
        prefix: metric 前缀
    
    Returns:
        metrics 字典
    """
    if not tool_stats:
        return {}
    
    metrics = {}
    
    total_calls = tool_stats.get('total_calls', 0)
    success_calls = tool_stats.get('success_calls', 0)
    total_errors = tool_stats.get('total_errors', 0)
    cache_hits = tool_stats.get('cache_hits', 0)
    cache_misses = tool_stats.get('cache_misses', 0)
    
    success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0.0
    cache_total = cache_hits + cache_misses
    cache_hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0.0
    
    metrics.update({
        f"{prefix}tool_stats/tool_total_calls": float(total_calls),
        f"{prefix}tool_stats/tool_success_calls": float(success_calls),
        f"{prefix}tool_stats/tool_error_calls": float(total_errors),
        f"{prefix}tool_stats/tool_success_rate": float(success_rate),
        f"{prefix}tool_stats/tool_cache_hits": float(cache_hits),
        f"{prefix}tool_stats/tool_cache_misses": float(cache_misses),
        f"{prefix}tool_stats/tool_cache_hit_rate": float(cache_hit_rate),
    })
    
    return metrics


