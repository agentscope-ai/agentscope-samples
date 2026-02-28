import os
from typing import Dict, List, Any, Optional

from .save_trajectory_as_json import save_single_trajectory, save_batch_trajectories
from .tool_metric_helper import extract_tool_stats_from_agent, compute_single_tool_metrics
from .reward_metric_helper import build_judge_metrics


def maybe_save_trajectory(
    task_id: str,
    reward: float,
    conversation_history: List[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]] = None,
    prefix: str = "train",
) -> Optional[str]:
    """
    根据环境变量决定是否保存 trajectory。
    
    Args:
        task_id: 任务 ID
        reward: judge 返回的 reward 值
        conversation_history: OpenAI 格式的对话历史
        metrics: judge 输出的 metrics 字典
        prefix: 目录前缀，"train" 或 "eval"
    
    Returns:
        保存的文件路径，如果未启用或保存失败则返回 None
    """
    if os.environ.get("SAVE_TRAJECTORY", "false").lower() == "true":
        return save_single_trajectory(
            task_id=task_id,
            reward=reward,
            conversation_history=conversation_history,
            metrics=metrics,
            prefix=prefix,
        )
    return None
