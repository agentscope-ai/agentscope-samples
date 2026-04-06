# -*- coding: utf-8 -*-
"""DeepFinance Judge - AgentScope Tuner 版本

基于 agentscope tuner 框架的 DeepFinance judge 函数。
集成: FinanceCompositionEvaluator (基于 OpenJudge), PresentationQualityGrader
"""

import os
import asyncio
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from agentscope.tuner import JudgeOutput
from agentscope.model import ChatModelBase

from openjudge.models.openai_chat_model import OpenAIChatModel
from openjudge.runner.grading_runner import GraderConfig, GradingRunner
from judge import (
    PresentationQualityGrader, 
    GroundingGrader, 
    AuditGrader, 
    FinanceCompositionEvaluator,
    load_reference_answers_from_file,
)
from metric_helper.reward_metric_helper import build_judge_metrics

logger = logging.getLogger(__name__)


# =============================================================================
# 配置类（从环境变量读取）
# =============================================================================

@dataclass(frozen=True)
class DeepFinanceJudgeConfig:
    """Judge 配置，从环境变量读取"""
    openjudge_llm: str
    openjudge_base_url: str
    openjudge_api_key: str
    concurrency: int = 6
    
    # Finance Judge 单独的模型配置
    finance_judge_llm: str = ""
    
    # 权重配置
    finance_rm_weight: float = 1.0
    presentation_quality_weight: float = 0.25
    grounding_weight: float = 0.0
    audit_weight: float = 0.0
    
    # 参考答案路径
    train_ref_ans_path: str = ""
    val_ref_ans_path: str = ""

    @staticmethod
    def from_env() -> "DeepFinanceJudgeConfig":
        return DeepFinanceJudgeConfig(
            openjudge_llm=os.environ.get("OPENJUDGE_LLM", "gpt-4o-mini"),
            openjudge_base_url=os.environ.get("OPENJUDGE_BASE_URL", ""),
            openjudge_api_key=os.environ.get("OPENJUDGE_API_KEY", ""),
            concurrency=int(os.environ.get("OPENJUDGE_CONCURRENCY", "6")),
            finance_judge_llm=os.environ.get("FINANCE_JUDGE_LLM", ""),
            finance_rm_weight=float(os.environ.get("FINANCE_RM_WEIGHT", "1.0")),
            presentation_quality_weight=float(os.environ.get("JUDGE_PRESENTATION_QUALITY_WEIGHT", "0.25")),
            grounding_weight=float(os.environ.get("JUDGE_GROUNDING_WEIGHT", "0.0")),
            audit_weight=float(os.environ.get("JUDGE_AUDIT_WEIGHT", "0.0")),
            train_ref_ans_path=os.environ.get("JUDGE_TRAIN_REF_ANS_PATH", ""),
            val_ref_ans_path=os.environ.get("JUDGE_VAL_REF_ANS_PATH", ""),
        )


# =============================================================================
# 全局辅助函数
# =============================================================================

def extract_text_content(content) -> str:
    """统一提取纯文本内容"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "".join(texts)
    return str(content)


# =============================================================================
# DeepFinance Judge Engine（可复用的评估引擎）
# =============================================================================

class DeepFinanceJudgeEngine:
    """
    DeepFinance 评估引擎（进程级单例）
    
    功能：
    - 初始化 OpenJudge model 和 graders
    - 执行评估并返回 (reward, metrics)
    """
    
    _instance: Optional["DeepFinanceJudgeEngine"] = None
    _ref_answers_cache: Dict[str, Dict[str, str]] = {}
    _ref_domains_cache: Dict[str, Dict[str, str]] = {}
    
    def __init__(self, cfg: DeepFinanceJudgeConfig):
        self.cfg = cfg
        self._model: Optional[OpenAIChatModel] = None
        self._finance_model: Optional[OpenAIChatModel] = None  # Finance Judge 单独的模型
        self._finance_evaluator: Optional[FinanceCompositionEvaluator] = None
        
        # 设置权重并归一化
        self.w = {
            "finance": cfg.finance_rm_weight,
            "presentation_quality": cfg.presentation_quality_weight,
            "grounding": cfg.grounding_weight,
            "audit": cfg.audit_weight,
        }
        positive_weights = {k: v for k, v in self.w.items() if v > 0}
        total = sum(positive_weights.values())
        if total > 0:
            for k in positive_weights:
                self.w[k] = self.w[k] / total
        
        self._finance_enabled = (self.w.get("finance", 0) > 0)
        
        # 加载参考答案
        self._load_reference_answers()
    
    def _load_reference_answers(self):
        """加载参考答案"""
        def _load(path, key):
            if path and key not in DeepFinanceJudgeEngine._ref_answers_cache:
                try:
                    ans, dom = load_reference_answers_from_file(path)
                    DeepFinanceJudgeEngine._ref_answers_cache[key] = ans
                    DeepFinanceJudgeEngine._ref_domains_cache[key] = dom
                except Exception:
                    DeepFinanceJudgeEngine._ref_answers_cache[key] = {}
                    DeepFinanceJudgeEngine._ref_domains_cache[key] = {}
        
        _load(self.cfg.train_ref_ans_path, "train")
        _load(self.cfg.val_ref_ans_path, "val")
    
    def _get_reference_data(self, task_id: str) -> Tuple[str, str]:
        """获取参考答案和领域"""
        cache_key = "val" if task_id.startswith("val_") else "train"
        ans = DeepFinanceJudgeEngine._ref_answers_cache.get(cache_key, {}).get(task_id, "")
        dom = DeepFinanceJudgeEngine._ref_domains_cache.get(cache_key, {}).get(task_id)
        return ans, dom
    
    def _init_model(self) -> OpenAIChatModel:
        """懒加载 OpenJudge model"""
        if self._model is None:
            self._model = OpenAIChatModel(
                model=self.cfg.openjudge_llm,
                base_url=self.cfg.openjudge_base_url,
                api_key=self.cfg.openjudge_api_key,
            )
        return self._model
    
    def _init_finance_model(self) -> OpenAIChatModel:
        """懒加载 Finance Judge 单独的模型"""
        if self._finance_model is None:
            # 如果配置了单独的 FINANCE_JUDGE_LLM，则使用它；否则回退到 OPENJUDGE_LLM
            model_name = self.cfg.finance_judge_llm if self.cfg.finance_judge_llm else self.cfg.openjudge_llm
            self._finance_model = OpenAIChatModel(
                model=model_name,
                base_url=self.cfg.openjudge_base_url,
                api_key=self.cfg.openjudge_api_key,
            )
        return self._finance_model
    
    def _init_finance_evaluator(self) -> Optional[FinanceCompositionEvaluator]:
        """懒加载 FinanceCompositionEvaluator（使用独立的 Finance Judge 模型）"""
        if self._finance_enabled and self._finance_evaluator is None:
            model = self._init_finance_model()
            self._finance_evaluator = FinanceCompositionEvaluator(model=model)
        return self._finance_evaluator
    
    def _create_grader_configs(self, model: OpenAIChatModel) -> Dict[str, GraderConfig]:
        """创建 grader 配置"""
        def extract_user_query(data: Dict) -> str:
            for msg in data.get("messages", []):
                if msg.get("role") == "user":
                    return msg.get("content", "")
            return ""

        def extract_report_content(data: Dict) -> str:
            for msg in reversed(data.get("messages", [])):
                if msg.get("role") == "assistant":
                    return msg.get("content", "")
            return ""

        return {
            "presentation_quality": GraderConfig(
                grader=PresentationQualityGrader(model=model),
                mapper=lambda data: {
                    "user_query": extract_user_query(data),
                    "report_content": extract_report_content(data),
                },
            ),
            "grounding": GraderConfig(
                grader=GroundingGrader(model=model),
                mapper=lambda data: {"traj": data},
            ),
            "audit": GraderConfig(
                grader=AuditGrader(model=model),
                mapper=lambda data: {"traj": data},
            ),
        }
    
    async def evaluate_one(
        self, 
        task: Dict[str, Any], 
        response: Any
    ) -> Tuple[float, Dict[str, float]]:
        """
        评估单个样本
        
        Args:
            task: 任务信息
            response: workflow 输出的 response
        
        Returns:
            (reward, metrics) - reward 值和用于 monitor 的 metrics
        """
        judge_start_time = time.time()

        # 提取任务信息
        task_id = task.get("task_id", "unknown")
        query = task.get("main_query", task.get("query", ""))
        chat_date = task.get("metadata", {}).get("chat_date", datetime.now().strftime("%Y-%m-%d"))
        
        # 构建对话历史
        history = self._build_history_from_response(task, response)
        
        if not history:
            return 0.0, {"rewards/final_reward": 0.0, "error": 1.0}
        
        # 准备 Finance 评估参数
        ref_ans, domain = self._get_reference_data(task_id)
        assistants = [extract_text_content(m["content"]) for m in history if m.get("role") == "assistant"]
        
        finance_eval_params = None
        if self._finance_enabled and ref_ans and domain:
            finance_eval_params = {
                "query": query,
                "current": assistants[-1] if assistants else "",
                "reference": ref_ans,
                "domain": domain
            }
        

        
        # 转换为 OpenJudge 格式
        openjudge_sample = self._convert_to_openjudge_format(history, query, task_id, chat_date)
        
        # 运行评估
        grading_start_time = time.time()
        grader_results, finance_score = await self._run_evaluation(
            [openjudge_sample], 
            finance_eval_params
        )
        grading_time = time.time() - grading_start_time
        
        # 提取分数
        grader_scores = self._extract_grader_scores(grader_results)
        
        # 融合分数
        fused_reward, contributions = self._fuse_scores(grader_scores, finance_score)
        
        # 计算惩罚（从 response 获取 tool_stats）
        tool_stats = {}
        if isinstance(response, dict):
            metadata = response.get("metadata", {})
            tool_stats = metadata.get("tool_stats", {}) if isinstance(metadata, dict) else {}
        elif hasattr(response, "metadata") and isinstance(response.metadata, dict):
            tool_stats = response.metadata.get("tool_stats", {})
        penalty = self._compute_penalty(tool_stats.get("total_calls", 0))
        
        # 最终 reward
        final_reward = fused_reward + penalty
        judge_total_time = time.time() - judge_start_time

        # 构建 metrics
        metrics = build_judge_metrics(
            final_reward=final_reward,
            fused_reward=fused_reward,
            penalty=penalty,
            finance_score=finance_score,
            contributions=contributions,
            grader_scores=grader_scores,
            grading_time=grading_time,
            judge_total_time=judge_total_time,
        )
        
        logger.info(f"Judge: task_id={task_id}, final={final_reward:.4f}, grading_time={grading_time:.2f}s")
        
        return final_reward, metrics
    
    def _build_history_from_response(self, task: Dict, response: Any) -> List[Dict[str, Any]]:
        """从 response 构建对话历史"""
        # 优先从 response 获取 metadata（支持 dict 和对象两种格式）
        metadata = None
        if isinstance(response, dict):
            metadata = response.get("metadata")
        elif hasattr(response, "metadata"):
            metadata = response.metadata
        
        if isinstance(metadata, dict):
            history = metadata.get("conversation_history")
            if history:
                return history
        
        # 回退：从 task 构建最小历史
        init_messages = task.get("init_messages", [])
        history = []
        
        for m in init_messages:
            if isinstance(m, dict):
                history.append({
                    "role": m.get("role", "user"),
                    "content": m.get("content", "")
                })
        
        # 添加 response
        if response:
            if isinstance(response, dict):
                content = extract_text_content(response.get("content"))
            else:
                content = extract_text_content(getattr(response, "content", None))
            history.append({"role": "assistant", "content": content})
        
        return history
    
    def _convert_to_openjudge_format(
        self, 
        history: List[Dict], 
        query: str, 
        task_id: str, 
        chat_date: str
    ) -> Dict[str, Any]:
        """转换为 OpenJudge 格式"""
        messages = []
        for msg in history:
            content = extract_text_content(msg.get("content", ""))
            normalized_msg = {
                "role": msg.get("role", "user"),
                "content": content
            }
            for field in ["tool_calls", "tool_call_id", "name"]:
                if field in msg:
                    normalized_msg[field] = msg[field]
            messages.append(normalized_msg)
        
        return {
            "messages": messages,
            "chat_date": chat_date,
            "rubrics": []
        }
    
    async def _run_evaluation(
        self, 
        dataset: List[Dict], 
        finance_eval_params: Optional[Dict] = None
    ) -> Tuple[Dict[str, List], float]:
        """运行 OpenJudge 评估"""
        grader_results = {}
        finance_score = 0.0
        
        model = self._init_model()
        grader_configs = self._create_grader_configs(model)
        
        runner = GradingRunner(
            grader_configs=grader_configs,
            max_concurrency=self.cfg.concurrency,
            show_progress=False
        )
        
        try:
            grader_results = await runner.arun(dataset)
        except Exception as e:
            logger.error(f"OpenJudge evaluation failed: {e}")
        
        # Finance 评估
        if finance_eval_params and self._finance_enabled:
            evaluator = self._init_finance_evaluator()
            if evaluator:
                try:
                    finance_score = await evaluator.aevaluate(
                        query=finance_eval_params.get("query", ""),
                        current=finance_eval_params.get("current", ""),
                        reference=finance_eval_params.get("reference", ""),
                        domain=finance_eval_params.get("domain", "")
                    )
                except Exception as e:
                    logger.error(f"Finance evaluation failed: {e}")
        
        return grader_results, finance_score
    
    def _extract_grader_scores(self, grader_results: Dict[str, List]) -> Dict[str, float]:
        """提取 grader 分数"""
        scores = {}
        for grader_name, score_list in grader_results.items():
            if score_list and len(score_list) > 0:
                gs = score_list[0]
                scores[grader_name] = getattr(gs, "score", 0.0) if hasattr(gs, "score") else 0.0
            else:
                scores[grader_name] = 0.0
        return scores
    
    def _fuse_scores(
        self, 
        grader_scores: Dict[str, float], 
        finance_score: float
    ) -> Tuple[float, Dict[str, float]]:
        """融合分数"""
        contributions = {}
        contributions["rm_contribution"] = self.w.get("finance", 0.0) * finance_score
        
        for grader_name, weight in self.w.items():
            if grader_name == "finance":
                continue
            score = grader_scores.get(grader_name, 0.0)
            contributions[grader_name] = weight * score
        
        fused_reward = sum(contributions.values())
        return fused_reward, contributions
    
    def _compute_penalty(self, tool_calls: int) -> float:
        """计算工具调用惩罚"""
        if tool_calls == 0:
            return -1.0
        elif tool_calls <= 2:
            return -0.5
        return 0.0


# =============================================================================
# 全局 Judge Engine 实例（懒加载）
# =============================================================================

_JUDGE_ENGINE: Optional[DeepFinanceJudgeEngine] = None


def _get_judge_engine() -> DeepFinanceJudgeEngine:
    """获取 Judge Engine 单例"""
    global _JUDGE_ENGINE
    if _JUDGE_ENGINE is None:
        cfg = DeepFinanceJudgeConfig.from_env()
        _JUDGE_ENGINE = DeepFinanceJudgeEngine(cfg)
    return _JUDGE_ENGINE


# =============================================================================
# AgentScope Tuner 风格的 Judge 函数
# =============================================================================

async def deep_finance_judge(
    task: Dict[str, Any],
    response: Any,
    auxiliary_models: Dict[str, ChatModelBase] | None = None,
) -> JudgeOutput:
    """
    DeepFinance Judge 函数（AgentScope Tuner 风格）
    
    Args:
        task: 任务信息字典
        response: workflow 返回的 response
        auxiliary_models: 辅助模型（可选，未使用）
    
    Returns:
        JudgeOutput: 包含 reward 和 metrics
    """
    _ = auxiliary_models  # 当前未使用
    
    engine = _get_judge_engine()
    reward, metrics = await engine.evaluate_one(task=task, response=response)
    
    return JudgeOutput(reward=reward, metrics=metrics)
