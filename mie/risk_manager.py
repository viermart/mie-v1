"""
Advanced Risk Management - NIVEL 7
Sharpe ratio, max drawdown, risk-adjusted returns per hypothesis type
Position sizing based on accuracy and coherence
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict
import math


class RiskManager:
    """
    Calculates advanced risk metrics for each hypothesis type.

    Metrics:
    - Sharpe Ratio: Risk-adjusted returns
    - Max Drawdown: Largest peak-to-trough decline
    - Risk-Adjusted Return: Return per unit of risk
    - Sortino Ratio: Return vs downside volatility
    - Recommended Position Size: Based on accuracy + volatility
    """

    def __init__(self, decision_registry=None, logger=None):
        self.decision_registry = decision_registry
        self.logger = logger or logging.getLogger("RiskManager")

        # Risk parameters
        self.risk_free_rate = 0.0  # Crypto: assume 0% risk-free rate
        self.min_sample_size = 5  # Need at least 5 trades to calculate metrics
        self.max_position_size = 0.10  # Max 10% of portfolio per trade

        # Per-type risk metrics
        self.type_risk_metrics = defaultdict(lambda: {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "avg_return": 0.0,
            "downside_volatility": 0.0,
            "sortino_ratio": 0.0,
            "recommended_position_size": 0.0,
            "risk_level": "UNKNOWN"
        })

    def analyze_risk_metrics(self) -> Dict:
        """
        Analyze all completed decisions and calculate risk metrics per type.
        """
        if not self.decision_registry or not self.decision_registry.completed_decisions:
            return {"status": "no_data", "total_decisions": 0}

        # Group decisions by type
        decisions_by_type = defaultdict(list)
        for decision in self.decision_registry.completed_decisions:
            hyp_type = decision.get("hypothesis_type", "unknown")
            outcome_24h = decision.get("outcome_24h", {})
            pnl_pct = outcome_24h.get("change_pct", 0.0)
            decisions_by_type[hyp_type].append(pnl_pct)

        # Calculate metrics for each type
        for hyp_type, returns in decisions_by_type.items():
            if len(returns) < self.min_sample_size:
                self.logger.debug(f"Insufficient data for {hyp_type}: {len(returns)} < {self.min_sample_size}")
                continue

            metrics = self._calculate_metrics(returns)
            self.type_risk_metrics[hyp_type] = metrics
            self.logger.info(
                f"📊 Risk metrics for {hyp_type}: "
                f"Sharpe={metrics['sharpe_ratio']:.2f}, "
                f"MaxDD={metrics['max_drawdown']:.1%}, "
                f"Size={metrics['recommended_position_size']:.1%}"
            )

        return {
            "status": "analyzed",
            "total_decisions": len(self.decision_registry.completed_decisions),
            "type_metrics": dict(self.type_risk_metrics)
        }

    def _calculate_metrics(self, returns: List[float]) -> Dict:
        """Calculate all risk metrics from a series of returns (%)."""
        if len(returns) < 2:
            return self._empty_metrics()

        metrics = {}

        # Average return
        avg_return = sum(returns) / len(returns)
        metrics["avg_return"] = avg_return

        # Volatility (standard deviation)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) if variance > 0 else 0
        metrics["volatility"] = volatility

        # Sharpe Ratio: (return - risk_free_rate) / volatility
        sharpe = (avg_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        metrics["sharpe_ratio"] = sharpe

        # Max Drawdown: largest peak-to-trough decline
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for ret in returns:
            cumulative += ret
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / abs(peak) if peak != 0 else 0
            max_dd = max(max_dd, drawdown)
        metrics["max_drawdown"] = max_dd

        # Downside Volatility: std dev of negative returns only
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_variance = sum((r - 0) ** 2 for r in negative_returns) / len(negative_returns)
            downside_vol = math.sqrt(downside_variance)
        else:
            downside_vol = 0
        metrics["downside_volatility"] = downside_vol

        # Sortino Ratio: (return - risk_free_rate) / downside_volatility
        sortino = (avg_return - self.risk_free_rate) / downside_vol if downside_vol > 0 else 0
        metrics["sortino_ratio"] = sortino

        # Recommended Position Size
        # Base: win_rate determines position
        # Adjust down: for high volatility
        # Adjust down: for negative Sharpe ratio
        win_rate = sum(1 for r in returns if r > 0) / len(returns)

        position_size = 0.05  # Base 5%
        position_size *= (1 + win_rate)  # Scale by win rate (5%-10%)
        position_size *= max(0, 1 - max_dd)  # Reduce if drawdown is high
        if sharpe < 0:
            position_size *= 0.5  # Cut in half if negative Sharpe

        position_size = min(position_size, self.max_position_size)
        position_size = max(position_size, 0.01)  # Minimum 1%
        metrics["recommended_position_size"] = position_size

        # Risk Level Classification
        if sharpe > 1.5:
            risk_level = "🟢 LOW RISK"
        elif sharpe > 0:
            risk_level = "🟡 MODERATE RISK"
        elif sharpe > -1.0:
            risk_level = "🟠 HIGH RISK"
        else:
            risk_level = "🔴 CRITICAL RISK"
        metrics["risk_level"] = risk_level

        return metrics

    def _empty_metrics(self) -> Dict:
        """Return empty metrics dict."""
        return {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "avg_return": 0.0,
            "downside_volatility": 0.0,
            "sortino_ratio": 0.0,
            "recommended_position_size": 0.01,
            "risk_level": "UNKNOWN"
        }

    def format_risk_report(self) -> str:
        """Generate human-readable risk report."""
        report = "⚠️  RISK MANAGEMENT REPORT (NIVEL 7)\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        report += "\n⚙️  Risk Parameters:\n"
        report += f"  Risk-free rate: {self.risk_free_rate:.1%}\n"
        report += f"  Min sample size: {self.min_sample_size} trades\n"
        report += f"  Max position: {self.max_position_size:.1%}\n"

        if not self.type_risk_metrics or all(m["sharpe_ratio"] == 0 for m in self.type_risk_metrics.values()):
            report += "\n⏳ Waiting for sufficient data (min 5 trades per type)\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            return report

        report += "\n📊 RISK METRICS BY TYPE:\n"
        for hyp_type, metrics in self.type_risk_metrics.items():
            if metrics["sharpe_ratio"] == 0 and metrics["max_drawdown"] == 0:
                continue

            report += f"\n  {hyp_type}:\n"
            report += f"    Sharpe Ratio: {metrics['sharpe_ratio']:+.2f}\n"
            report += f"    Max Drawdown: {metrics['max_drawdown']:.1%}\n"
            report += f"    Volatility: {metrics['volatility']:.2f}%\n"
            report += f"    Avg Return: {metrics['avg_return']:+.2f}%\n"
            report += f"    Sortino Ratio: {metrics['sortino_ratio']:+.2f}\n"
            report += f"    Recommended Position: {metrics['recommended_position_size']:.1%}\n"
            report += f"    {metrics['risk_level']}\n"

        report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        return report

    def should_take_trade(self, hypothesis: Dict, backtest_score: float) -> Dict:
        """
        Determine if we should take a trade based on risk metrics.
        Returns: {should_trade: bool, position_size: float, reason: str}
        """
        hyp_type = hypothesis.get("type", "unknown")
        metrics = self.type_risk_metrics.get(hyp_type, self._empty_metrics())

        # Trade decision rules
        should_trade = True
        reason = "✅ Trade approved"

        # Rule 1: Positive Sharpe ratio
        if metrics["sharpe_ratio"] < 0:
            should_trade = False
            reason = f"❌ Negative Sharpe ratio ({metrics['sharpe_ratio']:.2f})"

        # Rule 2: Max drawdown < 30%
        elif metrics["max_drawdown"] > 0.30:
            should_trade = False
            reason = f"❌ Max drawdown too high ({metrics['max_drawdown']:.1%})"

        # Rule 3: Backtest score > 0.55
        elif backtest_score < 0.55:
            should_trade = False
            reason = f"❌ Backtest score too low ({backtest_score:.2f})"

        position_size = metrics["recommended_position_size"] if should_trade else 0.0

        return {
            "should_trade": should_trade,
            "position_size": position_size,
            "reason": reason,
            "metrics": metrics
        }
