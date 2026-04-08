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
    Build the metrics dict for judge output.

    Args:
        final_reward: Final reward value
        fused_reward: Fused reward value
        penalty: Penalty value
        finance_score: Raw finance evaluation score
        contributions: Per-dimension contributions {grader_name: contribution, "rm_contribution": xxx}
        grader_scores: Raw scores from each OpenJudge grader
        grading_time: Time spent on grading
        judge_total_time: Total judge execution time

    Returns:
        Metrics dict
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
        
        # Time statistics
        "judge_time/grading_time": grading_time,
        "judge_time/total_time": judge_total_time,
    }
    
    # OpenJudge grader scores
    for grader_name, score in grader_scores.items():
        metrics[f"rewards/openjudge/{grader_name}_raw"] = score
        if grader_name in contributions:
            metrics[f"rewards/openjudge/{grader_name}_contribution"] = contributions[grader_name]
    
    return metrics

