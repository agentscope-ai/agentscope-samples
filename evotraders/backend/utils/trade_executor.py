# -*- coding: utf-8 -*-
"""
Trading Execution Engine - Supports Two Modes
1. Signal mode: Only records directional signal decisions
2. Portfolio mode: Executes specific trades and tracks positions
"""
# flake8: noqa: E501
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional


class DirectionSignalRecorder:
    """Direction signal recorder, records daily investment direction decisions"""

    def __init__(self):
        """Initialize direction signal recorder"""
        self.signal_log = []  # Record all directional signal history

    def record_direction_signals(
        self,
        decisions: Dict[str, Dict[str, Any]],
        current_date: str = None,
    ) -> Dict[str, Any]:
        """
        Record Portfolio Manager's directional signal decisions

        Args:
            decisions: PM's direction decisions {ticker: {action, confidence, reasoning}}
            current_date: Current date (used for backtest compatibility)

        Returns:
            Signal recording report
        """
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        # Use provided date for timestamp (backtest compatible)
        timestamp = f"{current_date}T09:30:00"

        signal_report: Dict[str, Any] = {
            "recorded_signals": {},
            "date": current_date,
            "timestamp": timestamp,
            "total_signals": len(decisions),
        }

        print(
            f"\n📊 Recording directional signal decisions for {current_date}...",
        )

        # Record directional signal for each ticker
        for ticker, decision in decisions.items():
            action = decision.get("action", "hold")
            confidence = decision.get("confidence", 0)
            reasoning = decision.get("reasoning", "")

            # Record signal
            signal_record = {
                "ticker": ticker,
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning,
                "date": current_date,
                "timestamp": timestamp,
            }

            self.signal_log.append(signal_record)
            signal_report["recorded_signals"][ticker] = {
                "action": action,
                "confidence": confidence,
            }

            # Display signal
            action_emoji = {"long": "📈", "short": "📉", "hold": "➖"}
            emoji = action_emoji.get(action, "❓")
            print(
                f"   {emoji} {ticker}: {action.upper()} (Confidence: {confidence}%) - {reasoning}",
            )

        print(f"\n✅ Recorded directional signals for {len(decisions)} stocks")

        return signal_report

    def get_signal_summary(self) -> Dict[str, Any]:
        """Get signal recording summary"""
        return {
            "total_signals": len(self.signal_log),
            "signal_log": self.signal_log,
        }


def parse_pm_decisions(pm_output: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Parse Portfolio Manager output format

    Args:
        pm_output: PM's raw output

    Returns:
        Standardized decision format
    """
    if isinstance(pm_output, dict) and "decisions" in pm_output:
        return pm_output["decisions"]
    elif isinstance(pm_output, dict):
        # If directly a decision dictionary
        return pm_output
    else:
        print(f"Warning: Unable to parse PM output format: {type(pm_output)}")
        return {}


class PortfolioTradeExecutor:
    """Portfolio mode trade executor, executes specific trades and tracks positions"""

    portfolio: Dict[str, Any]
    trade_history: List[Dict[str, Any]]
    portfolio_history: List[Dict[str, Any]]

    def __init__(self, initial_portfolio: Optional[Dict[str, Any]] = None):
        """
        Initialize Portfolio trade executor

        Args:
            initial_portfolio: Initial portfolio state
        """

        if initial_portfolio is None:
            self.portfolio = {
                "cash": 100000.0,
                "positions": {},
                # Default 0.0 (short selling disabled)
                "margin_requirement": 0.0,
                "margin_used": 0.0,
            }
        else:
            self.portfolio = deepcopy(initial_portfolio)

        self.trade_history = []  # Trade history
        self.portfolio_history = []  # Portfolio history

    def execute_trade(
        self,
        ticker: str,
        action: str,
        quantity: int,
        price: float,
        current_date: str = None,
    ) -> Dict[str, Any]:
        """
        Execute a single trade

        Args:
            ticker: Stock ticker
            action: Trade action (long/short/hold)
            quantity: Number of shares
            price: Current price
            current_date: Trade date

        Returns:
            Trade result dictionary
        """
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        if action == "hold" or quantity == 0:
            return {"status": "success", "message": "No trade needed"}

        if price <= 0:
            return {"status": "failed", "reason": "Invalid price"}

        result = self._execute_single_trade(
            ticker=ticker,
            action=action,
            target_quantity=quantity,
            price=price,
            date=current_date,
        )

        return result

    def execute_trades(
        self,
        decisions: Dict[str, Dict[str, Any]],
        current_prices: Dict[str, float],
        current_date: str = None,
    ) -> Dict[str, Any]:
        """
        Execute trading decisions and update positions

        Args:
            decisions: {ticker: {action, quantity, confidence, reasoning}}
            current_prices: {ticker: current_price}
            current_date: Current date (used for backtest compatibility)

        Returns:
            Trade execution report
        """
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        # Use provided date for timestamp (backtest compatible)
        timestamp = f"{current_date}T09:30:00"

        execution_report: Dict[str, Any] = {
            "date": current_date,
            "timestamp": timestamp,
            "executed_trades": [],
            "failed_trades": [],
            "portfolio_before": deepcopy(self.portfolio),
            "portfolio_after": None,
        }

        print(f"\n💼 Executing Portfolio trades for {current_date}...")

        # Execute trades for each ticker
        for ticker, decision in decisions.items():
            action = decision.get("action", "hold")
            quantity = decision.get("quantity", 0)

            if action == "hold" or quantity == 0:
                continue

            price = current_prices.get(ticker, 0)
            if price <= 0:
                execution_report["failed_trades"].append(
                    {
                        "ticker": ticker,
                        "action": action,
                        "quantity": quantity,
                        "reason": "No valid price data",
                    },
                )
                print(
                    f"   ❌ {ticker}: Unable to execute {action} - No valid price",
                )
                continue

            # Execute trade
            trade_result = self._execute_single_trade(
                ticker,
                action,
                quantity,
                price,
                current_date,
            )
            if trade_result["status"] == "success":
                execution_report["executed_trades"].append(trade_result)

                trades_info = ", ".join(trade_result.get("trades", []))
                print(
                    f"   ✔ {ticker}: {action} Target {quantity} shares "
                    f"({trades_info}) @ ${price:.2f}",
                )
            else:
                execution_report["failed_trades"].append(trade_result)
                print(
                    f"   ✗ {ticker}: Unable to execute {action} - {trade_result['reason']}",
                )

        # Record final portfolio state
        execution_report["portfolio_after"] = deepcopy(self.portfolio)
        self.portfolio_history.append(
            {
                "date": current_date,
                "portfolio": deepcopy(self.portfolio),
            },
        )

        # Calculate portfolio value
        portfolio_value = self._calculate_portfolio_value(current_prices)
        execution_report["portfolio_value"] = portfolio_value

        print("\n✔ Trade execution completed:")
        print(f"   Success: {len(execution_report['executed_trades'])} trades")
        print(f"   Failed: {len(execution_report['failed_trades'])} trades")
        print(f"   Portfolio value: ${portfolio_value:,.2f}")
        print(f"   Cash balance: ${self.portfolio['cash']:,.2f}")

        return execution_report

    def _execute_single_trade(
        self,
        ticker: str,
        action: str,
        target_quantity: int,
        price: float,
        date: str,
    ) -> Dict[str, Any]:
        """
        Execute single trade - Incremental mode

        Args:
            ticker: Stock ticker
            action: long(add position)/short(reduce position)/hold
            target_quantity: Incremental quantity (long=buy shares, short=sell shares)
            price: Current price
            date: Trade date
        """

        # Ensure position exists
        if ticker not in self.portfolio["positions"]:
            self.portfolio["positions"][ticker] = {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
            }

        position = self.portfolio["positions"][ticker]
        current_long = position["long"]
        current_short = position["short"]

        trades_executed = []  # Record actually executed trade steps

        if action == "long":
            result = self._execute_long_action(
                ticker,
                target_quantity,
                price,
                date,
                current_long,
                current_short,
                trades_executed,
            )
            if result["status"] == "failed":
                return result

        elif action == "short":
            result = self._execute_short_action(
                ticker,
                target_quantity,
                price,
                date,
                current_long,
                current_short,
                trades_executed,
            )
            if result["status"] == "failed":
                return result

        elif action == "hold":
            print(f"\n⏸️ {ticker} Position unchanged: {current_long} shares")

        # Record trade with backtest-compatible timestamp
        trade_record = {
            "status": "success",
            "ticker": ticker,
            "action": action,
            "target_quantity": target_quantity,
            "price": price,
            "trades": trades_executed,
            "date": date,
            "timestamp": f"{date}T09:30:00",
        }

        self.trade_history.append(trade_record)

        return trade_record

    def _execute_long_action(
        self,
        ticker: str,
        target_quantity: int,
        price: float,
        date: str,
        current_long: int,
        current_short: int,
        trades_executed: list,
    ) -> Dict[str, Any]:
        """Execute long action: Buy shares or cover shorts first"""
        print(
            f"\n📈 {ticker} Long operation: Current Long {current_long}, "
            f"Short {current_short} → Target quantity {target_quantity}",
        )

        if target_quantity <= 0:
            print("   ⏸️ Quantity is 0, no trade needed")
            return {"status": "success"}

        remaining = target_quantity

        # If has short position, cover first
        if current_short > 0:
            cover_qty = min(remaining, current_short)
            print(f"   1️⃣ Cover short: {cover_qty} shares")
            cover_result = self._cover_short_position(
                ticker,
                cover_qty,
                price,
                date,
            )
            if cover_result["status"] == "failed":
                return cover_result
            trades_executed.append(f"Cover {cover_qty} shares")
            remaining -= cover_qty

        # If still has remaining quantity, buy long
        if remaining > 0:
            print(f"   2️⃣ Buy long: {remaining} shares")
            buy_result = self._buy_long_position(
                ticker,
                remaining,
                price,
                date,
            )
            if buy_result["status"] == "failed":
                return buy_result
            trades_executed.append(f"Buy {remaining} shares")

        # Display final result
        final_long = self.portfolio["positions"][ticker]["long"]
        final_short = self.portfolio["positions"][ticker]["short"]
        print(
            f"   ✅ Final state: Long {final_long} shares, Short {final_short} shares",
        )

        return {"status": "success"}

    def _execute_short_action(
        self,
        ticker: str,
        target_quantity: int,
        price: float,
        date: str,
        current_long: int,
        current_short: int,
        trades_executed: list,
    ) -> Dict[str, Any]:
        """Execute short action: Sell long positions first, then short if needed"""
        print(
            f"\n📉 {ticker} Short operation (quantity={target_quantity} shares):",
        )
        print(
            f"   Current state: Long {current_long} shares, Short {current_short} shares",
        )

        if target_quantity <= 0:
            print("   ⏸️ Quantity is 0, no trade needed")
            return {"status": "success"}

        remaining_quantity = target_quantity

        # Step 1: If there are long positions, sell first
        if current_long > 0:
            sell_quantity = min(remaining_quantity, current_long)
            print(f"   1️⃣ Sell long: {sell_quantity} shares")
            sell_result = self._sell_long_position(
                ticker,
                sell_quantity,
                price,
                date,
            )
            if sell_result["status"] == "failed":
                return sell_result
            trades_executed.append(f"Sell {sell_quantity} shares")
            remaining_quantity -= sell_quantity

        # Step 2: If there's remaining quantity, establish or increase short position
        if remaining_quantity > 0:
            print(f"   2️⃣ Short: {remaining_quantity} shares")
            short_result = self._open_short_position(
                ticker,
                remaining_quantity,
                price,
                date,
            )
            if short_result["status"] == "failed":
                return short_result
            trades_executed.append(f"Short {remaining_quantity} shares")

        # Display final result
        final_long = self.portfolio["positions"][ticker]["long"]
        final_short = self.portfolio["positions"][ticker]["short"]
        print(
            f"   ✅ Final state: Long {final_long} shares, Short {final_short} shares",
        )

        return {"status": "success"}

    def _buy_long_position(
        self,
        ticker: str,
        quantity: int,
        price: float,
        _date: str,
    ) -> Dict[str, Any]:
        """Buy long position"""
        position = self.portfolio["positions"][ticker]
        trade_value = quantity * price

        if self.portfolio["cash"] < trade_value:
            return {
                "status": "failed",
                "ticker": ticker,
                "action": "buy",
                "quantity": quantity,
                "price": price,
                "reason": f"Insufficient cash (needed: ${trade_value:.2f}, available: "
                f"${self.portfolio['cash']:.2f})",
            }

        # Update position cost basis
        old_long = position["long"]
        old_cost_basis = position["long_cost_basis"]
        new_long = old_long + quantity

        # 🐛 Debug info
        print(f"   🔍 Buy {ticker}:")
        print(f"      Old position: {old_long} shares @ ${old_cost_basis:.2f}")
        print(f"      Buy: {quantity} shares @ ${price:.2f}")
        print(f"      New position: {new_long} shares")

        if new_long > 0:
            new_cost_basis = (
                (old_long * old_cost_basis) + (quantity * price)
            ) / new_long
            print(
                f"      New cost: ${new_cost_basis:.2f} = "
                f"(({old_long} × ${old_cost_basis:.2f}) + "
                f"({quantity} × ${price:.2f})) / {new_long}",
            )
            position["long_cost_basis"] = new_cost_basis
        position["long"] = new_long

        # Deduct cash
        self.portfolio["cash"] -= trade_value

        return {"status": "success"}

    def _sell_long_position(
        self,
        ticker: str,
        quantity: int,
        price: float,
        _date: str,
    ) -> Dict[str, Any]:
        """Sell long position"""
        position = self.portfolio["positions"][ticker]

        if position["long"] < quantity:
            return {
                "status": "failed",
                "ticker": ticker,
                "action": "sell",
                "quantity": quantity,
                "price": price,
                "reason": f"Insufficient long position (holding: {position['long']},"
                f" trying to sell: {quantity})",
            }

        # Reduce position
        position["long"] -= quantity
        if position["long"] == 0:
            position["long_cost_basis"] = 0.0

        # Increase cash
        trade_value = quantity * price
        self.portfolio["cash"] += trade_value

        return {"status": "success"}

    def _open_short_position(
        self,
        ticker: str,
        quantity: int,
        price: float,
        _date: str,
    ) -> Dict[str, Any]:
        """Open short position"""
        position = self.portfolio["positions"][ticker]
        trade_value = quantity * price
        margin_needed = trade_value * self.portfolio["margin_requirement"]

        if self.portfolio["cash"] < margin_needed:
            return {
                "status": "failed",
                "ticker": ticker,
                "action": "short",
                "quantity": quantity,
                "price": price,
                "reason": f"Insufficient margin (needed: ${margin_needed:.2f}, "
                f"available: ${self.portfolio['cash']:.2f})",
            }

        # Update position cost basis
        old_short = position["short"]
        old_cost_basis = position["short_cost_basis"]
        new_short = old_short + quantity
        if new_short > 0:
            position["short_cost_basis"] = (
                (old_short * old_cost_basis) + (quantity * price)
            ) / new_short
        position["short"] = new_short

        # Increase cash (short sale proceeds) and margin used
        self.portfolio["cash"] += trade_value - margin_needed
        self.portfolio["margin_used"] += margin_needed

        return {"status": "success"}

    def _cover_short_position(
        self,
        ticker: str,
        quantity: int,
        price: float,
        _date: str,
    ) -> Dict[str, Any]:
        """Cover short position"""
        position = self.portfolio["positions"][ticker]

        if position["short"] < quantity:
            return {
                "status": "failed",
                "ticker": ticker,
                "action": "cover",
                "quantity": quantity,
                "price": price,
                "reason": f"Insufficient short position (holding: {position['short']}, "
                f"trying to cover: {quantity})",
            }

        # Calculate released margin - 🔧 FIX: Use cost_basis instead of current price
        trade_value = quantity * price
        cost_basis = position["short_cost_basis"]
        margin_released = (
            quantity * cost_basis * self.portfolio["margin_requirement"]
        )

        # Reduce position
        position["short"] -= quantity
        if position["short"] == 0:
            position["short_cost_basis"] = 0.0

        # Deduct cash (buy to cover) and release margin
        self.portfolio["cash"] -= trade_value
        self.portfolio["cash"] += margin_released
        self.portfolio["margin_used"] -= margin_released

        return {"status": "success"}

    def _calculate_portfolio_value(
        self,
        current_prices: Dict[str, float],
    ) -> float:
        """Calculate total portfolio value (net liquidation value)"""
        # Add margin_used back because it's frozen cash, not lost money
        total_value = self.portfolio["cash"] + self.portfolio["margin_used"]

        for ticker, position in self.portfolio["positions"].items():
            if ticker in current_prices:
                price = current_prices[ticker]
                # Add long position value
                total_value += position["long"] * price
                # Subtract short position value (liability)
                total_value -= position["short"] * price

        return total_value

    def get_portfolio_summary(
        self,
        current_prices: Dict[str, float],
    ) -> Dict[str, Any]:
        """Get portfolio summary"""
        portfolio_value = self._calculate_portfolio_value(current_prices)

        positions_summary = []
        for ticker, position in self.portfolio["positions"].items():
            if position["long"] > 0 or position["short"] > 0:
                price = current_prices.get(ticker, 0)
                long_value = position["long"] * price
                short_value = position["short"] * price

                positions_summary.append(
                    {
                        "ticker": ticker,
                        "long_shares": position["long"],
                        "short_shares": position["short"],
                        "long_value": long_value,
                        "short_value": short_value,
                        "long_cost_basis": position["long_cost_basis"],
                        "short_cost_basis": position["short_cost_basis"],
                        "long_pnl": (
                            long_value
                            - (position["long"] * position["long_cost_basis"])
                            if position["long"] > 0
                            else 0
                        ),
                        "short_pnl": (
                            (position["short"] * position["short_cost_basis"])
                            - short_value
                            if position["short"] > 0
                            else 0
                        ),
                    },
                )

        return {
            "portfolio_value": portfolio_value,
            "cash": self.portfolio["cash"],
            "margin_used": self.portfolio["margin_used"],
            "positions": positions_summary,
            "total_trades": len(self.trade_history),
        }


def execute_trading_decisions(
    pm_decisions: Dict[str, Any],
    current_date: str = None,
) -> Dict[str, Any]:
    """
    Convenience function to record directional signal decisions (Signal mode)

    Args:
        pm_decisions: PM's direction decisions
        current_date: Current date (optional)

    Returns:
        Signal recording report
    """
    # Parse PM decisions
    decisions = parse_pm_decisions(pm_decisions)

    # Create direction signal recorder
    recorder = DirectionSignalRecorder()

    # Record directional signals
    signal_report = recorder.record_direction_signals(decisions, current_date)

    return signal_report


def execute_portfolio_trades(
    pm_decisions: Dict[str, Any],
    current_prices: Dict[str, float],
    portfolio: Dict[str, Any],
    current_date: str = None,
) -> Dict[str, Any]:
    """
    Execute Portfolio mode trading decisions

    Args:
        pm_decisions: PM's trading decisions
        current_prices: Current prices
        portfolio: Current portfolio state
        current_date: Current date (optional)

    Returns:
        Trade execution report and updated portfolio
    """
    # Parse PM decisions
    decisions = parse_pm_decisions(pm_decisions)

    # Create Portfolio trade executor
    executor = PortfolioTradeExecutor(initial_portfolio=portfolio)

    # Execute trades
    execution_report = executor.execute_trades(
        decisions,
        current_prices,
        current_date,
    )

    # Add portfolio summary
    execution_report["portfolio_summary"] = executor.get_portfolio_summary(
        current_prices,
    )

    # Return updated portfolio
    execution_report["updated_portfolio"] = executor.portfolio

    return execution_report
