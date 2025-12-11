# -*- coding: utf-8 -*-
"""
Risk Manager Agent - Based on AgentScope ReActAgent
Uses LLM for risk assessment
"""
from typing import Any, Dict, Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory, LongTermMemoryBase
from agentscope.message import Msg
from agentscope.tool import Toolkit

from ..utils.progress import progress
from .prompt_loader import PromptLoader

_prompt_loader = PromptLoader()


class RiskAgent(ReActAgent):
    """
    Risk Manager Agent - Uses LLM for risk assessment
    Inherits from AgentScope's ReActAgent
    """

    def __init__(
        self,
        model: Any,
        formatter: Any,
        name: str = "risk_manager",
        config: Optional[Dict[str, Any]] = None,
        long_term_memory: Optional[LongTermMemoryBase] = None,
    ):
        """
        Initialize Risk Manager Agent

        Args:
            model: LLM model instance
            formatter: Message formatter instance
            name: Agent name
            config: Configuration dictionary
            long_term_memory: Optional ReMeTaskLongTermMemory instance
        """
        self.config = config or {}

        sys_prompt = self._load_system_prompt()

        # Create dedicated toolkit for this agent
        toolkit = Toolkit()

        kwargs = {
            "name": name,
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
        """Load system prompt for risk manager"""
        return _prompt_loader.load_prompt(
            "risk_manager",
            "system",
        )

    async def reply(self, x: Msg = None) -> Msg:
        """
        Provide risk assessment

        Args:
            x: Input message (content must be str)

        Returns:
            Msg with risk warnings (content is str)
        """
        progress.update_status(self.name, None, "Assessing risk")

        result = await super().reply(x)

        progress.update_status(self.name, None, "Risk assessment completed")

        return result
