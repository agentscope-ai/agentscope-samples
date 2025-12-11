# -*- coding: utf-8 -*-
"""
Message Adapter - Converts AgentScope Msg to frontend JSON format
Ensures compatibility with existing frontend without modifications
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agentscope.message import Msg

logger = logging.getLogger(__name__)


class FrontendAdapter:
    """
    Adapter to convert AgentScope messages to frontend-compatible format

    Frontend expects specific message types:
    - agent: Agent thinking/analysis messages
    - team_summary: Portfolio summary with equity curves
    - team_holdings: Current portfolio holdings
    - team_stats: Portfolio statistics
    - team_trades: Trade history
    - team_leaderboard: Agent performance rankings
    - price_update: Real-time price updates
    - system: System notifications
    """

    @staticmethod
    def parse(msg: Msg) -> Optional[Dict[str, Any]]:
        """
        Parse AgentScope Msg to frontend format

        Args:
            msg: AgentScope Msg object

        Returns:
            Dictionary in frontend format, or None if message should be skipped
        """
        if msg is None:
            return None

        # Determine message type based on metadata or content
        msg_type = FrontendAdapter._determine_type(msg)

        if msg_type == "agent":
            return FrontendAdapter._format_agent_msg(msg)
        elif msg_type == "portfolio_update":
            return FrontendAdapter._format_portfolio_msg(msg)
        elif msg_type == "system":
            return FrontendAdapter._format_system_msg(msg)
        else:
            # Default: treat as agent message
            return FrontendAdapter._format_agent_msg(msg)

    @staticmethod
    def _determine_type(msg: Msg) -> str:
        """Determine frontend message type from Msg"""
        # Check metadata for explicit type
        if hasattr(msg, "metadata") and msg.metadata:
            if "type" in msg.metadata:
                return msg.metadata["type"]

            # Check if message contains portfolio update
            if "portfolio" in msg.metadata:
                return "portfolio_update"

        # Check message name/role
        if msg.name == "system":
            return "system"

        # Default to agent message
        return "agent"

    @staticmethod
    def _format_agent_msg(msg: object) -> Dict[str, Any]:
        """
        Format agent message for frontend

        Args:
            msg: Either AgentScope Msg or dict from pipeline results

        Frontend expects:
        {
            "type": "agent",
            "role_key": "analyst_id",
            "content": "message text",
            "timestamp": "ISO timestamp"
        }
        """
        # Handle dict from pipeline results
        if isinstance(msg, dict):
            name = msg.get("agent", "unknown")
            content = msg.get("content", "")
        else:
            # Handle Msg object
            name = msg.name
            content = msg.content

        return {
            "type": "agent",
            "role_key": name,
            "content": content
            if isinstance(content, str)
            else json.dumps(content),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def _format_portfolio_msg(msg: Msg) -> Dict[str, Any]:
        """
        Format portfolio update message

        This typically generates multiple frontend messages:
        - team_summary
        - team_holdings
        - team_stats
        - team_trades (if trades were executed)
        """
        metadata = msg.metadata or {}
        portfolio = metadata.get("portfolio", {})

        messages: List[Dict[str, Any]] = []

        # Generate holdings message
        holdings = FrontendAdapter.build_holdings(portfolio)
        if holdings:
            messages.append(
                {
                    "type": "team_holdings",
                    "data": holdings,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Generate stats message
        stats = FrontendAdapter.build_stats(portfolio)
        if stats:
            messages.append(
                {
                    "type": "team_stats",
                    "data": stats,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Generate trades message if execution logs exist
        execution_logs = metadata.get("execution_logs", [])
        if execution_logs:
            trades = FrontendAdapter.build_trades(execution_logs)
            messages.append(
                {
                    "type": "team_trades",
                    "mode": "incremental",
                    "data": trades,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Return composite message
        return {
            "type": "composite",
            "messages": messages,
        }

    @staticmethod
    def _format_system_msg(msg: Msg) -> Dict[str, Any]:
        """Format system message"""
        return {
            "type": "system",
            "content": msg.content
            if isinstance(msg.content, str)
            else json.dumps(msg.content),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def build_holdings(
        portfolio: Dict[str, Any],
        prices: Dict[str, float] = None,
    ) -> List[Dict[str, Any]]:
        """Build holdings array from portfolio state"""
        holdings = []
        prices = prices or {}

        positions = portfolio.get("positions", {})
        cash = portfolio.get("cash", 0.0)

        # Calculate total value using current prices
        total_value = cash
        for ticker, position in positions.items():
            long_shares = position.get("long", 0)
            short_shares = position.get("short", 0)
            price = prices.get(ticker) or position.get("avg_price", 0)
            total_value += (long_shares - short_shares) * price

        # Build holdings for each position
        for ticker, position in positions.items():
            long_shares = position.get("long", 0)
            short_shares = position.get("short", 0)
            avg_price = position.get("avg_price", 0)
            current_price = prices.get(ticker) or avg_price

            net_shares = long_shares - short_shares
            if net_shares == 0:
                continue

            market_value = net_shares * current_price
            weight = market_value / total_value if total_value > 0 else 0

            holdings.append(
                {
                    "ticker": ticker,
                    "quantity": net_shares,
                    "avg": avg_price,
                    "currentPrice": current_price,
                    "marketValue": market_value,
                    "weight": weight,
                },
            )

        # Add cash as a holding
        if cash > 0:
            holdings.append(
                {
                    "ticker": "CASH",
                    "quantity": 1,
                    "avg": cash,
                    "currentPrice": cash,
                    "marketValue": cash,
                    "weight": cash / total_value if total_value > 0 else 0,
                },
            )

        return holdings

    @staticmethod
    def build_stats(
        portfolio: Dict[str, Any],
        prices: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """Build stats dictionary from portfolio"""
        prices = prices or {}
        positions = portfolio.get("positions", {})
        cash = portfolio.get("cash", 0.0)
        margin_used = portfolio.get("margin_used", 0.0)

        # Calculate total value using current prices
        total_value = cash
        for ticker, position in positions.items():
            long_shares = position.get("long", 0)
            short_shares = position.get("short", 0)
            price = prices.get(ticker) or position.get("avg_price", 0)
            total_value += (long_shares - short_shares) * price

        # Calculate ticker weights
        ticker_weights = {}
        for ticker, position in positions.items():
            long_shares = position.get("long", 0)
            short_shares = position.get("short", 0)
            price = prices.get(ticker) or position.get("avg_price", 0)

            market_value = (long_shares - short_shares) * price
            if market_value != 0:
                ticker_weights[ticker] = (
                    market_value / total_value if total_value > 0 else 0
                )

        # Calculate total return
        initial_cash = portfolio.get("initial_cash", 100000.0)
        total_return = (
            ((total_value - initial_cash) / initial_cash * 100)
            if initial_cash > 0
            else 0.0
        )

        return {
            "totalAssetValue": round(total_value, 2),
            "totalReturn": round(total_return, 2),
            "cashPosition": round(cash, 2),
            "tickerWeights": ticker_weights,
            "marginUsed": round(margin_used, 2),
        }

    @staticmethod
    def build_trades(execution_logs: List[str]) -> List[Dict[str, Any]]:
        """
        Build trades array from execution logs

        Frontend expects:
        [{
            "ts": 1234567890,
            "ticker": "AAPL",
            "side": "LONG",
            "qty": 100,
            "price": 150.0,
            "reason": "Buy signal"
        }, ...]
        """
        trades = []
        timestamp = int(datetime.now().timestamp() * 1000)

        for log in execution_logs:
            # Parse execution log (simplified - should use structured data)
            if "Executed" in log:
                # Extract trade details from log string
                # in real implementation, pass structured data
                trades.append(
                    {
                        "ts": timestamp,
                        "ticker": "UNKNOWN",  # Should parse from log
                        "side": "LONG",  # Should parse from log
                        "qty": 0,  # Should parse from log
                        "price": 0.0,  # Should parse from log
                        "reason": log,
                    },
                )

        return trades
