# -*- coding: utf-8 -*-
"""
Analyst Agent - Based on AgentScope ReActAgent
Performs analysis using tools and LLM
"""
from typing import Any, Dict, Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory, LongTermMemoryBase
from agentscope.message import Msg

from ..config.constants import ANALYST_TYPES
from ..utils.progress import progress
from .prompt_loader import PromptLoader

_prompt_loader = PromptLoader()


class AnalystAgent(ReActAgent):
    """
    Analyst Agent - Uses LLM for tool selection and analysis
    Inherits from AgentScope's ReActAgent
    """

    def __init__(
        self,
        analyst_type: str,
        toolkit: Any,
        model: Any,
        formatter: Any,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        long_term_memory: Optional[LongTermMemoryBase] = None,
    ):
        """
        Initialize Analyst Agent

        Args:
            analyst_type: Type of analyst (e.g., "fundamentals", etc.)
            toolkit: AgentScope Toolkit instance
            model: LLM model instance
            formatter: Message formatter instance
            agent_id: Agent ID (defaults to "{analyst_type}_analyst")
            config: Configuration dictionary
            long_term_memory: Optional ReMeTaskLongTermMemory instance
        """
        if analyst_type not in ANALYST_TYPES:
            raise ValueError(
                f"Unknown analyst type: {analyst_type}. "
                f"Must be one of: {list(ANALYST_TYPES.keys())}",
            )

        self.analyst_type_key = analyst_type
        self.analyst_persona = ANALYST_TYPES[analyst_type]["display_name"]

        if agent_id is None:
            agent_id = analyst_type

        self.config = config or {}

        sys_prompt = self._load_system_prompt()

        kwargs = {
            "name": agent_id,
            "sys_prompt": sys_prompt,
            "model": model,
            "formatter": formatter,
            "toolkit": toolkit,
            "memory": InMemoryMemory(),
            "max_iters": 10,
        }
        if long_term_memory:
            kwargs["long_term_memory"] = long_term_memory
            kwargs["long_term_memory_mode"] = "static_control"

        super().__init__(**kwargs)

    def _load_system_prompt(self) -> str:
        """Load system prompt for analyst"""
        personas_config = _prompt_loader.load_yaml_config(
            "analyst",
            "personas",
        )
        persona = personas_config.get(self.analyst_type_key, {})

        # Get focus items and format as bullet points
        focus_items = persona.get("focus", [])
        focus_text = "\n".join(f"- {item}" for item in focus_items)

        # Get description
        description = persona.get("description", "").strip()

        return _prompt_loader.load_prompt(
            "analyst",
            "system",
            variables={
                "analyst_type": self.analyst_persona,
                "focus": focus_text,
                "description": description,
            },
        )

    async def reply(self, x: Msg = None) -> Msg:
        """
        Override reply method to add progress tracking

        Args:
            x: Input message (content must be str)

        Returns:
            Response message (content is str)
        """
        ticker = None
        if x and hasattr(x, "metadata") and x.metadata:
            ticker = x.metadata.get("tickers")

        if ticker:
            progress.update_status(
                self.name,
                ticker,
                f"Starting {self.analyst_persona} analysis",
            )

        result = await super().reply(x)

        if ticker:
            progress.update_status(
                self.name,
                ticker,
                "Analysis completed",
            )

        return result
