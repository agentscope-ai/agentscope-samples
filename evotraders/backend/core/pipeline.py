# -*- coding: utf-8 -*-
"""
Core Pipeline - Orchestrates multi-agent analysis and decision-making
"""

# flake8: noqa: E501
# pylint: disable=W0613,C0301

import json
import logging
import os
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from agentscope.message import Msg
from agentscope.pipeline import MsgHub

from backend.utils.settlement import SettlementCoordinator
from backend.utils.terminal_dashboard import get_dashboard
from backend.core.state_sync import StateSync
from backend.utils.trade_executor import PortfolioTradeExecutor


logger = logging.getLogger(__name__)


def _log(msg: str):
    """Log to dashboard if available, otherwise to logger"""
    dashboard = get_dashboard()
    if dashboard.live:
        dashboard.log(msg)
    else:
        logger.info(msg)


class TradingPipeline:
    """
    Trading Pipeline - Orchestrates the complete trading cycle

    Flow:
    1. Clear agent short-term memory (avoid cross-day context pollution)
    2. Analysts analyze stocks
    3. Risk Manager provides risk assessment
    4. PM makes decisions (direction + quantity)
    5. Execute trades with provided prices
    6. Reflection phase: broadcast closing P&L, agents record to long-term memory

    Real-time updates via StateSync after each agent completes.
    """

    def __init__(
        self,
        analysts: List[Any],
        risk_manager: Any,
        portfolio_manager: Any,
        state_sync: Optional["StateSync"] = None,
        settlement_coordinator: Optional[SettlementCoordinator] = None,
        max_comm_cycles: Optional[int] = None,
    ):
        self.analysts = analysts
        self.risk_manager = risk_manager
        self.pm = portfolio_manager
        self.state_sync = state_sync
        self.settlement_coordinator = settlement_coordinator
        self.max_comm_cycles = max_comm_cycles or int(
            os.getenv("MAX_COMM_CYCLES", "2"),
        )
        self.conference_summary = None  # Store latest conference summary

    async def run_cycle(
        self,
        tickers: List[str],
        date: str,
        prices: Optional[Dict[str, float]] = None,
        close_prices: Optional[Dict[str, float]] = None,
        market_caps: Optional[Dict[str, float]] = None,
        get_open_prices_fn: Optional[
            Callable[[], Awaitable[Dict[str, float]]]
        ] = None,
        get_close_prices_fn: Optional[
            Callable[[], Awaitable[Dict[str, float]]]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Run one complete trading cycle

        Args:
            tickers: List of stock tickers
            date: Trading date (YYYY-MM-DD)
            prices: Open prices {ticker: price} (for backtest)
            close_prices: Close prices for settlement (for backtest)
            market_caps: Optional market caps for baseline calculation
            get_open_prices_fn: Async callback to wait for open prices (live mode)
            get_close_prices_fn: Async callback to wait for close prices (live mode)

        For live mode:
        - Analysis runs immediately
        - Execution waits for market open via get_open_prices_fn
        - Settlement waits for market close via get_close_prices_fn

        Each agent's result is broadcast immediately via StateSync.
        """
        _log(f"Starting cycle {date} - {len(tickers)} tickers")

        # Phase 0: Clear short-term memory to avoid cross-day context pollution
        _log("Phase 0: Clearing memory")
        await self._clear_all_agent_memory()

        participants = self.analysts + [self.risk_manager, self.pm]

        # Single MsgHub for entire cycle - no nesting
        async with MsgHub(
            participants=participants,
            announcement=Msg(
                "system",
                f"Starting analysis cycle for {date}. Tickers: {', '.join(tickers)}",
                "system",
            ),
        ):
            # Phase 1.1: Analysts
            _log("Phase 1.1: Analyst analysis")
            analyst_results = await self._run_analysts_with_sync(tickers, date)

            # Phase 1.2: Risk Manager
            _log("Phase 1.2: Risk assessment")
            risk_assessment = await self._run_risk_manager_with_sync(
                tickers,
                date,
                prices,
            )

            # Phase 2.1: Conference discussion (within same MsgHub)
            _log("Phase 2.1: Conference discussion")
            conference_summary = await self._run_conference_cycles(
                tickers=tickers,
                date=date,
                prices=prices,
                analyst_results=analyst_results,
                risk_assessment=risk_assessment,
            )
            self.conference_summary = conference_summary

            # Phase 2.2: Analysts generate final structured predictions
            _log("Phase 2.2: Analysts generate final structured predictions")
            final_predictions = await self._collect_final_predictions(
                tickers,
                date,
            )

            # Record final predictions for leaderboard ranking
            if self.settlement_coordinator:
                self.settlement_coordinator.record_analyst_predictions(
                    final_predictions,
                )

            # Live mode: wait for market open before execution
            if get_open_prices_fn:
                _log("Waiting for market open...")
                prices = await get_open_prices_fn()
                _log(f"Got open prices: {prices}")

            # Phase 3: PM makes decisions
            _log("Phase 3.1: PM makes decisions")
            pm_result = await self._run_pm_with_sync(
                tickers,
                date,
                prices,
                analyst_results,
                risk_assessment,
            )

        # Phase 4: Execute decisions
        _log("Phase 4: Executing trades")
        decisions = pm_result.get("decisions", {})
        execution_result = self._execute_decisions(decisions, prices, date)

        # Live mode: wait for market close before settlement
        if get_close_prices_fn:
            _log("Waiting for market close")
            close_prices = await get_close_prices_fn()
            _log(f"Got close prices: {close_prices}")

        # Phase 5: Settlement - run after close prices available
        settlement_result = None
        if close_prices and self.settlement_coordinator:
            _log("Phase 5: Daily review and generate memories")

            agent_trajectories = await self._capture_agent_trajectories()

            if market_caps is None:
                market_caps = {ticker: 1e9 for ticker in tickers}

            settlement_result = (
                self.settlement_coordinator.run_daily_settlement(
                    date=date,
                    tickers=tickers,
                    open_prices=prices,
                    close_prices=close_prices,
                    market_caps=market_caps,
                    agent_portfolio=execution_result.get("portfolio", {}),
                    analyst_results=analyst_results,
                    pm_decisions=decisions,
                )
            )

            await self._run_reflection(
                date=date,
                agent_trajectories=agent_trajectories,
                analyst_results=analyst_results,
                decisions=decisions,
                executed_trades=execution_result.get("executed_trades", []),
                open_prices=prices,
                close_prices=close_prices,
                settlement_result=settlement_result,
                conference_summary=self.conference_summary,
            )

        _log(f"Cycle complete: {date}")

        return {
            "analyst_results": analyst_results,
            "risk_assessment": risk_assessment,
            "pm_decisions": decisions,
            "executed_trades": execution_result.get("executed_trades", []),
            "portfolio": execution_result.get("portfolio", {}),
            "settlement_result": settlement_result,
        }

    async def _clear_all_agent_memory(self):
        """Clear short-term memory for all agents"""
        for analyst in self.analysts:
            await analyst.memory.clear()

        await self.risk_manager.memory.clear()
        await self.pm.memory.clear()

    async def _sync_memory_if_retrieved(self, agent: Any) -> None:
        """
        Check agent's short-term memory for retrieved long-term memory and sync to frontend.

        AgentScope's ReActAgent adds a Msg with name="long_term_memory" when
        memory is retrieved in static_control mode.
        """
        if not self.state_sync:
            return

        try:
            msgs = await agent.memory.get_memory()
            for msg in msgs:
                if getattr(msg, "name", None) == "long_term_memory":
                    content = self._extract_text_content(msg.content)
                    if content:
                        parsed = self._parse_memory_content(content)
                        await self.state_sync.on_memory_retrieved(
                            agent_id=agent.name,
                            content=parsed,
                        )
                    break  # Only sync the first (most recent) memory retrieval
        except Exception as e:
            logger.warning(f"Failed to sync memory for {agent.name}: {e}")

    def _parse_memory_content(self, content: str) -> str:
        """
        Parse memory content to extract rewritten_context from JSON format.

        AgentScope ReMe memory wraps content in <long_term_memory> tags with JSON.
        """
        # Try to extract JSON from the content
        print("memory content:\n", content)

        json_match = re.search(
            r"<long_term_memory>.*?```json\s*(\{[\s\S]*?\})\s*```\s*</long_term_memory>",
            content,
            re.DOTALL,
        )
        if not json_match:
            json_match = re.search(
                r'\{[^{}]*"rewritten_context"[^{}]*\}',
                content,
                re.DOTALL,
            )

        if json_match:
            try:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                return data.get("rewritten_context", "")
            except json.JSONDecodeError:
                pass

        # Fallback: strip XML tags and return cleaned content
        content = re.sub(r"</?long_term_memory>", "", content)
        content = re.sub(
            r"The content below are retrieved from long-term memory.*?:\s*",
            "",
            content,
        )
        return content.strip()

    async def _capture_agent_trajectories(self) -> Dict[str, List[Msg]]:
        """
        Capture execution trajectories from all agents' short-term memory

        This should be called BEFORE clearing memory to preserve the
        complete execution trajectory for long-term memory recording.

        Returns:
            Dict mapping agent name to list of Msg objects (the trajectory)
        """
        trajectories = {}

        # Capture analyst trajectories
        for analyst in self.analysts:
            try:
                msgs = await analyst.memory.get_memory()
                if msgs:
                    trajectories[analyst.name] = list(msgs)
            except Exception as e:
                logger.warning(
                    f"Failed to capture trajectory for {analyst.name}: {e}",
                )

        # Capture risk manager trajectory
        try:
            msgs = await self.risk_manager.memory.get_memory()
            if msgs:
                trajectories["risk_manager"] = list(msgs)
        except Exception as e:
            logger.warning(
                f"Failed to capture trajectory for risk_manager: {e}",
            )

        # Capture PM trajectory
        try:
            msgs = await self.pm.memory.get_memory()
            if msgs:
                trajectories["portfolio_manager"] = list(msgs)
        except Exception as e:
            logger.warning(
                f"Failed to capture trajectory for portfolio_manager: {e}",
            )

        return trajectories

    async def _run_reflection(
        self,
        date: str,
        agent_trajectories: Dict[str, List[Msg]],
        analyst_results: List[Dict[str, Any]],
        decisions: Dict[str, Dict],
        executed_trades: List[Dict],
        open_prices: Optional[Dict[str, float]],
        close_prices: Optional[Dict[str, float]],
        settlement_result: Optional[Dict[str, Any]] = None,
        conference_summary: Optional[str] = None,
    ):
        """
        Run reflection phase after market close

        Calculates actual P&L and records execution trajectory to long-term memory

        Args:
            date: Trading date
            agent_trajectories: Dict mapping agent name to their execution trajectory
            analyst_results: Results from analyst agents
            decisions: PM decisions
            executed_trades: List of executed trades
            open_prices: Opening prices
            close_prices: Closing prices
            settlement_result: Optional settlement results with baseline performance
            conference_summary: Optional summary from conference discussion
        """
        # Calculate P&L for each trade
        trade_pnl = []
        for trade in executed_trades:
            ticker = trade["ticker"]
            action = trade["action"]
            quantity = trade["quantity"]
            entry_price = trade["price"]
            exit_price = close_prices.get(ticker, entry_price)

            if action == "long":
                pnl = (exit_price - entry_price) * quantity
            elif action == "short":
                pnl = (entry_price - exit_price) * quantity
            else:
                pnl = 0

            pnl_pct = (
                (pnl / (entry_price * quantity) * 100) if quantity > 0 else 0
            )

            trade_pnl.append(
                {
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                },
            )

        total_pnl = sum(t["pnl"] for t in trade_pnl)

        # Build reflection summary with settlement info
        reflection_content = self._build_reflection_content(
            date=date,
            analyst_results=analyst_results,
            decisions=decisions,
            trade_pnl=trade_pnl,
            total_pnl=total_pnl,
            settlement_result=settlement_result,
            conference_summary=conference_summary,
        )

        # Record execution trajectories to long-term memory for agents that support it
        # Score based on profitability: higher score for profitable days
        score = 1.0 if total_pnl > 0 else 0.0

        await self._record_to_long_term_memory(
            date=date,
            agent_trajectories=agent_trajectories,
            trade_pnl=trade_pnl,
            total_pnl=total_pnl,
            score=score,
        )

        # Broadcast reflection to StateSync
        if self.state_sync:
            await self.state_sync.on_agent_complete(
                agent_id="Daily Log",
                content=reflection_content,
            )

    def _build_reflection_content(
        self,
        date: str,
        analyst_results: List[Dict[str, Any]],
        decisions: Dict[str, Dict],
        trade_pnl: List[Dict],
        total_pnl: float,
        settlement_result: Optional[Dict[str, Any]] = None,
        conference_summary: Optional[str] = None,
    ) -> str:
        """Build human-readable reflection content"""
        lines = [f"Daily log for {date}:"]
        lines.append(f"Total P&L: ${total_pnl:,.2f}")
        lines.append("")

        if conference_summary:
            lines.append("Conference Discussion Summary:")
            lines.append(conference_summary)
            lines.append("")

        if settlement_result:
            baseline_values = settlement_result.get("baseline_values", {})
            initial = 100000.0
            lines.append("Baseline Comparison:")
            lines.append(
                f"  Equal Weight: ${baseline_values.get('equal_weight', 0):,.2f} "
                f"({(baseline_values.get('equal_weight', initial) - initial) / initial * 100:.2f}%)",
            )
            lines.append(
                f"  Market Cap Weighted: ${baseline_values.get('market_cap_weighted', 0):,.2f} "
                f"({(baseline_values.get('market_cap_weighted', initial) - initial) / initial * 100:.2f}%)",
            )
            lines.append(
                f"  Momentum: ${baseline_values.get('momentum', 0):,.2f} "
                f"({(baseline_values.get('momentum', initial) - initial) / initial * 100:.2f}%)",
            )
            lines.append("")

        if trade_pnl:
            lines.append("Trade Results:")
            for t in trade_pnl:
                pnl_sign = "+" if t["pnl"] >= 0 else ""
                lines.append(
                    f"  {t['ticker']}: {t['action'].upper()} {t['quantity']} @ "
                    f"${t['entry_price']:.2f} -> ${t['exit_price']:.2f}, "
                    f"P&L: {pnl_sign}${t['pnl']:.2f} ({pnl_sign}{t['pnl_pct']:.1f}%)",
                )
        else:
            lines.append("No trades executed today.")

        return "\n".join(lines)

    async def _record_to_long_term_memory(
        self,
        date: str,
        agent_trajectories: Dict[str, List[Msg]],
        trade_pnl: List[Dict],
        total_pnl: float,
        score: float,
    ):
        """
        Record execution trajectories to long-term memory for all agents

        This method records the actual execution trajectory (conversation history)
        from each agent's short-term memory. This allows the ReMe memory system
        to learn from the complete task execution flow, not just summaries.

        Args:
            date: Trading date
            agent_trajectories: Dict mapping agent name to their execution trajectory
            trade_pnl: P&L details for each trade
            total_pnl: Total P&L for the day
            score: Score for this trajectory (1.0 for profitable, 0.5 for loss)
        """
        # Build outcome message to append to trajectories
        outcome_msg = Msg(
            role="user",
            content=f"You are an analyst/financial manager, The Key point is to predict correctly and"
            f"have good P&L. The Definition of loss is when P&L < 0. "
            f"Focus on how to do good prediction but not only execution correctly."
            f"[Outcome] Trading day {date} - Total P&L: ${total_pnl:,.2f}. "
            f"{'Profitable day.' if total_pnl > 0 else 'Loss day.'}",
            name="system",
        )

        # Record for analysts
        for analyst in self.analysts:
            if (
                hasattr(analyst, "long_term_memory")
                and analyst.long_term_memory is not None
            ):
                trajectory = agent_trajectories.get(analyst.name, [])
                if trajectory:
                    # Append outcome to trajectory
                    trajectory_with_outcome = trajectory + [outcome_msg]
                    try:
                        await analyst.long_term_memory.record(
                            msgs=trajectory_with_outcome,
                            score=score,
                        )
                        logger.debug(
                            f"Recorded {len(trajectory_with_outcome)} messages "
                            f"to long-term memory for {analyst.name}",
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to record to long-term memory for {analyst.name}: {e}",
                        )

        # Record for risk manager
        if (
            hasattr(self.risk_manager, "long_term_memory")
            and self.risk_manager.long_term_memory is not None
        ):
            trajectory = agent_trajectories.get("risk_manager", [])
            if trajectory:
                trajectory_with_outcome = trajectory + [outcome_msg]
                try:
                    await self.risk_manager.long_term_memory.record(
                        msgs=trajectory_with_outcome,
                        score=score,
                    )
                    logger.debug(
                        f"Recorded {len(trajectory_with_outcome)} messages "
                        f"to long-term memory for risk_manager",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to record to long-term memory for risk_manager: {e}",
                    )

        # Record for PM with trade outcome details
        if (
            hasattr(self.pm, "long_term_memory")
            and self.pm.long_term_memory is not None
        ):
            trajectory = agent_trajectories.get("portfolio_manager", [])
            if trajectory:
                # Build detailed outcome message for PM
                pnl_details = []
                for t in trade_pnl:
                    pnl_sign = "+" if t["pnl"] >= 0 else ""
                    pnl_details.append(
                        f"{t['ticker']}: {t['action']} {t['quantity']} @ "
                        f"${t['entry_price']:.2f} -> ${t['exit_price']:.2f}, "
                        f"P&L: {pnl_sign}${t['pnl']:.2f}",
                    )

                pm_outcome_msg = Msg(
                    role="user",
                    content=f"[Outcome] Trading day {date}\n"
                    f"Total P&L: ${total_pnl:,.2f} "
                    f"({'Profitable' if total_pnl >= 0 else 'Loss'})\n"
                    f"Trade details:\n" + "\n".join(pnl_details)
                    if pnl_details
                    else f"[Outcome] Trading day {date}\n"
                    f"Total P&L: ${total_pnl:,.2f}\nNo trades executed.",
                    name="system",
                )
                trajectory_with_outcome = trajectory + [pm_outcome_msg]
                try:
                    await self.pm.long_term_memory.record(
                        msgs=trajectory_with_outcome,
                        score=score,
                    )
                    logger.debug(
                        f"Recorded {len(trajectory_with_outcome)} messages "
                        f"to long-term memory for portfolio_manager",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to record to long-term memory for portfolio_manager: {e}",
                    )

    async def _run_conference_cycles(
        self,
        tickers: List[str],
        date: str,
        prices: Optional[Dict[str, float]],
        analyst_results: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
    ) -> Optional[str]:
        """
        Run conference discussion cycles (within existing MsgHub context)

        No nested MsgHub - this runs inside the main cycle's MsgHub.

        Returns:
            Conference summary string generated by PM
        """
        if self.max_comm_cycles <= 0:
            _log(
                "Phase 2.1: Conference discussion - "
                "Conference skipped (disabled)",
            )
            return None

        conference_title = f"Investment Discussion - {date}"

        if self.state_sync:
            await self.state_sync.on_conference_start(
                title=conference_title,
                date=date,
            )

        # Run discussion cycles (no new MsgHub - use parent's)
        for cycle in range(self.max_comm_cycles):
            _log(
                "Phase 2.1: Conference discussion - "
                f"Conference {cycle + 1}/{self.max_comm_cycles}",
            )

            if self.state_sync:
                await self.state_sync.on_conference_cycle_start(
                    cycle=cycle + 1,
                    total_cycles=self.max_comm_cycles,
                )

            # PM sets agenda or asks questions
            pm_prompt = self._build_pm_discussion_prompt(
                cycle=cycle,
                tickers=tickers,
                date=date,
                prices=prices,
                analyst_results=analyst_results,
                risk_assessment=risk_assessment,
            )

            pm_msg = Msg(name="system", content=pm_prompt, role="user")
            pm_response = await self.pm.reply(pm_msg)

            if self.state_sync:
                pm_content = self._extract_text_content(pm_response.content)
                await self.state_sync.on_conference_message(
                    agent_id="portfolio_manager",
                    content=pm_content,
                )

            # Analysts share perspectives
            for analyst in self.analysts:
                analyst_prompt = self._build_analyst_discussion_prompt(
                    cycle=cycle,
                    tickers=tickers,
                    date=date,
                )

                analyst_msg = Msg(
                    name="system",
                    content=analyst_prompt,
                    role="user",
                )
                analyst_response = await analyst.reply(analyst_msg)

                if self.state_sync:
                    analyst_content = self._extract_text_content(
                        analyst_response.content,
                    )
                    await self.state_sync.on_conference_message(
                        agent_id=analyst.name,
                        content=analyst_content,
                    )

            if self.state_sync:
                await self.state_sync.on_conference_cycle_end(
                    cycle=cycle + 1,
                )

        # Generate conference summary by PM
        _log(
            "Phase 2.1: Conference discussion - Generating conference summary",
        )
        summary_prompt = (
            f"The conference discussion for {date} has concluded. "
            f"As Portfolio Manager, provide a concise summary of the key insights, "
            f"concerns, and consensus points discussed about {', '.join(tickers)}. "
            f"Highlight any critical factors that should be considered in the final decision-making."
        )
        summary_msg = Msg(name="system", content=summary_prompt, role="user")
        summary_response = await self.pm.reply(summary_msg)

        conference_summary = self._extract_text_content(
            summary_response.content,
        )

        _log(
            "Phase 2.1: Conference discussion - Conference summary generated",
        )

        if self.state_sync:
            await self.state_sync.on_conference_message(
                agent_id="conference summary",
                content=conference_summary,
            )
            await self.state_sync.on_conference_end()

        return conference_summary

    def _build_pm_discussion_prompt(
        self,
        cycle: int,
        tickers: List[str],
        date: str,
        prices: Optional[Dict[str, float]],
        analyst_results: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
    ) -> str:
        """Build PM discussion prompt with full context"""
        # Get current portfolio state
        portfolio = self.pm.get_portfolio_state()

        if cycle == 0:
            # First cycle: provide full context
            context_lines = [
                f"As Portfolio Manager, review the following information for {date}:",
                "",
                "=== Current Portfolio ===",
                f"Cash: ${portfolio.get('cash', 0):,.2f}",
                f"Positions: {json.dumps(portfolio.get('positions', {}), indent=2)}",
                "",
                "=== Current Prices ===",
                json.dumps(prices, indent=2),
                "",
                "=== Analyst Signals ===",
            ]

            # Add analyst results summary
            for result in analyst_results:
                agent_name = result.get("agent", "Unknown")
                content = result.get("content", "")
                context_lines.append(f"{agent_name}: {content}")

            context_lines.extend(
                [
                    "",
                    "=== Risk Assessment ===",
                    str(risk_assessment.get("content", "")),
                    "",
                    "Based on the above context, share your key concerns or questions about the opportunities in "
                    f"{', '.join(tickers)}. Do not make final decisions yet - this is a discussion phase.",
                ],
            )

            return "\n".join(context_lines)
        else:
            return (
                f"Continue the discussion. Share your thoughts on the perspectives raised "
                f"and any remaining concerns about {', '.join(tickers)}."
            )

    def _build_analyst_discussion_prompt(
        self,
        cycle: int,
        tickers: List[str],
        date: str,
    ) -> str:
        """Build analyst discussion prompt"""
        return (
            f"Share your perspective on the discussion so far. "
            f"Provide insights or address concerns raised by others about {', '.join(tickers)}. "
            f"Do not use tools - focus on sharing your professional opinion."
        )

    async def _collect_final_predictions(
        self,
        tickers: List[str],
        date: str,
    ) -> List[Dict[str, Any]]:
        """
        Collect final predictions from all analysts as simple text responses.
        Analysts provide their predictions in plain text without tool calls.
        """
        _log(
            "Phase 2.2: Analysts generate final structured predictions\n"
            f"  Starting _collect_final_predictions for {len(self.analysts)} analysts",
        )
        final_predictions = []

        for i, analyst in enumerate(self.analysts):
            _log(
                "Phase 2.2: Analysts generate final structured predictions\n"
                f"  Collecting prediction from analyst {i+1}/{len(self.analysts)}: {analyst.name}",
            )

            prompt = (
                f"Based on your analysis, provide your final prediction for {date}. "
                f"For each ticker ({', '.join(tickers)}), state: "
                f"TICKER: UP/DOWN/NEUTRAL (confidence: X%). "
                f"Do not use any tools, just respond with your predictions."
            )

            msg = Msg(name="system", content=prompt, role="user")
            _log(
                "Phase 2.2: Analysts generate final structured predictions\n"
                f"  Sending prediction request to {analyst.name}",
            )
            response = await analyst.reply(msg)
            _log(
                "Phase 2.2: Analysts generate final structured predictions\n"
                f" Received response from {analyst.name}",
            )

            # Parse predictions from text response
            content = self._extract_text_content(response.content)
            predictions_data = self._parse_predictions_from_text(
                content,
                tickers,
            )

            _log(
                "Phase 2.2: Analysts generate final structured predictions\n"
                f"  {analyst.name} final predictions: {predictions_data}",
            )

            final_predictions.append(
                {
                    "agent": analyst.name,
                    "predictions": predictions_data,
                    "raw_content": content,
                },
            )

            # if self.state_sync:
            #     await self.state_sync.on_agent_complete(
            #         agent_id=f"{analyst.name}_final_prediction",
            #         content=content,
            #     )

        return final_predictions

    def _parse_predictions_from_text(
        self,
        content: str,
        tickers: List[str],
    ) -> List[Dict[str, Any]]:
        """Parse predictions from analyst text response"""
        predictions = []
        content_upper = content.upper()

        for ticker in tickers:
            direction = "neutral"
            confidence = 0.5

            # Simple pattern matching for direction
            ticker_idx = content_upper.find(ticker)
            if ticker_idx >= 0:
                # Look at text near ticker mention
                context = content_upper[ticker_idx : ticker_idx + 100]
                if (
                    "UP" in context
                    or "BULLISH" in context
                    or "LONG" in context
                ):
                    direction = "up"
                    confidence = 0.7
                elif (
                    "DOWN" in context
                    or "BEARISH" in context
                    or "SHORT" in context
                ):
                    direction = "down"
                    confidence = 0.7

            predictions.append(
                {
                    "ticker": ticker,
                    "direction": direction,
                    "confidence": confidence,
                },
            )

        return predictions

    async def _run_analysts_with_sync(
        self,
        tickers: List[str],
        date: str,
    ) -> List[Dict[str, Any]]:
        """Run all analysts with real-time sync after each completion"""
        results = []

        for analyst in self.analysts:
            content = (
                f"Analyze the following stocks for date {date}: {', '.join(tickers)}. "
                f"Provide investment signals with confidence scores and reasoning."
            )

            msg = Msg(
                name="system",
                content=content,
                role="user",
                metadata={"tickers": tickers, "date": date},
            )

            result = await analyst.reply(msg)
            extracted = self._extract_result_from_msg(result)
            results.append(extracted)

            # Sync retrieved memory first
            await self._sync_memory_if_retrieved(analyst)

            # Broadcast agent result via StateSync
            if self.state_sync:
                text_content = self._extract_text_content(result.content)
                await self.state_sync.on_agent_complete(
                    agent_id=analyst.name,
                    content=text_content,
                )

        return results

    async def _run_analysts(
        self,
        tickers: List[str],
        date: str,
    ) -> List[Dict[str, Any]]:
        """Run all analysts (without sync, for backward compatibility)"""
        results = []

        for analyst in self.analysts:
            content = (
                f"Analyze the following stocks for date {date}: {', '.join(tickers)}. "
                f"Provide investment signals with confidence scores and reasoning."
            )

            msg = Msg(
                name="system",
                content=content,
                role="user",
                metadata={"tickers": tickers, "date": date},
            )

            result = await analyst.reply(msg)
            results.append(self._extract_result_from_msg(result))

        return results

    async def _run_risk_manager_with_sync(
        self,
        tickers: List[str],
        date: str,
        prices: Optional[Dict[str, float]],
    ) -> Dict[str, Any]:
        """Run risk manager assessment with real-time sync"""
        portfolio = self.pm.get_portfolio_state()

        context = {
            "portfolio": portfolio,
            "tickers": tickers,
            "date": date,
            "current_prices": prices,
        }
        content = (
            f"Assess risk for the following portfolio and market conditions:\n"
            f"{json.dumps(context, indent=2)}\n"
            f"Provide risk warnings and recommendations."
        )

        msg = Msg(name="system", content=content, role="user")
        result = await self.risk_manager.reply(msg)
        extracted = self._extract_result_from_msg(result)

        # Sync retrieved memory first
        await self._sync_memory_if_retrieved(self.risk_manager)

        # Broadcast agent result via StateSync
        if self.state_sync:
            text_content = self._extract_text_content(result.content)
            await self.state_sync.on_agent_complete(
                agent_id="risk_manager",
                content=text_content,
            )

        return extracted

    async def _run_risk_manager(
        self,
        tickers: List[str],
        date: str,
        prices: Dict[str, float],
    ) -> Dict[str, Any]:
        """Run risk manager assessment (without sync, for backward compatibility)"""
        portfolio = self.pm.get_portfolio_state()

        context = {
            "portfolio": portfolio,
            "tickers": tickers,
            "date": date,
            "current_prices": prices,
        }
        content = (
            f"Assess risk for the following portfolio and market conditions:\n"
            f"{json.dumps(context, indent=2)}\n"
            f"Provide risk warnings and recommendations."
        )

        msg = Msg(name="system", content=content, role="user")
        result = await self.risk_manager.reply(msg)
        return self._extract_result_from_msg(result)

    async def _run_pm_with_sync(
        self,
        tickers: List[str],
        date: str,
        prices: Optional[Dict[str, float]],
        analyst_results: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run PM decision-making with real-time sync"""
        portfolio = self.pm.get_portfolio_state()

        context = {
            "analyst_signals": {
                r["agent"]: r.get("content", "") for r in analyst_results
            },
            "risk_warnings": risk_assessment.get("content", ""),
            "current_prices": prices,
            "tickers": tickers,
            "portfolio_cash": portfolio.get("cash", 0),
            "portfolio_positions": portfolio.get("positions", {}),
        }

        # Add conference summary if available
        if self.conference_summary:
            context["conference_summary"] = self.conference_summary

        content_parts = [
            f"Based on the analyst signals, risk assessment, and conference discussion, "
            f"make investment decisions for date {date}.\n",
            f"Context:\n{json.dumps(context, indent=2)}\n",
        ]

        if self.conference_summary:
            content_parts.append(
                f"\n=== Conference Summary ===\n{self.conference_summary}\n",
            )

        content_parts.append(
            "\nUse the make_decision tool for each ticker to record your decisions. "
            "After recording all decisions, provide a summary of your investment rationale.",
        )

        content = "".join(content_parts)

        msg = Msg(name="system", content=content, role="user")
        result = await self.pm.reply(msg)
        extracted = self._extract_result_from_msg(result)

        # Sync retrieved memory first
        await self._sync_memory_if_retrieved(self.pm)

        # Broadcast PM decision via StateSync
        if self.state_sync:
            text_content = self._extract_text_content(result.content)
            await self.state_sync.on_agent_complete(
                agent_id="portfolio_manager",
                content=text_content,
            )

        return extracted

    async def _run_pm(
        self,
        tickers: List[str],
        date: str,
        prices: Dict[str, float],
        analyst_results: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run PM decision-making (without sync, for backward compatibility)"""
        portfolio = self.pm.get_portfolio_state()

        context = {
            "analyst_signals": {
                r["agent"]: r.get("content", "") for r in analyst_results
            },
            "risk_warnings": risk_assessment.get("content", ""),
            "current_prices": prices,
            "tickers": tickers,
            "portfolio_cash": portfolio.get("cash", 0),
            "portfolio_positions": portfolio.get("positions", {}),
        }

        content = (
            f"Based on the analyst signals and risk assessment, make investment decisions "
            f"for date {date}.\n"
            f"Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Use the make_decision tool for each ticker to record your decisions. "
            f"After recording all decisions, provide a summary of your investment rationale."
        )

        msg = Msg(name="system", content=content, role="user")
        result = await self.pm.reply(msg)
        return self._extract_result_from_msg(result)

    def _execute_decisions(
        self,
        decisions: Dict[str, Dict],
        prices: Optional[Dict[str, float]],
        date: str,
    ) -> Dict[str, Any]:
        """Execute PM decisions with provided prices"""
        if not decisions:
            return {
                "executed_trades": [],
                "portfolio": self.pm.get_portfolio_state(),
            }

        executor = PortfolioTradeExecutor(
            initial_portfolio=self.pm.get_portfolio_state(),
        )

        executed_trades = []

        for ticker, decision in decisions.items():
            action = decision.get("action", "hold")
            quantity = decision.get("quantity", 0)

            if action == "hold" or quantity == 0:
                continue

            price = prices.get(ticker)
            if not price or price <= 0:
                logger.warning(f"No price for {ticker}, skipping trade")
                continue

            result = executor.execute_trade(
                ticker=ticker,
                action=action,
                quantity=quantity,
                price=price,
                current_date=date,
            )

            if result.get("status") == "success":
                executed_trades.append(
                    {
                        "ticker": ticker,
                        "action": action,
                        "quantity": quantity,
                        "price": price,
                    },
                )

        updated_portfolio = executor.portfolio.copy()
        self.pm.update_portfolio(updated_portfolio)

        return {
            "executed_trades": executed_trades,
            "portfolio": updated_portfolio,
        }

    def _extract_result_from_msg(self, msg: Msg) -> Dict[str, Any]:
        """Extract result dictionary from Msg object"""
        result = {
            "agent": msg.name,
            "content": msg.content,
        }

        if hasattr(msg, "metadata") and msg.metadata:
            result.update(msg.metadata)

        if isinstance(msg.content, str):
            try:
                result["content_parsed"] = json.loads(msg.content)
            except json.JSONDecodeError:
                pass

        return result

    def _extract_text_content(self, content: Any) -> str:
        """
        Extract plain text from AgentScope Msg content

        AgentScope content can be:
        - str: plain text
        - list: list of TextBlocks like [{'type': 'text', 'text': '...'}]
        - dict: single TextBlock
        """
        if content is None:
            return ""

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict):
                    # TextBlock format: {'type': 'text', 'text': '...'}
                    if item.get("type") == "text" and "text" in item:
                        texts.append(item["text"])
                    elif "content" in item:
                        texts.append(str(item["content"]))
                    else:
                        texts.append(str(item))
                elif isinstance(item, str):
                    texts.append(item)
                else:
                    texts.append(str(item))
            return "\n".join(texts)

        if isinstance(content, dict):
            if content.get("type") == "text" and "text" in content:
                return content["text"]
            return str(content)

        return str(content)

    def _format_pm_decisions(self, decisions: Dict[str, Dict]) -> str:
        """Format PM decisions as a human-readable string"""
        if not decisions:
            return "Portfolio analysis completed. No trades recommended."

        decision_texts = []
        for ticker, decision in decisions.items():
            action = decision.get("action", "hold")
            quantity = decision.get("quantity", 0)
            reasoning = decision.get("reasoning", "")

            if action != "hold" and quantity > 0:
                decision_texts.append(
                    f"{action.upper()} {quantity} {ticker}: {reasoning}",
                )

        if decision_texts:
            return "Decisions: " + "; ".join(decision_texts)
        return "Portfolio analysis completed. No trades recommended."
