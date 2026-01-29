"""DeepFinance Task Judge - OpenJudge 版本
集成: RM Gallery, PresentationQualityGrader
"""

import os
import json
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from ajet.task_judge.base_judge import BaseJudge
from ajet.workflow import WorkflowOutput, WorkflowTask

from openjudge.models.openai_chat_model import OpenAIChatModel
from openjudge.runner.grading_runner import GraderConfig, GradingRunner
from tutorial.example_deep_finance.judge import PresentationQualityGrader, GroundingGrader



# OpenJudge imports
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


def load_reference_answers_from_file(file_path: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """加载参考答案 (RM Gallery 需要)"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Reference answers file not found: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ref_answers, ref_domains = {}, {}
        for item in data:
            task_id = item.get("task", {}).get("task_id")
            if not task_id or "answer" not in item: continue
            ref_answers[task_id] = item["answer"]
            domain = item.get("task", {}).get("metadata", {}).get("domain")
            if domain: ref_domains[task_id] = domain
        return ref_answers, ref_domains
    except Exception as e:
        raise ValueError(f"Error loading reference answers: {e}")


# =============================================================================
# DeepFinanceJudgeByOpenJudge 类
# =============================================================================

class DeepFinanceJudgeByOpenJudge(BaseJudge):
    """
    使用 OpenJudge 框架的 DeepFinance Judge
    集成: RM Gallery, PresentationQualityGrader
    
    分析：
    - compute_reward 每次处理 **一条采样**（单个 workflow_output）
    - 输入：workflow_task, workflow_output
    - 输出：(final_reward: float, is_success: bool)
    - 副作用：更新 workflow_output.metadata["reward_stats"]
    
    注意：GradingRunner 不能使用单例模式，因为其内部 Semaphore 会绑定到创建时的事件循环
    """
    
    _model_instance = None  # Model 可以复用
    _rm_evaluator_instance = None  # RM Gallery Evaluator (单例)
    _ref_answers_cache: Dict[str, Dict[str, str]] = {}  # 参考答案缓存
    _ref_domains_cache: Dict[str, Dict[str, str]] = {}  # 领域缓存
    
    def __init__(self, config):
        super().__init__(config)
        self._setup_weights()
        self._init_openjudge_model()  # 只初始化 model，runner 在每次调用时创建
        self._init_rm_components()  # 初始化 RM Gallery 组件
        self._init_reference_answers()  # 初始化参考答案
        
    def _setup_weights(self):
        """
        配置 OpenJudge 各 grader 的权重并归一化
        
        graders 对应关系：
        - presentation_quality: 报告呈现质量评估
        """
        cfg = getattr(self.config, "ajet", None)
        
        # 定义各 grader 的权重（可从 config 中读取）
        self.w = {
            "rm": getattr(cfg, "rm_weight", 1.0) if cfg else 1.0,  # RM Gallery 权重
            "presentation_quality": getattr(cfg, "presentation_quality_weight", 0.25) if cfg else 0.25,
            "grounding": getattr(cfg, "grounding_weight", 0.25) if cfg else 0.25,
        }
        
        # 归一化（注意：action_loop 是惩罚项，不参与归一化；rm 需要参与归一化）
        positive_weights = {k: v for k, v in self.w.items() if k != "action_loop" and v > 0}
        total = sum(positive_weights.values())
        if total > 0:
            for k in positive_weights:
                self.w[k] = self.w[k] / total
                
    
    def _init_openjudge_model(self):
        """初始化 OpenJudge LLM Model"""
        # --- model name from config.ajet.judge.* ---
        openjudge_model_name = self.config.ajet.judge.openjudge_llm
        openjudge_base_url = os.environ.get("OPENJUDGE_BASE_URL")
        openjudge_api_key = os.environ.get("OPENJUDGE_API_KEY")

        self._model_instance = OpenAIChatModel(
            model=openjudge_model_name,
            base_url=openjudge_base_url,
            api_key=openjudge_api_key,
        )
        # 设置实例变量供 _create_runner_in_loop 使用
        self.model = self._model_instance
        self.max_concurrency = getattr(self.config.ajet.judge, "concurrency", 6)
        
        print(
            f"[Init OpenJudge Model] model={openjudge_model_name}, base_url={openjudge_base_url}, "
            f"api_key={'SET' if openjudge_api_key else 'NONE'}, max_concurrency={self.max_concurrency}"
        )

    def _init_rm_components(self):
        """初始化 RM Gallery Evaluator（仅当 rm_weight > 0 时）"""
        self._rm_enabled = (self.w.get("rm", 0) > 0)
        if self._rm_enabled:
            if DeepFinanceJudgeByOpenJudge._rm_evaluator_instance is None:
                self._init_rm_evaluator()
                DeepFinanceJudgeByOpenJudge._rm_evaluator_instance = self.rm_evaluator
            else:
                self.rm_evaluator = DeepFinanceJudgeByOpenJudge._rm_evaluator_instance
        else:
            self.rm_evaluator = None
    
    def _init_rm_evaluator(self):
        """初始化 RM Gallery Evaluator"""
        try:
            # Monkey patch OpenAI client timeout (RM Gallery 默认只有60s，对于30B模型不够用)
            import openai
            _original_openai_init = openai.OpenAI.__init__
            def _patched_openai_init(self, *args, **kwargs):
                kwargs.setdefault('timeout', 600.0)  # 增大到600秒
                return _original_openai_init(self, *args, **kwargs)
            openai.OpenAI.__init__ = _patched_openai_init
            
            from rm_gallery.core.reward.registry import RewardRegistry
            import logging
            logging.getLogger("rm_gallery").setLevel(logging.WARNING)
            
            # 从 config 读取 rm_llm，环境变量作为 fallback
            rm_llm_name = self.config.ajet.judge.rm_llm
            rm_api_key = os.environ.get("RM_API_KEY")
            rm_base_url = os.environ.get("RM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            
            rm_params = {"is_parallel": True, "enable_thinking": False, "base_url": rm_base_url}
            if rm_api_key:
                rm_params["api_key"] = rm_api_key
            
            self.rm_evaluator = RewardRegistry.get("finance_composition")(
                llm=rm_llm_name, name="finance_composition", params=rm_params
            )
            print(f"[Init RM Evaluator] llm={rm_llm_name}, base_url={rm_base_url}, api_key={'SET' if rm_api_key else 'NONE'} (timeout=600s)")
        except Exception as e:
            print(f"✗ Failed to initialize RM evaluator: {e}")
            import traceback
            traceback.print_exc()
            self.rm_evaluator = None
    
    def _init_reference_answers(self):
        """初始化参考答案缓存，从 config 中读取路径"""
        # 从 config 中获取 reference answer 路径
        train_ref_ans_path = getattr(self.config.ajet.judge, "train_ref_ans_path", "")
        val_ref_ans_path = getattr(self.config.ajet.judge, "val_ref_ans_path", "")
        
        def _load(path, key):
            if path and key not in DeepFinanceJudgeByOpenJudge._ref_answers_cache:
                try:
                    ans, dom = load_reference_answers_from_file(path)
                    DeepFinanceJudgeByOpenJudge._ref_answers_cache[key], DeepFinanceJudgeByOpenJudge._ref_domains_cache[key] = ans, dom
                except Exception:
                    DeepFinanceJudgeByOpenJudge._ref_answers_cache[key], DeepFinanceJudgeByOpenJudge._ref_domains_cache[key] = {}, {}
        _load(train_ref_ans_path, "train")
        _load(val_ref_ans_path, "val")
    
    def _get_reference_data(self, task_id: str) -> Tuple[str, str]:
        """获取任务的参考答案和领域"""
        cache_key = "val" if task_id.startswith("val_") else "train"
        ans = DeepFinanceJudgeByOpenJudge._ref_answers_cache.get(cache_key, {}).get(task_id, "")
        dom = DeepFinanceJudgeByOpenJudge._ref_domains_cache.get(cache_key, {}).get(task_id)
        return ans, dom
    

    def _create_runner_in_loop(self) -> GradingRunner:
        """
        在当前事件循环中创建 GradingRunner
        
        注意：GradingRunner 内部的 Semaphore 会绑定到创建时的事件循环，
        因此不能使用单例模式，必须在每次调用的事件循环中创建新实例。
        """
        grader_configs = self._create_grader_configs(self.model)
        return GradingRunner(
            grader_configs=grader_configs,
            max_concurrency=self.max_concurrency,
            show_progress=False
        )
    
    def _create_grader_configs(self, model: OpenAIChatModel) -> Dict[str, GraderConfig]:
        """
        创建所有 grader 的配置
        
        返回：Dict[str, GraderConfig]
        - key: grader 名称
        - value: GraderConfig(grader=..., mapper=...)
        """
        
        def extract_user_query(data: Dict) -> str:
            """从 messages 中提取第一条 user 消息的 content"""
            for msg in data.get("messages", []):
                if msg.get("role") == "user":
                    return msg.get("content", "")
            return ""
        
        def extract_report_content(data: Dict) -> str:
            """从 messages 中提取最后一条 assistant 消息的 content"""
            for msg in reversed(data.get("messages", [])):
                if msg.get("role") == "assistant":
                    return msg.get("content", "")
            return ""
        
        return {
            # 报告呈现质量评估 - 需要 user_query 和 report_content
            "presentation_quality": GraderConfig(
                grader=PresentationQualityGrader(model=model),
                mapper=lambda data: {
                    "user_query": extract_user_query(data),
                    "report_content": extract_report_content(data),
                },
            ),
            # 引用规范性评估 - 需要完整的 traj
            "grounding": GraderConfig(
                grader=GroundingGrader(model=model),
                mapper=lambda data: {"traj": data},
            ),
        }
    
    def compute_reward(self, workflow_task: WorkflowTask, workflow_output: WorkflowOutput) -> Tuple[float, bool]:
        """
        主计算逻辑：使用 OpenJudge Runner.arun 计算 reward
        
        流程：
        1. 从 workflow_output.metadata 提取 conversation_history、query、rubrics 等
        2. 转换为 OpenJudge 的输入格式 (messages, chat_date, rubrics)
        3. 调用 Runner.arun([sample]) 获取所有 graders 的评分
        4. 加权融合各 grader 分数
        5. 计算惩罚项（tool_calls）
        6. 更新 metadata["reward_stats"]
        7. 返回 (final_reward, is_success)
        """
        judge_start_time = time.time()
        
        try:
            metadata = workflow_output.metadata
            
            # 1. 提取输入数据
            history = metadata.get("conversation_history", [])
            query = metadata.get("query") or getattr(workflow_task.task, "main_query", "")
            task_id = metadata.get("task_id") or getattr(workflow_task.task, "task_id", "")
            rubrics = metadata.get("rubrics")  # 可能是 None 或 list of dicts
            step_reward = metadata.get("reward_stats", {}).get("step_reward", 0.0)
            chat_date = metadata.get("chat_date") if metadata else datetime.now().strftime("%Y-%m-%d")
            
            if not history:
                print(f"⚠️ Empty conversation history for task_id={task_id}")
                return 0.0, False
            
            # 1.5 RM Gallery 评估（如果启用）
            ref_ans, domain = self._get_reference_data(task_id)
            assistants = [extract_text_content(m["content"]) for m in history if m["role"] == "assistant"]
            
            # RM Gallery 耗时记录
            rm_start_time = time.time()
            if self._rm_enabled and self.rm_evaluator:
                rm_raw = self._evaluate_with_rm_gallery(query, assistants[-1] if assistants else "", ref_ans, task_id, domain)
            else:
                rm_raw = 0.0
            rm_time = time.time() - rm_start_time
            
            # 2. 转换为 OpenJudge 输入格式
            openjudge_sample = self._convert_to_openjudge_format(
                history=history,
                query=query,
                task_id=task_id,
                rubrics=rubrics,
                chat_date=chat_date
            )
            
            if openjudge_sample.get('messages'):
                last_msg = openjudge_sample['messages'][-1]
            
            # 3. 调用 OpenJudge Runner.arun（异步）
            grading_start_time = time.time()
            grader_results = self._run_openjudge_evaluation([openjudge_sample])
            grading_time = time.time() - grading_start_time

            
            # 4. 提取各 grader 分数（arun 返回 Dict[str, List[GraderScore]]，这里取第一条）
            grader_scores, quota_exceeded_flags = self._extract_grader_scores(grader_results)
            
            # 4.5 如果有分数为0的grader，保存调试信息到单独文件
            self._save_zero_score_debug(
                grader_scores=grader_scores,
                grader_results=grader_results,
                query=query,
                history=history,
                report=assistants[-1] if assistants else "",
                task_id=task_id
            )
            
            # 5. 加权融合（包含 RM Gallery 和 OpenJudge Graders）
            fused_reward, contributions = self._fuse_grader_scores(grader_scores, rm_raw)
            
            # 6. 计算惩罚项（保留原有的 tool_calls 惩罚逻辑）
            # 从 log_metrics 中提取 tool_stats（deep_finance.py 将其放在 log_metrics 而非 metadata）
            tool_stats = workflow_output.log_metrics.get("tool_stats", {})
            tool_calls = tool_stats.get("total_calls", 0)
            penalty = self._compute_penalty(tool_calls)
            if penalty < 0:
                print(f"⚠️ Penalty applied: penalty={penalty}, tool_calls={tool_stats}")
            
            # 7. 汇总
            final_reward = fused_reward + step_reward + penalty
            
            judge_total_time = time.time() - judge_start_time
            
            # 8. 更新元数据（实例化 RewardStats）
            time_stats = {
                "rm_time": rm_time,
                "grading_time": grading_time,
                "judge_total_time": judge_total_time,
            }
            self._update_metadata_stats(
                metadata=metadata,
                final_reward=final_reward,
                fused_reward=fused_reward,
                penalty=penalty,
                step_reward=step_reward,
                grader_scores=grader_scores,
                contributions=contributions,
                time_stats=time_stats,
                rm_raw=rm_raw,
                quota_exceeded_flags=quota_exceeded_flags
            )
            
            print(f"DeepFinanceJudgeByOpenJudge: task_id={task_id}, fused={fused_reward:.4f}, final={final_reward:.4f}, rm_time={rm_time:.2f}s, grading_time={grading_time:.2f}s, total={judge_total_time:.2f}s")
            
            # 9. 判断是否成功（可根据实际需求调整阈值）
            is_success = final_reward >= 0.7
            
            return final_reward, is_success
        
        except Exception as e:
            print(f"✗ Error in OpenJudge compute_reward: {e}")
            import traceback
            traceback.print_exc()
            return 0.0, False
    
    def _convert_to_openjudge_format(
        self,
        history: List[Dict],
        query: str,
        task_id: str,
        rubrics: Optional[Any],
        chat_date: Optional[str]
    ) -> Dict[str, Any]:
        """
        将训练框架的 conversation_history 转换为 OpenJudge 的输入格式
        
        输入：
        - history: [{"role": "user/assistant/tool", "content": ..., "tool_calls": ...}, ...]
        
        输出：
        - {
            "messages": [...],  # OpenJudge 格式
            "chat_date": "YYYY-MM-DD",
            "rubrics": [...]
          }
        """
        # 1. 规范化 messages
        messages = []
        for msg in history:
            content = extract_text_content(msg.get("content", ""))
            normalized_msg = {
                "role": msg.get("role", "user"),
                "content": content
            }
            
            # 透传 tool_calls 等字段（OpenJudge 需要）
            for field in ["tool_calls", "tool_call_id", "name"]:
                if field in msg:
                    normalized_msg[field] = msg[field]
            
            messages.append(normalized_msg)

        
        # 3. 转换 rubrics 格式（如果存在）
        # OpenJudge 期望的格式：[{"dimension": ..., "description": ..., "check_points": [...]}, ...]
        openjudge_rubrics = []
        if rubrics:
            if isinstance(rubrics, list):
                openjudge_rubrics = rubrics
            elif isinstance(rubrics, dict):
                # 如果 rubrics 是 dict，尝试转换
                # 假设格式类似 {"criteria": [...], "scoring_dimensions": [...]}
                if "criteria" in rubrics:
                    for criterion in rubrics.get("criteria", []):
                        openjudge_rubrics.append({
                            "dimension": criterion.get("name", ""),
                            "description": criterion.get("description", ""),
                            "check_points": criterion.get("check_points", [])
                        })
        
        return {
            "messages": messages,
            "chat_date": chat_date,
            "rubrics": openjudge_rubrics
        }
    
    def _run_openjudge_evaluation(self, dataset: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        调用 OpenJudge Runner.arun 进行评估（带重试机制）
        
        输入：
        - dataset: List[Dict] - OpenJudge 格式的样本列表
        
        输出：
        - Dict[str, List[GraderScore]] - 每个 grader 的评分结果
        
        注意：GradingRunner 必须在当前事件循环中创建，因为其内部 Semaphore 会绑定事件循环
        """
        result = {}
        judge_instance = self  # 保存引用以便在 async 函数中访问
        max_retries = 3  # 最大重试次数
        
        async def run_with_retry():
            nonlocal result
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # 在当前事件循环中创建 Runner（避免 Semaphore 绑定错误的事件循环）
                    runner = judge_instance._create_runner_in_loop()
                    result = await runner.arun(dataset)
                    return  # 成功则直接返回
                except Exception as e:
                    last_exception = e
                    error_str = str(e)
                    
                    # 判断是否为可重试的连接错误
                    is_connection_error = any(keyword in error_str for keyword in [
                        "Connection", "connection", "TCPTransport", 
                        "SSLWantReadError", "BrokenPipe", "timeout",
                        "closed", "APIConnectionError"
                    ])
                    
                    if is_connection_error and attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                        print(f"⚠️ OpenJudge connection error (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s... Error: {error_str[:100]}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # 非连接错误或已达最大重试次数
                        raise last_exception
            
            # 所有重试都失败
            if last_exception:
                raise last_exception
        
        try:
            # 创建新的标准 asyncio 事件循环，并设置为当前线程的事件循环
            # 这样可以避免 Semaphore 绑定到不同事件循环的问题
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)  # 关键：将新循环设置为当前线程的事件循环
            try:
                loop.run_until_complete(run_with_retry())
            finally:
                loop.close()
                asyncio.set_event_loop(None)  # 清理：避免引用已关闭的循环
        except Exception as e:
            print(f"✗ OpenJudge Runner.arun failed after {max_retries} attempts: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _extract_grader_scores(self, grader_results: Dict[str, List[Any]]) -> Tuple[Dict[str, float], Dict[str, bool]]:
        """
        从 Runner.arun 结果中提取各 grader 的分数
        
        输入：
        - grader_results: Dict[str, List[GraderScore]]
          {
              "presentation_quality": [GraderScore(score=0.88, reason="...", metadata={...})],
              ...
          }
        
        输出：
        - Tuple[Dict[str, float], Dict[str, bool]]
          - scores: 每个 grader 的分数（取第一条采样的分数）
          - quota_exceeded_flags: 每个 grader 是否发生 429 quota exceeded
        """
        scores = {}
        quota_exceeded_flags = {}
        
        for grader_name, score_list in grader_results.items():
            quota_exceeded_flags[grader_name] = False
            if score_list and len(score_list) > 0:
                # 取第一条采样的分数（因为每次只评估一条）
                grader_score = score_list[0]
                
                # DEBUG: 记录详细信息
                reason_str = getattr(grader_score, 'reason', None)
                print(f"  [DEBUG] {grader_name}: score={getattr(grader_score, 'score', 'N/A')}, reason={str(reason_str)[:300] if reason_str else 'N/A'}")
                if hasattr(grader_score, "score"):
                    scores[grader_name] = grader_score.score
                    # 检测错误类型：分数为0且有错误信息
                    if grader_score.score == 0.0 and hasattr(grader_score, "reason"):
                        reason = str(grader_score.reason) if grader_score.reason else ""
                        # 检测 429 quota exceeded
                        if "429" in reason or "insufficient_quota" in reason or "exceeded your current quota" in reason:
                            quota_exceeded_flags[grader_name] = True
                else:
                    # 如果出错，设为 0
                    scores[grader_name] = 0.0
                    print(f"  [DEBUG] {grader_name}: no 'score' attr, grader_score={grader_score}")
            else:
                scores[grader_name] = 0.0
        
        print(f"  [OpenJudge Scores] {scores}")
        if any(quota_exceeded_flags.values()):
            quota_graders = [k for k, v in quota_exceeded_flags.items() if v]
            print(f"  [OpenJudge QuotaExceeded] {quota_graders}")
        return scores, quota_exceeded_flags
    
    def _fuse_grader_scores(self, grader_scores: Dict[str, float], rm_raw: float = 0.0) -> Tuple[float, Dict[str, float]]:
        """
        加权融合各 grader 的分数（包含 RM Gallery 和 OpenJudge Graders）
        
        输入：
        - grader_scores: Dict[str, float] - 各 grader 的原始分数
        - rm_raw: float - RM Gallery 原始分数
        
        输出：
        - (fused_reward, contributions)
          - fused_reward: 加权后的总分
          - contributions: Dict[str, float] - 各 grader 的贡献分数
        """
        contributions = {}
        
        # 添加 RM Gallery 贡献
        contributions["rm_contribution"] = self.w.get("rm", 0.0) * rm_raw
        
        # 添加 OpenJudge Graders 贡献（包括 citation_audit）
        for grader_name, weight in self.w.items():
            if grader_name == "rm":
                continue  # 已单独处理
            score = grader_scores.get(grader_name, 0.0)
            contributions[grader_name] = weight * score
        
        fused_reward = sum(contributions.values())
        
        return fused_reward, contributions
    
    def _evaluate_with_rm_gallery(self, query: str, current: str, reference: str, task_id: str, domain: str) -> float:
        """使用 RM Gallery 评估"""
        if not self.rm_evaluator or not domain or not reference:
            return 0.0
        try:
            from rm_gallery.core.data.schema import DataSample
            sample = DataSample(
                unique_id=task_id,
                input=[{"role": "user", "content": query}],
                output=[
                    {"answer": {"role": "assistant", "content": current, "label": {"model_name": "training"}}, "steps": None},
                    {"answer": {"role": "assistant", "content": reference, "label": {"model_name": "reference"}}, "steps": None},
                ],
                task_category="financial_analysis", source="finance_samples", metadata={"domain": domain}
            )
            result = self.rm_evaluator.evaluate(sample)
            self._save_rm_log(result, query, task_id)
            return result.metadata["dimension_scores"]["overall_score"]["training"]
        except Exception as e:
            print(f"✗ RM Gallery evaluation failed: {e}")
            return 0.0
    
    def _save_rm_log(self, result, query: str, task_id: str):
        """保存 RM Gallery 评估日志"""
        try:
            log = {
                "task_id": task_id,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "scores": result.metadata.get("dimension_scores", {})
            }
            save_dir = "./outputs/rm_evaluation_logs"
            os.makedirs(save_dir, exist_ok=True)
            with open(os.path.join(save_dir, f"rmeval_{datetime.now().strftime('%Y%m%d')}.json"), "a") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def _save_zero_score_debug(
        self,
        grader_scores: Dict[str, float],
        grader_results: Dict[str, List[Any]],
        query: str,
        history: List[Dict],
        report: str,
        task_id: str
    ):
        """
        当有 grader 分数为 0 时，保存详细调试信息到单独文件
        
        保存内容包括：
        - query: 用户查询
        - traj: 对话历史
        - report: 最终报告（前500字）
        - zero_score_reasons: 得 0 分的原因
        """
        try:
            # 检查是否有分数为 0 的 grader
            zero_score_graders = [name for name, score in grader_scores.items() if score == 0.0]
            if not zero_score_graders:
                return
            
            # 提取得 0 分的原因
            zero_score_reasons = {}
            for grader_name in zero_score_graders:
                if grader_name in grader_results:
                    score_list = grader_results[grader_name]
                    if score_list and len(score_list) > 0:
                        grader_score = score_list[0]
                        reason = getattr(grader_score, 'reason', None)
                        zero_score_reasons[grader_name] = str(reason) if reason else "N/A"
                    else:
                        zero_score_reasons[grader_name] = "empty score_list"
                else:
                    zero_score_reasons[grader_name] = "grader not in results"
            
            # 构建调试日志
            debug_log = {
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "report": report if report else "",
                "trajectory": history,
                "grader_scores": grader_scores,
                "zero_score_graders": zero_score_graders,
                "zero_score_reasons": zero_score_reasons
            }
            
            # 保存到单独文件
            save_dir = "/mnt/data_cpfs/taoshuchang.tsc/deepresearch/AgentJet_new/tutorial/example_deep_finance/outputs/reward_zero_debug"
            os.makedirs(save_dir, exist_ok=True)
            log_file = os.path.join(save_dir, f"zeroscore_{datetime.now().strftime('%Y%m%d')}.jsonl")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(debug_log, ensure_ascii=False) + "\n")
            
            print(f"  [ZERO SCORE DEBUG] task_id={task_id}, zero_graders={zero_score_graders}, saved to {log_file}")
            
        except Exception as e:
            print(f"⚠️ Failed to save zero score debug: {e}")
            pass
    
    def _compute_penalty(self, tool_calls: int) -> float:
        """
        计算工具调用惩罚（保留原有逻辑）
        
        - 0 次调用：-1.0
        - 1-2 次：-0.5
        - 3+ 次：0.0
        """
        if tool_calls == 0:
            return -1.0
        elif tool_calls <= 2:
            return -0.5
        else:
            return 0.0
    
    def _update_metadata_stats(
        self,
        metadata: Dict[str, Any],
        final_reward: float,
        fused_reward: float,
        penalty: float,
        step_reward: float,
        grader_scores: Dict[str, float],
        contributions: Dict[str, float],
        time_stats: Dict[str, float],
        rm_raw: float = 0.0,
        quota_exceeded_flags: Optional[Dict[str, bool]] = None
    ):
        """
        更新 metadata["reward_stats"] - 直接使用 OpenJudge 原始字段
        
        OpenJudge graders（按实际启用情况）：
        - presentation_quality: 报告呈现质量评估
        
        注意：不再硬套 RewardStats 的字段名，直接使用 openjudge_ 前缀
        """
        quota_exceeded_flags = quota_exceeded_flags or {}
        
        # 计算 quota exceeded 统计
        quota_exceeded_count = sum(1 for v in quota_exceeded_flags.values() if v)
        quota_exceeded_any = quota_exceeded_count > 0
        
        # 基础分数
        stats_dict = {
            "final_reward": final_reward,
            "fused_reward": fused_reward,
            "penalty": penalty,
            "step_reward": step_reward,
            "openjudge_enabled": True,
            # RM Gallery 相关
            "rm_enabled": self._rm_enabled,
            "rm_raw": rm_raw,
            "rm_weight": self.w.get("rm", 0.0),
            "rm_contribution": contributions.get("rm_contribution", 0.0),
        }
        
        # OpenJudge grader 原始分数（dimensions）
        for grader_name, score in grader_scores.items():
            stats_dict[f"openjudge_{grader_name}_raw"] = score
            stats_dict[f"openjudge_{grader_name}_weight"] = self.w.get(grader_name, 0.0)
        
        # OpenJudge grader 加权贡献（contribution）
        for grader_name, contrib in contributions.items():
            stats_dict[f"openjudge_{grader_name}_contribution"] = contrib
        
        # 保留原始字典便于调试
        stats_dict["openjudge_grader_scores"] = grader_scores
        stats_dict["openjudge_contributions"] = contributions
        
        # 注入耗时统计
        if time_stats:
            stats_dict.update(time_stats)
        
        metadata["reward_stats"] = stats_dict
    
    def _save_evaluation_log(self, task_id: str, grader_results: Dict[str, List[Any]], query: str):
        """
        保存 OpenJudge 评估日志（可选）
        """
        try:
            log = {
                "task_id": task_id,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "grader_results": {}
            }
            
            # 简化 grader_results 以便序列化
            for grader_name, score_list in grader_results.items():
                log["grader_results"][grader_name] = []
                for score in score_list:
                    if hasattr(score, "score"):
                        log["grader_results"][grader_name].append({
                            "score": score.score,
                            "reason": score.reason[:200] if hasattr(score, "reason") else "",
                        })
            
            save_dir = "./outputs/openjudge_logs"
            os.makedirs(save_dir, exist_ok=True)
            
            log_file = os.path.join(save_dir, f"openjudge_{datetime.now().strftime('%Y%m%d')}.json")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
                
        except Exception as e:
            print(f"⚠️ Failed to save evaluation log: {e}")
            pass

