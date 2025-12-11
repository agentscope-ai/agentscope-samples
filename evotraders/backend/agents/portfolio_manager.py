# -*- coding: utf-8 -*-
"""
Portfolio Manager Agent - Based on AgentScope ReActAgent
Responsible for decision-making (NOT trade execution)
"""

from typing import Any, Dict, Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory, LongTermMemoryBase
from agentscope.message import Msg, TextBlock
from agentscope.tool import Toolkit, ToolResponse

from ..utils.progress import progress
from .prompt_loader import PromptLoader

_prompt_loader = PromptLoader()


class PMAgent(ReActAgent):
    """
    Portfolio Manager Agent - Makes investment decisions

    Key features:
    1. PM outputs decisions only (action + quantity per ticker)
    2. Trade execution happens externally (in pipeline/executor)
    3. Supports both backtest and live modes
    """

    def __init__(
        self,
        name: str = "portfolio_manager",
        model: Any = None,
        formatter: Any = None,
        initial_cash: float = 100000.0,
        margin_requirement: float = 0.25,
        config: Optional[Dict[str, Any]] = None,
        long_term_memory: Optional[LongTermMemoryBase] = None,
    ):
        self.config = config or {}

        # Portfolio state
        self.portfolio = {
            "cash": initial_cash,
            "positions": {},
            "margin_used": 0.0,
            "margin_requirement": margin_requirement,
        }

        # Decisions made in current cycle
        self._decisions: Dict[str, Dict] = {}

        # Create toolkit
        toolkit = self._create_toolkit()

        sys_prompt = _prompt_loader.load_prompt("portfolio_manager", "system")

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
            kwargs["long_term_memory_mode"] = "both"

        super().__init__(**kwargs)

    def _create_toolkit(self) -> Toolkit:
        """Create toolkit with decision recording tool"""
        toolkit = Toolkit()
        toolkit.register_tool_function(self._make_decision)
        return toolkit

    def _make_decision(
        self,
        ticker: str,
        action: str,
        quantity: int,
        confidence: int = 50,
        reasoning: str = "",
    ) -> ToolResponse:
        """
        Record a trading decision for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            action: Decision - "long", "short" or "hold"
            quantity: Number of shares to trade (0 for hold)
            confidence: Confidence level 0-100
            reasoning: Explanation for this decision

        Returns:
            ToolResponse confirming decision recorded
        """
        if action not in ["long", "short", "hold"]:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Invalid action: {action}. "
                        "Must be 'long', 'short', or 'hold'.",
                    ),
                ],
            )

        self._decisions[ticker] = {
            "action": action,
            "quantity": quantity if action != "hold" else 0,
            "confidence": confidence,
            "reasoning": reasoning,
        }

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Decision recorded: {action} "
                    f"{quantity} shares of {ticker}"
                    f" (confidence: {confidence}%)",
                ),
            ],
        )

    async def reply(self, x: Msg = None) -> Msg:
        """
        Make investment decisions

        Returns:
            Msg with decisions in metadata
        """
        if x is None:
            return Msg(
                name=self.name,
                content="No input provided",
                role="assistant",
            )

        # Clear previous decisions
        self._decisions = {}

        progress.update_status(
            self.name,
            None,
            "Analyzing and making decisions",
        )

        result = await super().reply(x)

        progress.update_status(self.name, None, "Completed")

        # Attach decisions to metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata["decisions"] = self._decisions.copy()
        result.metadata["portfolio"] = self.portfolio.copy()

        return result

    def get_decisions(self) -> Dict[str, Dict]:
        """Get decisions from current cycle"""
        return self._decisions.copy()

    def get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        return self.portfolio.copy()

    def load_portfolio_state(self, portfolio: Dict[str, Any]):
        """Load portfolio state"""
        if not portfolio:
            return
        self.portfolio = {
            "cash": portfolio.get("cash", self.portfolio["cash"]),
            "positions": portfolio.get("positions", {}).copy(),
            "margin_used": portfolio.get("margin_used", 0.0),
            "margin_requirement": portfolio.get(
                "margin_requirement",
                self.portfolio["margin_requirement"],
            ),
        }

    def update_portfolio(self, portfolio: Dict[str, Any]):
        """Update portfolio after external execution"""
        self.portfolio.update(portfolio)
