"""Audit Grader - 引用逻辑审计 (OpenJudge logic version)"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from openjudge.graders.base_grader import BaseGrader
from openjudge.graders.schema import GraderScore

try:
    from openjudge.models import OpenAIChatModel
except Exception:
    from openjudge.models.openai_chat_model import OpenAIChatModel

from .prompt import CITATION_INTEGRITY_PROMPT_COT, CITATION_INTEGRITY_USER_TEMPLATE
from .json_utils import strict_load_json, validate_integrity_shape, construct_reward_prompt


class AuditGrader(BaseGrader):
    """
    引用逻辑审计 Grader
    
    - 输入：traj (完整对话轨迹)
    - 输出：GraderScore(score, reason)
    - score: integrity_score (Supported / Total)
    - reason: 审计摘要，包括错误分布和定性总结
    """

    def __init__(
        self,
        model: OpenAIChatModel,
        name: str = "citation_integrity",
        **kwargs: Any,
    ):
        super().__init__(name=name, **kwargs)
        self.model = model

    @staticmethod
    def create_default_model(
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        deterministic: bool = True,
        enable_thinking: bool = False,
        seed: int = 42,
    ) -> OpenAIChatModel:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")

        extra_body: Dict[str, Any] = {}
        if deterministic:
            extra_body.update(
                {
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "seed": seed,
                }
            )
        if enable_thinking is False:
            extra_body["enable_thinking"] = False

        kwargs: Dict[str, Any] = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        if extra_body:
            kwargs["extra_body"] = extra_body

        return OpenAIChatModel(**kwargs)

    async def _aevaluate(
        self,
        traj: Any,
        **_: Any,
    ) -> GraderScore:
        """
        入口：必须喂 traj（完整对话轨迹）
        
        Args:
            traj: 对话轨迹，支持以下格式：
                  - [{"role": ..., "content": ...}, ...] 直接消息列表
                  - {"messages": [...]} 包含 messages 字段的 dict
                  - {"traj": [[...]]} 包含 traj 字段的 dict（双重嵌套）
        
        Returns:
            GraderScore(name, score, reason)
        """
        # 1. 提取 messages（兼容多种格式）
        if isinstance(traj, dict):
            if "traj" in traj:
                # 支持 {"traj": [[...]]} 格式
                traj_list = traj["traj"]
                if traj_list and isinstance(traj_list[0], list):
                    messages_list = traj_list[0]
                else:
                    messages_list = traj_list
            else:
                messages_list = traj.get("messages", [])
        elif isinstance(traj, list):
            messages_list = traj
        else:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: traj must be list or dict with 'messages'/'traj'",
            )
        
        if not messages_list:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: empty trajectory",
            )

        # 2. 构建 Prompt
        # 使用新的 System Prompt 和 User Template
        user_prompt = construct_reward_prompt(messages_list, CITATION_INTEGRITY_USER_TEMPLATE)
        
        messages = [
            {"role": "system", "content": CITATION_INTEGRITY_PROMPT_COT},
            {"role": "user", "content": user_prompt}
        ]

        # 3. 模型推理
        try:
            resp = await self.model.achat(messages)
            raw_text = getattr(resp, "content", str(resp))
        except Exception as e:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"ModelCallError: {type(e).__name__}: {e}",
            )

        # 4. JSON 解析与验证
        obj, jerr = strict_load_json(raw_text)
        if obj is None:
            snippet = str(raw_text)[:200].replace("\n", " ")
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"ParseError: {jerr}; raw[:200]={snippet}",
            )

        # 使用新的验证逻辑 validate_integrity_shape
        obj, serr = validate_integrity_shape(obj)
        if obj is None:
            snippet = str(raw_text)[:200].replace("\n", " ")
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"SchemaError: {serr}; raw[:200]={snippet}",
            )

        # 5. 计算分数与生成理由
        score, reason = self._compute_scores(obj)
        return GraderScore(name=self.name, score=score, reason=reason)

    def _compute_scores(self, obj: Dict[str, Any]) -> Tuple[float, str]:
        """
        基于 audit_trail 和 integrity_score 计算最终结果
        """
        # 直接获取模型计算的 integrity_score，若缺失则手动计算
        audit_trail = obj.get("audit_trail", [])
        total_citations = len(audit_trail)
        
        # 统计各Verdict数量
        verdict_counts = {
            "Supported": 0,
            "Overstated": 0,
            "Contradicted": 0,
            "Hallucinated": 0,
            "Irrelevant": 0
        }
        
        for item in audit_trail:
            v = item.get("verdict", "Irrelevant")
            if v in verdict_counts:
                verdict_counts[v] += 1
            else:
                verdict_counts["Irrelevant"] += 1
        
        supported_count = verdict_counts["Supported"]
        
        # 优先使用模型输出的 score，如果有误则回退到手动计算
        # model_score = obj.get("integrity_score")
        # if isinstance(model_score, (float, int)) and 0.0 <= model_score <= 1.0:
        #     final_score = float(model_score)
        # else:
        final_score = supported_count / total_citations if total_citations > 0 else 0.0

        # 构建 Reason
        # 格式: Score: 0.80 | Total: 10 | Supp: 8, Over: 1, Hallu: 1 | Summary: ...
        stats_parts = []
        for k, v in verdict_counts.items():
            if v > 0:
                stats_parts.append(f"{k[:4]}:{v}") # 缩写 Verdict
        
        stats_str = ", ".join(stats_parts)
        qualitative = obj.get("qualitative_summary", "No summary provided.")
        
        # 截取主要错误示例 (如果有)
        errors = [x for x in audit_trail if x.get("verdict") != "Supported"]
        error_msg = ""
        if errors:
            first_err = errors[0]
            error_msg = f" | Example Error ([{first_err.get('citation_id')}]) {first_err.get('verdict')}: {first_err.get('logic_analysis')}"

        reason = (
            f"Score: {final_score:.2f} | Total: {total_citations} | {stats_str} | "
            f"Summary: {qualitative}{error_msg}"
        )

        return round(final_score, 4), reason[:1000]