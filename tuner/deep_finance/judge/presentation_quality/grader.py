# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from openjudge.graders.base_grader import BaseGrader
from openjudge.graders.schema import GraderScore

# Compatible with both import paths (both appear in docs)
try:
    from openjudge.models import OpenAIChatModel
except Exception:  # pragma: no cover
    from openjudge.models.openai_chat_model import OpenAIChatModel

from .prompt import (
    QUALITY_SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    ALL_KEYS,
    A_KEYS,
    B_KEYS,
    C_KEYS,
)
from .json_utils import strict_load_json, validate_shape, get_score, get_note


class PresentationQualityGrader(BaseGrader):
    """
    - Input: report_content (research report text)
    - Output: GraderScore(name, score, reason)
    - Score: 8 items rated on 1/3/5 scale, total normalized to [0,1] (total/40)
    - Determinism: recommend temperature=0 + disable thinking (see create_default_model)
    - Parse failure: score=0, error shown in reason
    """

    def __init__(
        self,
        model: OpenAIChatModel,
        name: str = "presentation_quality",
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
        seed: int = 0,
    ) -> OpenAIChatModel:
        """
        You may also skip this factory and directly instantiate OpenAIChatModel.
        QuickStart docs confirm OpenAIChatModel reads from OPENAI_API_KEY/OPENAI_BASE_URL.
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")

        extra_body: Dict[str, Any] = {}
        if deterministic:
            # Common fields for OpenAI-compatible APIs; DashScope/Qwen uses enable_thinking
            extra_body.update(
                {
                    "temperature": 0,
                    "top_p": 1,
                    "seed": seed,
                    "presence_penalty": 0,
                    "frequency_penalty": 0,
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
        report_content: str,
        user_query: str | None = None,
        **_: Any,
    ) -> GraderScore:
        """
        Entry point: directly feed report_content (research report text)
        - user_query is optional: used to fill prompt; defaults to "(unknown)" if not provided
        """

        # DEBUG: check input arguments
        import logging

        logger = logging.getLogger("PresentationQualityGrader")
        logger.warning("[DEBUG] _aevaluate called")
        logger.warning(
            "[DEBUG] report_content type: %s",
            type(report_content),
        )
        logger.warning(
            "[DEBUG] report_content is None: %s",
            report_content is None,
        )
        logger.warning(
            "[DEBUG] report_content length: %s",
            len(report_content) if report_content else 0,
        )
        logger.warning(
            "[DEBUG] report_content preview (first 500 chars): %s",
            (report_content or "")[:500],
        )
        logger.warning(
            "[DEBUG] user_query: %s",
            (user_query or "")[:200],
        )

        report = (report_content or "").strip()

        # Clean markdown code block markers
        report = self._strip_markdown_fences(report)
        # breakpoint()
        if not report:
            print("Empty report_content")
            logger.warning(
                "[DEBUG] EMPTY report after strip! original was: %s",
                (report_content or "")[:200],
            )
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: empty report_content",
            )

        uq = (user_query or "").strip() or "(unknown)"

        user_content = USER_PROMPT_TEMPLATE.format(
            user_query=uq,
            report_content=report,
        )
        messages = [
            {"role": "system", "content": QUALITY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # Core: OpenJudge's OpenAIChatModel supports await model.achat([...]) and returns .content
        try:
            resp = await self.model.achat(messages)
            raw_text = getattr(resp, "content", None)
            if raw_text is None:
                raw_text = str(resp)
        except Exception as e:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"ModelCallError: {type(e).__name__}: {e}",
            )

        obj, jerr = strict_load_json(str(raw_text))
        if obj is None:
            snippet = str(raw_text)[:200].replace("\n", " ")
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"ParseError: {jerr}; raw[:200]={snippet}",
            )

        obj, serr = validate_shape(obj)
        if obj is None:
            snippet = str(raw_text)[:200].replace("\n", " ")
            return GraderScore(
                name=self.name,
                score=0.0,
                reason=f"SchemaError: {serr}; raw[:200]={snippet}",
            )

        score, reason = self._score_and_reason(obj)

        return GraderScore(name=self.name, score=score, reason=reason)

    def _score_and_reason(self, obj: Dict[str, Any]) -> Tuple[float, str]:
        scan = obj["scan"]
        structuring = obj["structuring"]
        editorial = obj["editorial"]
        top_fixes = obj.get("top_fixes", [])

        # 8 items scored on 1/3/5 scale (deterministic: computed entirely in Python)
        score_map: Dict[str, int] = {}
        note_map: Dict[str, str] = {}

        def take(section: Dict[str, Any], key: str):
            item = section.get(key)
            score_map[key] = get_score(item)
            note_map[key] = get_note(item)

        for k in A_KEYS:
            take(scan, k)
        for k in B_KEYS:
            take(structuring, k)
        for k in C_KEYS:
            take(editorial, k)

        # Total = sum of scores / max possible (8*5=40), normalized to [0,1]
        total_score = sum(score_map.get(k, 1) for k in ALL_KEYS)
        max_score = len(ALL_KEYS) * 5  # 8 * 5 = 40
        score = total_score / float(max_score)

        # reason: sorted by score, list low-scoring items
        low_items = [
            (k, score_map.get(k, 1))
            for k in ALL_KEYS
            if score_map.get(k, 1) < 5
        ]
        low_items.sort(key=lambda x: x[1])  # Sort ascending
        low_str = ", ".join(
            f"{k}={s}({note_map.get(k,'')})" for k, s in low_items[:4]
        )
        fixes_str = " | ".join(str(x) for x in (top_fixes or [])[:3])

        parts: List[str] = []
        parts.append(f"Score {total_score}/{max_score}")
        if low_items:
            parts.append(f"Low: {low_str}")
        if fixes_str:
            parts.append(f"TopFixes: {fixes_str}")

        reason = " ; ".join(parts)
        return round(score, 6), reason[:800]

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """
        Strip markdown code block markers.
        - Remove leading ```markdown / ```md / ``` etc.
        - Remove trailing ```
        """
        text = text.strip()
        # Remove leading ```xxx
        text = re.sub(
            r"^```(?:markdown|md)?\s*\n?", "", text, flags=re.IGNORECASE
        )
        # Remove trailing ```
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()
