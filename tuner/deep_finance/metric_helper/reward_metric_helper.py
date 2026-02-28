"""
DeepFinance Reward Metrics Helper

Provides utility functions for building judge metrics.

Metrics directory structure:
- rewards/              Top-level aggregated scores
- rewards/finance/      Finance evaluator metrics
- rewards/openjudge/    OpenJudge grader metrics
- judge_time/           Judge time consumption statistics
"""

from typing import Dict


def build_judge_metrics(
    final_reward: float,
    fused_reward: float,
    penalty: float,
    finance_score: float,
    contributions: Dict[str, float],
    grader_scores: Dict[str, float],
    grading_time: float,
    judge_total_time: float,
) -> Dict[str, float]:
    """
    构建 judge 输出的 metrics 字典。
    
    Args:
        final_reward: 最终奖励
        fused_reward: 融合奖励
        penalty: 惩罚值
        finance_score: 金融评估原始分数
        contributions: 各维度贡献 {grader_name: contribution, "rm_contribution": xxx}
        grader_scores: OpenJudge 各 grader 原始分数
        grading_time: 评分耗时
        judge_total_time: judge 总耗时
    
    Returns:
        metrics 字典
    """
    metrics: Dict[str, float] = {
        # Top-level rewards
        "rewards/final_reward": final_reward,
        "rewards/fused_reward": fused_reward,
        "rewards/penalty": penalty,
        "rewards/step_reward": 0.0,
        
        # Finance Evaluator
        "rewards/finance/finance_raw": finance_score,
        "rewards/finance/finance_contribution": contributions.get("rm_contribution", 0.0),
        
        # 时间统计
        "judge_time/grading_time": grading_time,
        "judge_time/total_time": judge_total_time,
    }
    
    # OpenJudge graders 分数
    for grader_name, score in grader_scores.items():
        metrics[f"rewards/openjudge/{grader_name}_raw"] = score
        if grader_name in contributions:
            metrics[f"rewards/openjudge/{grader_name}_contribution"] = contributions[grader_name]
    
    return metrics

