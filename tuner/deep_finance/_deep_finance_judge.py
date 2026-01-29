# -*- coding: utf-8 -*-
"""
DeepFinance Judge Engine (Tuner style)

Goal
----
Adapt the AJet-style DeepFinance judge to tuner-style judge_func(task, response, ...).

Current scope (per request)
--------------------------
- ONLY compute presentation_quality
- Disable RM-Gallery / grounding / tool-penalty / action-loop reward
- Tools/trajectory integration is intentionally left as "best-effort":
  - If response.metadata["conversation_history"] exists, we will use it.
  - Otherwise we fall back to a minimal history built from task["init_messages"] + final response.

Environment variables
---------------------
Required for OpenJudge model (OpenAI-compatible endpoint):
- OPENJUDGE_BASE_URL
- OPENJUDGE_API_KEY

Model name is read from (in order):
- env: OPENJUDGE_LLM_MODEL
- env: OPENJUDGE_MODEL
- default: "gpt-4o-mini"   (override via env to avoid surprises)

Grader dependency
-----------------
Directly imports from tuner.deep_finance.judge:
- PresentationQualityGrader: 报告呈现质量评估
- GroundingGrader: 引用规范性评估
"""

from __future__ import annotations

import os
import time
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from judge import PresentationQualityGrader, GroundingGrader

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeepFinanceJudgeConfig:
    openjudge_llm: str
    concurrency: int = 6

    # env vars for OpenAI-compatible client
    base_url_env: str = "OPENJUDGE_BASE_URL"
    api_key_env: str = "OPENJUDGE_API_KEY"

    # when True, missing base_url/api_key raises an error
    strict_env: bool = True

    @staticmethod
    def from_env() -> "DeepFinanceJudgeConfig":
        model = (
            os.environ.get("OPENJUDGE_LLM_MODEL")
            or os.environ.get("OPENJUDGE_MODEL")
            or "gpt-4o-mini"
        )
        concurrency = int(os.environ.get("OPENJUDGE_CONCURRENCY", "6"))
        strict_env = os.environ.get("OPENJUDGE_STRICT_ENV", "1") not in ("0", "false", "False")
        return DeepFinanceJudgeConfig(
            openjudge_llm=model,
            concurrency=concurrency,
            strict_env=strict_env,
        )


class DeepFinanceJudgeEngine:
    """
    A process-local reusable judge engine.
    - Reuses OpenJudge model client across calls
    - Creates a new GradingRunner inside the current event loop per call
      (Runner contains a Semaphore bound to the loop).
    
    Graders:
    - presentation_quality: 报告呈现质量评估
    - grounding: 引用规范性评估
    """

    def __init__(self, cfg: DeepFinanceJudgeConfig):
        self.cfg = cfg
        self._model: Any = None  # OpenJudge OpenAIChatModel instance (lazy)
        self._pq_grader_cls: Any = None  # PresentationQualityGrader class (lazy)
        self._grounding_grader_cls: Any = None  # GroundingGrader class (lazy)

    # ----------------------------
    # Lazy initialization helpers
    # ----------------------------
    def _require_env(self, key: str) -> str:
        v = os.environ.get(key)
        if not v and self.cfg.strict_env:
            raise RuntimeError(
                f"Missing required env var: {key}. "
                f"Set {self.cfg.base_url_env} / {self.cfg.api_key_env} for OpenJudge."
            )
        return v or ""

    def _load_pq_grader_cls(self) -> Any:
        if self._pq_grader_cls is not None:
            return self._pq_grader_cls

        self._pq_grader_cls = PresentationQualityGrader
        return self._pq_grader_cls

    def _load_grounding_grader_cls(self) -> Any:
        if self._grounding_grader_cls is not None:
            return self._grounding_grader_cls

        self._grounding_grader_cls = GroundingGrader
        return self._grounding_grader_cls

    def _init_openjudge_model(self) -> Any:
        if self._model is not None:
            return self._model

        base_url = self._require_env(self.cfg.base_url_env)
        api_key = self._require_env(self.cfg.api_key_env)

        # OpenJudge model wrapper (try both import paths for robustness)
        try:
            from openjudge.models import OpenAIChatModel  # type: ignore
        except Exception:  # pragma: no cover
            from openjudge.models.openai_chat_model import OpenAIChatModel  # type: ignore

        self._model = OpenAIChatModel(
            model=self.cfg.openjudge_llm,
            base_url=base_url,
            api_key=api_key,
        )
        return self._model

    # ----------------------------
    # OpenJudge runner construction
    # ----------------------------
    def _create_runner_in_loop(self) -> Any:
        """
        Create a new GradingRunner bound to the current event loop.
        """
        model = self._init_openjudge_model()
        pq_cls = self._load_pq_grader_cls()
        grounding_cls = self._load_grounding_grader_cls()

        # OpenJudge runner classes
        from openjudge.runner.grading_runner import GraderConfig, GradingRunner  # type: ignore

        def extract_user_query(data: Dict[str, Any]) -> str:
            for msg in data.get("messages", []) or []:
                if msg.get("role") == "user":
                    return str(msg.get("content", "") or "")
            return ""

        def extract_report_content(data: Dict[str, Any]) -> str:
            # Last assistant message as report
            msgs = data.get("messages", []) or []
            for msg in reversed(msgs):
                if msg.get("role") == "assistant":
                    return _extract_text_content(msg.get("content"))
            return ""

        grader_configs = {
            # 报告呈现质量评估 - 需要 user_query 和 report_content
            "presentation_quality": GraderConfig(
                grader=pq_cls(model=model),
                mapper=lambda data: {
                    "user_query": extract_user_query(data),
                    "report_content": extract_report_content(data),
                },
            ),
            # 引用规范性评估 - 需要完整的 traj
            "grounding": GraderConfig(
                grader=grounding_cls(model=model),
                mapper=lambda data: {"traj": data},
            ),
        }

        return GradingRunner(
            grader_configs=grader_configs,
            max_concurrency=self.cfg.concurrency,
            show_progress=False,
        )

    # ----------------------------
    # Public API
    # ----------------------------
    async def evaluate_one(self, task: Dict[str, Any], response: Any) -> Tuple[float, Dict[str, Any]]:
        """
        Returns:
          reward: float  (presentation_quality score)
          metrics: Dict  (debuggable details)
        """
        t0 = time.time()

        task_id = _coalesce_str(
            _get_metadata(response, "task_id"),
            task.get("task_id"),
            task.get("id"),
        ) or "unknown"

        query = _coalesce_str(
            _get_metadata(response, "query"),
            task.get("query"),
            task.get("question"),
            task.get("main_query"),
        )

        rubrics = _get_metadata(response, "rubrics")
        if rubrics is None:
            rubrics = (task.get("metadata") or {}).get("rubrics", None)

        chat_date = _coalesce_str(
            _get_metadata(response, "chat_date"),
            (task.get("metadata") or {}).get("chat_date"),
        ) or datetime.now().strftime("%Y-%m-%d")

        # Best-effort history
        history = _get_metadata(response, "conversation_history")
        if not isinstance(history, list) or not history:
            init_messages = task.get("init_messages") if isinstance(task.get("init_messages"), list) else []
            history = _build_minimal_history(init_messages, query, response)

        sample = {
            "id": task_id,
            "messages": _normalize_messages(history),
            "chat_date": chat_date,
            "rubrics": rubrics,
        }

        grader_results = await self._arun_with_retry([sample], retries=3)

        # Extract presentation_quality scores
        pq_score, pq_reason, pq_meta, pq_quota_exceeded = _extract_single_grader_score(
            grader_results.get("presentation_quality")
        )

        # Extract grounding scores
        grounding_score, grounding_reason, grounding_meta, grounding_quota_exceeded = _extract_single_grader_score(
            grader_results.get("grounding")
        )

        # Combine scores (weighted average: 0.5 each)
        reward = 0.5 * float(pq_score or 0.0) + 0.5 * float(grounding_score or 0.0)
        quota_exceeded = pq_quota_exceeded or grounding_quota_exceeded

        metrics: Dict[str, Any] = {
            # Combined reward
            "reward": reward,
            # presentation_quality details
            "presentation_quality": float(pq_score or 0.0),
            "presentation_quality_reason": pq_reason,
            "presentation_quality_metadata": pq_meta,
            # grounding details
            "grounding": float(grounding_score or 0.0),
            "grounding_reason": grounding_reason,
            "grounding_metadata": grounding_meta,
            # General info
            "openjudge_model": self.cfg.openjudge_llm,
            "openjudge_concurrency": self.cfg.concurrency,
            "quota_exceeded": quota_exceeded,
            "task_id": task_id,
            "elapsed_sec": round(time.time() - t0, 4),
        }
        return reward, metrics

    async def _arun_with_retry(self, dataset: List[Dict[str, Any]], retries: int = 3) -> Dict[str, List[Any]]:
        """
        Call runner.arun(dataset) with small retry logic for transient errors.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(max(1, retries)):
            try:
                runner = self._create_runner_in_loop()
                return await runner.arun(dataset)
            except Exception as e:
                last_exc = e
                msg = str(e)
                retryable = any(k in msg for k in ("Connection", "connection", "TCP", "timeout", "Timeout", "429"))
                if attempt < retries - 1 and retryable:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise

        # Unreachable, but keep type-checker happy
        raise last_exc  # type: ignore[misc]


# ----------------------------
# Utilities
# ----------------------------
def _get_metadata(response: Any, key: str) -> Any:
    md = getattr(response, "metadata", None)
    if isinstance(md, dict) and key in md:
        return md.get(key)
    # Some Msg implementations may store extras in a dict-like field
    if isinstance(response, dict):
        return response.get("metadata", {}).get(key)
    return None


def _coalesce_str(*vals: Any) -> str:
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _extract_text_content(content: Any) -> str:
    """
    Normalize various message content shapes into plain text.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # e.g., [{"type": "text", "text": "..."}]
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in ("text", "output_text") and item.get("text") is not None:
                    parts.append(str(item.get("text")))
                elif item.get("type") == "tool_result" and item.get("output") is not None:
                    parts.append(str(item.get("output")))
                else:
                    # best-effort
                    if "text" in item:
                        parts.append(str(item.get("text")))
        return "\n".join([p for p in parts if p])
    if isinstance(content, dict):
        # tool_result-like objects
        if content.get("type") == "tool_result" and content.get("output") is not None:
            return str(content.get("output"))
        if "text" in content:
            return str(content.get("text"))
    return str(content)


def _build_minimal_history(init_messages: List[Dict[str, Any]], query: str, response: Any) -> List[Dict[str, Any]]:
    """
    Build a minimal conversation history for presentation_quality:
      - (optional) system from init_messages
      - user: query
      - assistant: response content
    """
    history: List[Dict[str, Any]] = []

    # include first system if present
    if isinstance(init_messages, list):
        for m in init_messages:
            if isinstance(m, dict) and m.get("role") == "system":
                history.append({"role": "system", "content": m.get("content", "")})
                break

    if query:
        history.append({"role": "user", "content": query})

    assistant_text = _extract_text_content(getattr(response, "content", None))
    if not assistant_text and isinstance(response, dict):
        assistant_text = _extract_text_content(response.get("content"))
    history.append({"role": "assistant", "content": assistant_text})

    return history


def _normalize_messages(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure each message has at least: role, content(str).
    Keep extra fields (tool_calls, tool_call_id, name) if present.
    """
    out: List[Dict[str, Any]] = []
    for m in history or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role", "") or "")
        content = m.get("content")
        mm = dict(m)
        mm["role"] = role
        mm["content"] = _extract_text_content(content)
        out.append(mm)
    return out


def _extract_single_grader_score(
    maybe_list: Any,
) -> Tuple[float, str, Dict[str, Any], bool]:
    """
    Supports OpenJudge returning a list with GraderScore-like objects.
    Returns: (score, reason, metadata, quota_exceeded)
    """
    if not isinstance(maybe_list, list) or not maybe_list:
        return 0.0, "", {}, False

    gs = maybe_list[0]
    score = 0.0
    reason = ""
    meta: Dict[str, Any] = {}
    quota_exceeded = False

    # object style
    if hasattr(gs, "score"):
        try:
            score = float(getattr(gs, "score"))
        except Exception:
            score = 0.0
    elif isinstance(gs, dict) and "score" in gs:
        try:
            score = float(gs.get("score") or 0.0)
        except Exception:
            score = 0.0

    if hasattr(gs, "reason"):
        reason = str(getattr(gs, "reason") or "")
    elif isinstance(gs, dict) and "reason" in gs:
        reason = str(gs.get("reason") or "")

    if hasattr(gs, "metadata"):
        md = getattr(gs, "metadata")
        if isinstance(md, dict):
            meta = md
    elif isinstance(gs, dict) and "metadata" in gs and isinstance(gs.get("metadata"), dict):
        meta = gs.get("metadata") or {}

    # quota detection (best-effort)
    if score == 0.0 and reason:
        if "429" in reason or "insufficient_quota" in reason or "exceeded your current quota" in reason:
            quota_exceeded = True

    return score, reason, meta, quota_exceeded
