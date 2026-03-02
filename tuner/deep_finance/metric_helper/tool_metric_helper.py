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
    debug_tool_result = True
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
        if debug_tool_result:
            logger.warning(f"[DEBUG_TOOL_STATS] memory has {len(memory_msgs)} messages")
            for i, msg in enumerate(memory_msgs):
                msg_type = type(msg).__name__
                has_gcb = hasattr(msg, 'get_content_blocks')
                content_type = type(msg.content).__name__ if hasattr(msg, 'content') else 'N/A'
                content_preview = str(msg.content)[:200] if hasattr(msg, 'content') else 'N/A'
                logger.warning(f"[DEBUG_TOOL_STATS] msg[{i}] type={msg_type} has_get_content_blocks={has_gcb} content_type={content_type}")
                logger.warning(f"[DEBUG_TOOL_STATS] msg[{i}] content_preview: {content_preview}")
                # 尝试直接检查 content 中是否有 tool_use/tool_result
                if hasattr(msg, 'content') and isinstance(msg.content, list):
                    for j, block in enumerate(msg.content):
                        block_type = block.get('type', 'unknown') if isinstance(block, dict) else type(block).__name__
                        logger.warning(f"[DEBUG_TOOL_STATS] msg[{i}] block[{j}] type={block_type}")
        
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
                
                # DEBUG: 打印工具返回结果的前100个词
                if debug_tool_result:
                    tool_use_id = tool_result.get('tool_use_id', 'unknown') if isinstance(tool_result, dict) else getattr(tool_result, 'tool_use_id', 'unknown')
                    content = tool_result.get('content', '') if isinstance(tool_result, dict) else getattr(tool_result, 'content', '')
                    if isinstance(content, list):
                        # 处理 content 为 list 的情况
                        content_str = ' '.join(
                            item.get('text', '') if isinstance(item, dict) else str(item) 
                            for item in content
                        )
                    else:
                        content_str = str(content) if content else ''
                    # 取前100个词
                    words = content_str.split()[:100]
                    preview = ' '.join(words)
                    status = "ERROR" if is_error else "SUCCESS"
                    logger.warning(f"[DEBUG_TOOL_RESULT] tool_use_id={tool_use_id} status={status} result_preview(100 words): {preview}")
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


