# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from openjudge.graders.base_grader import BaseGrader
from openjudge.graders.schema import GraderScore

try:
    from openjudge.models import OpenAIChatModel
except Exception:  # pragma: no cover
    from openjudge.models.openai_chat_model import OpenAIChatModel

from .prompt import EBTU_SYSTEM_PROMPT, EBTU_USER_PROMPT_TEMPLATE
from .json_utils import (
    strict_load_json,
    validate_shape,
    coerce_to_messages_list,
    construct_ebtu_prompt,
    count_digit_tokens,
)


class EBTUTraceabilityGrader(BaseGrader):
    """
    Evidence-Backed Trace Units (EBTU) Grader

    Input:
      - traj or record JSON that contains trajectory messages

    Output:
      - GraderScore(score in [0,1], reason with compact stats)
    """

    def __init__(
        self,
        model: Optional[OpenAIChatModel] = None,
        name: str = "ebtu_traceability",
        temperature: float = 0.0,
        max_tokens: int = 2600,
        model_name: str = "qwen-flash",
    ) -> None:
        super().__init__(name=name)
        self.model = model or OpenAIChatModel(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

    async def _aevaluate(self, traj: Any, **kwargs: Any) -> GraderScore:
        messages = coerce_to_messages_list(traj)

        # 输入有效性检查
        if not messages:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: empty or invalid trajectory",
            )

        user_prompt, report_plain = construct_ebtu_prompt(messages, EBTU_USER_PROMPT_TEMPLATE)

        judge_messages = [
            {"role": "system", "content": EBTU_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # 模型调用（带异常保护）
        try:
            resp = await self.model.achat(judge_messages)
            raw_text = getattr(resp, "content", None)
            if raw_text is None:
                raw_text = str(resp)
        except Exception as e:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"ModelCallError: {type(e).__name__}: {e}",
            )

        try:
            obj = strict_load_json(str(raw_text))
            norm = validate_shape(obj)

            score = self._compute_score(norm, report_plain)
            reason = self._build_reason(norm, report_plain, score)
            return GraderScore(name=self.name, score=score, reason=reason)
        except Exception as e:
            snippet = str(raw_text)[:200].replace("\n", " ")
            return GraderScore(name=self.name, score=0.0, reason=f"EBTU parse error: {e}; raw[:200]={snippet}")

    def _compute_score(self, norm: Dict[str, Any], report_plain: str) -> float:
        stats = norm["stats"]
        units = norm["units"]

        hard_total = max(1, int(stats.get("hard_units", 0)))
        supported = int(stats.get("supported", 0))
        contradicted = int(stats.get("contradicted", 0))
        no_evidence = int(stats.get("no_evidence", 0))
        unclear = int(stats.get("unclear", 0))
        misattrib = int(stats.get("misattrib", 0))
        anchored_hard = max(1, int(stats.get("anchored_hard_units", 0)))

        # Base: reward supported; penalize contradicted/no_evidence strongly; unclear mildly
        base = (supported - 1.4 * contradicted - 0.9 * no_evidence - 0.4 * unclear) / hard_total
        base = max(0.0, min(1.0, base))

        # Misattribution penalty: anchors exist but not supported (wrong anchor / wrong use)
        misattrib_rate = misattrib / anchored_hard
        misattrib_factor = max(0.0, 1.0 - 0.7 * misattrib_rate)

        # Deterministic coverage heuristics based on report digit tokens
        digit_tokens = count_digit_tokens(report_plain)
        expected_min_units = min(25, max(6, digit_tokens // 2))
        extracted_units = max(1, len(units))
        selection_factor = min(1.0, extracted_units / expected_min_units) if expected_min_units > 0 else 1.0

        # Optional judge-reported digit/date coverage (soft)
        reported_total = int(stats.get("report_digit_date_tokens", 0))
        reported_cov = int(stats.get("covered_digit_date_tokens", 0))
        if reported_total > 0:
            cov_ratio = max(0.0, min(1.0, reported_cov / reported_total))
        else:
            cov_ratio = 1.0
        cov_factor = 0.65 + 0.35 * cov_ratio  # [0.65, 1.0]

        score = base * misattrib_factor * selection_factor * cov_factor
        return float(max(0.0, min(1.0, score)))

    def _build_reason(self, norm: Dict[str, Any], report_plain: str, score: float) -> str:
        s = norm["stats"]
        ex = norm.get("examples", {})
        best = ex.get("best_supported", [])
        worst = ex.get("worst_failed", [])
        digit_tokens = count_digit_tokens(report_plain)

        parts = [
            f"score={score:.3f}",
            f"units={s['total_units']}",
            f"hard={s['hard_units']}",
            f"sup={s['supported']}",
            f"ctr={s['contradicted']}",
            f"noev={s['no_evidence']}",
            f"unc={s['unclear']}",
            f"anch_hard={s['anchored_hard_units']}",
            f"misattrib={s['misattrib']}",
            f"report_digits≈{digit_tokens}",
        ]
        if best:
            parts.append(f"best={best[:1]}")
        if worst:
            parts.append(f"worst={worst[:1]}")
        return " | ".join(parts)
