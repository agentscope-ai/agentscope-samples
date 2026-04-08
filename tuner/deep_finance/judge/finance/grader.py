# -*- coding: utf-8 -*-
"""Finance Composition Evaluator - OpenJudge-based finance evaluator

Features:
- Load reference answers
- Route to corresponding grader set based on domain
- Execute pairwise evaluation (compare training answer vs reference answer)
- Return score in [0, 1] range
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, List, Type

from openjudge.models.openai_chat_model import OpenAIChatModel
from openjudge.graders.base_grader import BaseGrader

# Finance Graders from OpenJudge cookbooks
from cookbooks.finance_grader.stock_analysis.valuation_analysis import ValuationAnalysisGrader
from cookbooks.finance_grader.macro_analysis.macro_analysis import MacroAnalysisGrader
from cookbooks.finance_grader.industry_research.characteristics_analysis import CharacteristicsAnalysisGrader
from cookbooks.finance_grader.event_interpretation.event_analysis import EventAnalysisGrader
from cookbooks.finance_grader.stock_search.search_relevance import SearchRelevanceGrader

logger = logging.getLogger(__name__)


def load_reference_answers_from_file(file_path: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load reference answers (required by FinanceCompositionEvaluator)."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Reference answers file not found: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ref_answers, ref_domains = {}, {}
        for item in data:
            task_id = item.get("task", {}).get("task_id")
            if not task_id or "answer" not in item: 
                continue
            ref_answers[task_id] = item["answer"]
            domain = item.get("task", {}).get("metadata", {}).get("domain")
            if domain: 
                ref_domains[task_id] = domain
        return ref_answers, ref_domains
    except Exception as e:
        raise ValueError(f"Error loading reference answers: {e}")


class FinanceCompositionEvaluator:
    """
    OpenJudge-based Finance Composition Evaluator (replaces rm_gallery.FinanceComposition)

    Features:
    - Route to corresponding grader set based on domain
    - Execute pairwise evaluation (compare training answer vs reference answer)
    - Return score in [0, 1] range
    """
    
    DOMAIN_GRADERS: Dict[str, List[Type[BaseGrader]]] = {
        "stock_analysis": [ValuationAnalysisGrader],
        "industry_research": [CharacteristicsAnalysisGrader],
        "macro_analysis": [MacroAnalysisGrader],
        "event_interpretation": [EventAnalysisGrader],
        "stock_search": [SearchRelevanceGrader],
    }
    
    def __init__(self, model: OpenAIChatModel, params: Dict[str, Any] = None):
        self.model = model
        self.params = params or {}
        self._grader_cache: Dict[str, List[BaseGrader]] = {}
        
    def _get_graders_for_domain(self, domain: str) -> List[BaseGrader]:
        if domain not in self._grader_cache:
            grader_classes = self.DOMAIN_GRADERS.get(domain, [])
            self._grader_cache[domain] = [
                grader_cls(model=self.model) for grader_cls in grader_classes
            ]
        return self._grader_cache[domain]
    
    async def aevaluate(self, query: str, current: str, reference: str, domain: str) -> float:
        if not domain or domain not in self.DOMAIN_GRADERS:
            return 0.5
            
        graders = self._get_graders_for_domain(domain)
        if not graders:
            return 0.5
        
        scores = []
        for grader in graders:
            try:
                result = await grader.aevaluate(
                    query=query,
                    answer_1=current,
                    answer_2=reference,
                )
                if hasattr(result, 'rank') and isinstance(result.rank, list):
                    scores.append(1.0 if result.rank[0] == 1 else 0.0)
                else:
                    scores.append(0.5)
            except Exception as e:
                logger.warning(f"FinanceCompositionEvaluator grader failed: {e}")
                scores.append(0.5)
        
        return sum(scores) / len(scores) if scores else 0.5
