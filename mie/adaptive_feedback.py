"""
Adaptive Feedback Loop - NIVEL 6
Auto-adjust confidence thresholds + disable bad hypothesis types
Real-time learning from decision outcomes
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class AdaptiveFeedbackEngine:
    """
    Learns from validation metrics and adapts MIE behavior in real-time.

    Goals:
    1. Increase alerts for high-coherence hypothesis types
    2. Decrease/disable alerts for low-coherence hypothesis types
    3. Auto-adjust confidence thresholds based on accuracy
    4. Track win rate per hypothesis type
    """

    def __init__(self, decision_registry=None, logger=None):
        self.decision_registry = decision_registry
        self.logger = logger or logging.getLogger("AdaptiveFeedback")

        # Track performance per hypothesis type
        self.type_stats = defaultdict(lambda: {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "confidence_sum": 0.0,
            "avg_confidence": 0.0,
            "coherence": 0.0,
            "alert_enabled": True
        })

        # Track performance per asset
        self.asset_stats = defaultdict(lambda: {
            "total": 0,
            "wins": 0,
            "win_rate": 0.0
        })

        # Adaptive thresholds
        self.confidence_threshold = 0.65  # Default: alert if score >= 0.65
        self.min_coherence_threshold = 0.05  # Disable if coherence < 0.05
        self.min_win_rate_threshold = 0.50  # Disable if win_rate < 0.50

    def analyze_completed_decisions(self) -> Dict:
        """
        Analyze all completed decisions and calculate per-type statistics.
        Returns: {type_name: stats, asset_name: stats, recommendations}
        """
        if not self.decision_registry or not self.decision_registry.completed_decisions:
            return {
                "status": "no_data",
                "total_decisions": 0
            }

        # Reset stats
        self.type_stats = defaultdict(lambda: {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "confidence_sum": 0.0,
            "avg_confidence": 0.0,
            "coherence": 0.0,
            "alert_enabled": True
        })
        self.asset_stats = defaultdict(lambda: {
            "total": 0,
            "wins": 0,
            "win_rate": 0.0
        })

        # Analyze each completed decision
        for decision in self.decision_registry.completed_decisions:
            hyp_type = decision.get("hypothesis_type", "unknown")
            asset = decision.get("asset", "unknown")
            backtest_score = decision.get("backtest_score", 0.5)

            # Check if prediction was correct (at +24h)
            outcome_24h = decision.get("outcome_24h", {})
            is_win = outcome_24h.get("win", False)

            # Update type stats
            self.type_stats[hyp_type]["total"] += 1
            self.type_stats[hyp_type]["confidence_sum"] += backtest_score
            if is_win:
                self.type_stats[hyp_type]["wins"] += 1
            else:
                self.type_stats[hyp_type]["losses"] += 1

            # Update asset stats
            self.asset_stats[asset]["total"] += 1
            if is_win:
                self.asset_stats[asset]["wins"] += 1

        # Calculate derived stats
        for hyp_type in self.type_stats:
            stats = self.type_stats[hyp_type]
            if stats["total"] > 0:
                stats["win_rate"] = stats["wins"] / stats["total"]
                stats["avg_confidence"] = stats["confidence_sum"] / stats["total"]

            # Calculate coherence for this type
            # High-confidence wins vs low-confidence wins
            high_conf_decisions = [d for d in self.decision_registry.completed_decisions
                                  if d.get("hypothesis_type") == hyp_type
                                  and d.get("backtest_score", 0) >= 0.65]
            low_conf_decisions = [d for d in self.decision_registry.completed_decisions
                                 if d.get("hypothesis_type") == hyp_type
                                 and d.get("backtest_score", 0) < 0.65]

            high_conf_wins = sum(1 for d in high_conf_decisions if d.get("outcome_24h", {}).get("win"))
            low_conf_wins = sum(1 for d in low_conf_decisions if d.get("outcome_24h", {}).get("win"))

            high_conf_rate = high_conf_wins / len(high_conf_decisions) if high_conf_decisions else 0
            low_conf_rate = low_conf_wins / len(low_conf_decisions) if low_conf_decisions else 0

            stats["coherence"] = high_conf_rate - low_conf_rate

        for asset in self.asset_stats:
            stats = self.asset_stats[asset]
            if stats["total"] > 0:
                stats["win_rate"] = stats["wins"] / stats["total"]

        return {
            "status": "analyzed",
            "total_decisions": len(self.decision_registry.completed_decisions),
            "type_stats": dict(self.type_stats),
            "asset_stats": dict(self.asset_stats)
        }

    def generate_recommendations(self) -> Dict:
        """
        Based on performance, generate recommendations for alert thresholds.
        Returns: {alerts_to_enable, alerts_to_disable, threshold_adjustments}
        """
        recommendations = {
            "enable_alerts": [],
            "disable_alerts": [],
            "adjust_threshold": None,
            "reasons": []
        }

        # Analyze each hypothesis type
        for hyp_type, stats in self.type_stats.items():
            if stats["total"] < 3:  # Need at least 3 decisions to make recommendations
                continue

            win_rate = stats["win_rate"]
            coherence = stats["coherence"]

            # DISABLE: Low win rate AND low coherence
            if win_rate < self.min_win_rate_threshold and coherence < self.min_coherence_threshold:
                recommendations["disable_alerts"].append({
                    "type": hyp_type,
                    "reason": f"Low win rate ({win_rate:.1%}) + low coherence ({coherence:+.2f})",
                    "current_state": "disabled"
                })
                stats["alert_enabled"] = False
                recommendations["reasons"].append(
                    f"🔴 {hyp_type}: DISABLE (WR={win_rate:.1%}, coherence={coherence:+.2f})"
                )

            # ENABLE: High win rate AND high coherence
            elif win_rate > 0.55 and coherence > 0.10:
                if not stats["alert_enabled"]:
                    recommendations["enable_alerts"].append({
                        "type": hyp_type,
                        "reason": f"Strong win rate ({win_rate:.1%}) + good coherence ({coherence:+.2f})",
                        "current_state": "enabled"
                    })
                stats["alert_enabled"] = True
                recommendations["reasons"].append(
                    f"🟢 {hyp_type}: ENABLE (WR={win_rate:.1%}, coherence={coherence:+.2f})"
                )

            else:
                # Keep current state but note it
                recommendations["reasons"].append(
                    f"🟡 {hyp_type}: MONITOR (WR={win_rate:.1%}, coherence={coherence:+.2f})"
                )

        # Adjust global confidence threshold based on overall accuracy
        metrics = self.decision_registry.get_validation_metrics() if self.decision_registry else {}
        accuracy_24h = metrics.get("accuracy_24h", 0.5)

        if accuracy_24h > 0.60:
            # High accuracy: be more aggressive, lower threshold
            old_threshold = self.confidence_threshold
            self.confidence_threshold = 0.55
            recommendations["adjust_threshold"] = {
                "old": old_threshold,
                "new": self.confidence_threshold,
                "reason": f"High accuracy ({accuracy_24h:.1%}): lower threshold to catch more opportunities"
            }
            recommendations["reasons"].append(
                f"📊 Confidence threshold: {old_threshold} → {self.confidence_threshold} (accuracy={accuracy_24h:.1%})"
            )

        elif accuracy_24h < 0.50:
            # Low accuracy: be more conservative, raise threshold
            old_threshold = self.confidence_threshold
            self.confidence_threshold = 0.75
            recommendations["adjust_threshold"] = {
                "old": old_threshold,
                "new": self.confidence_threshold,
                "reason": f"Low accuracy ({accuracy_24h:.1%}): raise threshold to filter weaker signals"
            }
            recommendations["reasons"].append(
                f"📊 Confidence threshold: {old_threshold} → {self.confidence_threshold} (accuracy={accuracy_24h:.1%})"
            )

        return recommendations

    def apply_recommendations(self, recommendations: Dict) -> str:
        """Apply recommendations and return summary."""
        report = "🔄 ADAPTIVE FEEDBACK REPORT\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        if recommendations["disable_alerts"]:
            report += "\n🔴 DISABLING ALERTS:\n"
            for item in recommendations["disable_alerts"]:
                report += f"  • {item['type']}\n"
                report += f"    Reason: {item['reason']}\n"
                self.logger.info(f"🔴 Disabled alerts for {item['type']}")

        if recommendations["enable_alerts"]:
            report += "\n🟢 ENABLING ALERTS:\n"
            for item in recommendations["enable_alerts"]:
                report += f"  • {item['type']}\n"
                report += f"    Reason: {item['reason']}\n"
                self.logger.info(f"🟢 Enabled alerts for {item['type']}")

        if recommendations["adjust_threshold"]:
            adjust = recommendations["adjust_threshold"]
            report += f"\n📊 THRESHOLD ADJUSTMENT:\n"
            report += f"  {adjust['old']:.2f} → {adjust['new']:.2f}\n"
            report += f"  Reason: {adjust['reason']}\n"
            self.logger.info(
                f"📊 Adjusted confidence threshold: {adjust['old']:.2f} → {adjust['new']:.2f}"
            )

        report += "\n📈 TYPE PERFORMANCE:\n"
        for reason in recommendations["reasons"]:
            report += f"  {reason}\n"

        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        return report

    def should_alert(self, hypothesis: Dict, backtest_score: float) -> bool:
        """
        Determine if we should send an alert for this hypothesis.
        Uses adaptive thresholds based on learning.
        """
        hyp_type = hypothesis.get("type", "unknown")

        # Check if this type is disabled
        if not self.type_stats[hyp_type].get("alert_enabled", True):
            self.logger.debug(f"⏸️  Alert suppressed for {hyp_type} (disabled)")
            return False

        # Check if backtest score meets threshold
        if backtest_score < self.confidence_threshold:
            self.logger.debug(
                f"⏸️  Alert suppressed for {hyp_type} (score {backtest_score:.2f} < threshold {self.confidence_threshold:.2f})"
            )
            return False

        self.logger.info(f"✅ Alert approved for {hyp_type} (score={backtest_score:.2f})")
        return True

    def format_status_report(self) -> str:
        """Generate human-readable status report."""
        report = "🎯 ADAPTIVE FEEDBACK STATUS\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        report += f"\n⚙️  Current Thresholds:\n"
        report += f"  Confidence: {self.confidence_threshold:.2f}\n"
        report += f"  Min Coherence: {self.min_coherence_threshold:+.2f}\n"
        report += f"  Min Win Rate: {self.min_win_rate_threshold:.1%}\n"

        report += f"\n📊 Hypothesis Type Performance:\n"
        for hyp_type, stats in self.type_stats.items():
            if stats["total"] == 0:
                continue

            status = "✅ ENABLED" if stats["alert_enabled"] else "🔴 DISABLED"
            report += f"  {hyp_type}:\n"
            report += f"    {stats['total']} decisions, {stats['win_rate']:.1%} win rate\n"
            report += f"    Coherence: {stats['coherence']:+.2f}\n"
            report += f"    Status: {status}\n"

        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        return report
