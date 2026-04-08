"""Grounding Grader - Citation compliance evaluation (OpenJudge version)"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from openjudge.graders.base_grader import BaseGrader
from openjudge.graders.schema import GraderScore

# Compatible with both import paths
try:
    from openjudge.models import OpenAIChatModel
except Exception:  # pragma: no cover
    from openjudge.models.openai_chat_model import OpenAIChatModel

from .prompt import GROUNDING_SYSTEM_PROMPT, GROUNDING_USER_PROMPT_TEMPLATE
from .json_utils import strict_load_json, validate_shape, construct_reward_prompt


class GroundingGrader(BaseGrader):
    """
    Citation Compliance Grader

    - Input: traj (full conversation trajectory)
    - Output: GraderScore(name, score, reason)
    - score: composite score in [0,1]
      - citation_coverage_score: citation coverage (0.5 weight)
      - grounding_score: citation truthfulness (0.5 weight)
      - invalid_penalty: penalty for invalid citations (up to 0.5)
    - determinism: recommend temperature=0 + disable thinking
    - parse failure: score=0, error shown in reason
    """

    def __init__(
        self,
        model: OpenAIChatModel,
        name: str = "grounding",
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
        Create a default model.
        You may also instantiate OpenAIChatModel directly without this factory.
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")

        extra_body: Dict[str, Any] = {}
        if deterministic:
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
        traj: Any,
        **_: Any,
    ) -> GraderScore:
        """
        Entry point: must receive traj (full conversation trajectory)
        
        Args:
            traj: Conversation trajectory, format: [{"role": ..., "content": ...}, ...]
                  or {"messages": [...]} format
        
        Returns:
            GraderScore(name, score, reason)
        """
        # 1. Extract messages (compatible with both formats)
        if isinstance(traj, dict):
            messages_list = traj.get("messages", [])
        elif isinstance(traj, list):
            messages_list = traj
        else:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: traj must be list or dict with 'messages'",
            )
        
        if not messages_list:
            return GraderScore(
                name=self.name,
                score=0.0,
                reason="BadInput: empty trajectory",
            )

        # 2. Build prompt
        user_prompt = construct_reward_prompt(messages_list, GROUNDING_USER_PROMPT_TEMPLATE)
        
        messages = [
            {"role": "system", "content": GROUNDING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        # 3. Call model
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

        # 4. Parse JSON
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

        # 5. Compute score
        score, reason = self._compute_scores(obj)
        return GraderScore(name=self.name, score=score, reason=reason)

    def _compute_scores(self, obj: Dict[str, Any]) -> Tuple[float, str]:
        """
        Compute score from LLM results.

        Args:
            obj: LLM returned JSON containing total_key_facts, cited_key_facts, fake_count, etc.

        Returns:
            (score, reason) tuple
        """
        total_key_facts = obj.get('total_key_facts', 0)
        cited_key_facts = obj.get('cited_key_facts', 0)
        fake_count = obj.get('fake_count', 0)
        missing_count = obj.get('missing_count', 0)

        # invalid refs: structural/traceability issues
        invalid_reference_nums = obj.get('invalid_reference_nums', [])
        if not isinstance(invalid_reference_nums, list):
            invalid_reference_nums = []
        invalid_ref_count = len(invalid_reference_nums)
        
        # Edge case: no key facts, return 0 directly
        if total_key_facts == 0:
            citation_coverage_score = 0.0
            grounding_score = 0.0
        else:
            # coverage: citation coverage rate
            citation_coverage_score = cited_key_facts / total_key_facts
            
            # grounding: citation truthfulness (ratio of non-fake among cited)
            if cited_key_facts == 0:
                grounding_score = 0.0
            else:
                grounding_score = max(0.0, 1 - fake_count / cited_key_facts)
        
        # Light penalty: invalid refs lower the reward
        # Each invalid ref deducts 0.1, up to 0.5 max
        # invalid_penalty = min(0.1 * invalid_ref_count, 0.5)
        invalid_penalty = 0

        # final_reward: composite score (weight 0.5:0.5), plus invalid penalty
        final_reward = 0.5 * citation_coverage_score + 0.5 * grounding_score
        # final_reward = max(0.0, final_reward - invalid_penalty)
        
        # Build reason
        good_citations = obj.get('good_citations', [])
        good_str = "; ".join(str(x)[:50] for x in good_citations[:2]) if good_citations else ""
        
        parts: List[str] = [
            f"total={total_key_facts}",
            f"cited={cited_key_facts}",
            f"missing={missing_count}",
            f"fake={fake_count}",
            f"invalid={invalid_ref_count}",
            f"coverage={citation_coverage_score:.3f}",
            f"grounding={grounding_score:.3f}",
            f"penalty={invalid_penalty:.2f}",
        ]
        if good_str:
            parts.append(f"good:[{good_str}]")
        
        reason = " | ".join(parts)
        return round(final_reward, 6), reason[:800]
