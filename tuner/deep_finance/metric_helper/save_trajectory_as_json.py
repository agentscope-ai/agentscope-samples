"""
Trajectory 保存模块 - 适配 AgentScope Tuner

将 workflow 的对话历史和 judge 结果保存为 JSON 文件，便于后续分析和调试。
"""

import os
import re
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


def determine_task_tag(reward: float) -> str:
    """
    根据 reward 值确定任务标签。
    
    Args:
        reward: judge 返回的 reward 值
    
    Returns:
        任务标签: "success", "half_success", 或 "failure"
    """
    if reward >= 1.0:
        return "success"
    elif reward > 0.0:
        return "half_success"
    else:
        return "failure"


def sanitize_filename(name: str) -> str:
    """
    清理文件名，移除非法字符。
    
    Args:
        name: 原始文件名
    
    Returns:
        清理后的安全文件名
    """
    # 替换非法字符为下划线
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 限制长度
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def save_single_trajectory(
    task_id: str,
    reward: float,
    conversation_history: List[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]] = None,
    prefix: str = "train",
) -> Optional[str]:
    """
    保存单个 trajectory 到 JSON 文件。
    
    Args:
        task_id: 任务 ID
        reward: judge 返回的 reward 值
        conversation_history: OpenAI 格式的对话历史
            [{"role": "system/user/assistant/tool", "content": "...", ...}, ...]
        metrics: judge 输出的 metrics 字典
        prefix: 目录前缀，"train" 或 "eval"
    
    Returns:
        保存的文件路径，如果保存失败则返回 None
    """
    if not task_id:
        print("[save_trajectory] Warning: task_id is empty, skipping save")
        return None
    
    # 确定任务标签
    task_tag = determine_task_tag(reward)
    
    # 构建 trajectory 数据
    traj_data = {
        "task_id": task_id,
        "task_tag": task_tag,
        "reward": reward,
        "metrics": metrics or {},
        "conversation_history": conversation_history or [],
        "saved_at": datetime.now().isoformat(),
    }
    
    # 确定保存目录
    base_dir = os.environ.get("TRAJECTORY_SAVE_DIR", "./trajectory")
    traj_save_dir = os.path.join(base_dir, prefix, task_tag)
    
    try:
        os.makedirs(traj_save_dir, exist_ok=True)
        
        # 生成安全的文件名（清理非法字符 + 时间戳 + UUID 避免冲突）
        safe_task_id = sanitize_filename(task_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:6]
        traj_file_path = os.path.join(traj_save_dir, f"{safe_task_id}_{timestamp}_{unique_suffix}.json")
        
        # 保存到 JSON 文件
        with open(traj_file_path, "w", encoding="utf-8") as f:
            json.dump(traj_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"[save_trajectory] Saved trajectory to {traj_file_path}")
        return traj_file_path
        
    except Exception as e:
        print(f"[save_trajectory] Error saving trajectory for {task_id}: {e}")
        return None


def save_batch_trajectories(
    trajectories: List[Dict[str, Any]],
    prefix: str = "train",
) -> List[str]:
    """
    批量保存多个 trajectories。
    
    Args:
        trajectories: trajectory 数据列表，每个元素包含:
            - task_id: str
            - reward: float
            - conversation_history: List[Dict]
            - metrics: Optional[Dict]
        prefix: 目录前缀
    
    Returns:
        成功保存的文件路径列表
    """
    saved_paths = []
    for traj in trajectories:
        path = save_single_trajectory(
            task_id=traj.get("task_id", ""),
            reward=traj.get("reward", 0.0),
            conversation_history=traj.get("conversation_history", []),
            metrics=traj.get("metrics"),
            prefix=prefix,
        )
        if path:
            saved_paths.append(path)
    
    return saved_paths
