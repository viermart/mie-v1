"""
Machine Learning Engine - NIVEL 8
Learns from decision outcomes to improve pattern detection.
Predicts hypothesis success before backtesting.
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json


class MLEngine:
    """
    Machine Learning engine that learns from real outcomes.

    Goals:
    1. Track which pattern characteristics → successful trades
    2. Build success probability model per pattern type
    3. Predict hypothesis win probability before backtest
    4. Continuously retrain as new outcomes arrive
    5. Identify best feature combinations
    """

    def __init__(self, decision_registry=None, logger=None):
        self.decision_registry = decision_registry
        self.logger = logger or logging.getLogger("MLEngine")

        # Feature importance tracking
        self.feature_importance = defaultdict(float)

        # Pattern success rates (pattern_key -> win_rate)
        self.pattern_success_rates = defaultdict(lambda: {"wins": 0, "total": 0, "rate": 0.0})

        # Hypothesis type success model
        self.type_success_model = defaultdict(lambda: {
            "total_decisions": 0,
            "total_wins": 0,
            "win_rate": 0.0,
            "feature_importance": {}
        })

        # Recent performance window (last N decisions)
        self.performance_window_size = 50
        self.recent_patterns = []

    def extract_features(self, hypothesis: Dict, decision: Dict) -> Dict:
        """
        Extract machine learning features from hypothesis + decision outcome.
        """
        outcome_24h = decision.get("outcome_24h", {})
        is_win = outcome_24h.get("win", False)

        # Get state snapshot
        state = decision.get("state_snapshot", {})

        features = {
            # Outcome
            "win": is_win,
            "change_pct": outcome_24h.get("change_pct", 0),

            # Hypothesis characteristics
            "type": hypothesis.get("type", "unknown"),
            "asset": hypothesis.get("asset", "unknown"),
            "direction": hypothesis.get("direction", "?"),
            "backtest_score": decision.get("backtest_score", 0.5),

            # Market state at decision time
            "momentum_1h": state.get("momentum_1h", "?"),
            "momentum_4h": state.get("momentum_4h", "?"),
            "momentum_24h": state.get("momentum_24h", "?"),
            "trend": state.get("trend", "?"),
            "volatility": state.get("volatility", "?"),

            # Pattern key (for grouping similar situations)
            "pattern_key": self._create_pattern_key(hypothesis, state)
        }

        return features

    def _create_pattern_key(self, hypothesis: Dict, state: Dict) -> str:
        """Create a hashable key representing this pattern combination."""
        hyp_type = hypothesis.get("type", "unknown")
        asset = hypothesis.get("asset", "unknown")
        direction = hypothesis.get("direction", "?")
        momentum_4h = state.get("momentum_4h", "?")
        trend = state.get("trend", "?")

        return f"{hyp_type}_{asset}_{direction}_{momentum_4h}_{trend}"

    def train_from_completed_decisions(self) -> Dict:
        """
        Train ML models from all completed decisions.
        """
        if not self.decision_registry or not self.decision_registry.completed_decisions:
            return {"status": "no_data", "decisions_processed": 0}

        self.logger.info("🤖 Starting ML training from completed decisions...")

        decisions_processed = 0
        pattern_count = defaultdict(int)

        for decision in self.decision_registry.completed_decisions:
            hyp_type = decision.get("hypothesis_type", "unknown")
            outcome_24h = decision.get("outcome_24h", {})
            is_win = outcome_24h.get("win", False)

            # Update type success model
            self.type_success_model[hyp_type]["total_decisions"] += 1
            if is_win:
                self.type_success_model[hyp_type]["total_wins"] += 1

            # Update pattern tracking
            pattern_key = self._create_pattern_key(
                {"type": hyp_type, "asset": decision.get("asset"), "direction": decision.get("hypothesis_direction")},
                decision.get("state_snapshot", {})
            )
            self.pattern_success_rates[pattern_key]["total"] += 1
            if is_win:
                self.pattern_success_rates[pattern_key]["wins"] += 1

            pattern_count[pattern_key] += 1
            decisions_processed += 1

        # Calculate win rates
        for hyp_type in self.type_success_model:
            model = self.type_success_model[hyp_type]
            if model["total_decisions"] > 0:
                model["win_rate"] = model["total_wins"] / model["total_decisions"]

        for pattern_key in self.pattern_success_rates:
            pattern = self.pattern_success_rates[pattern_key]
            if pattern["total"] > 0:
                pattern["rate"] = pattern["wins"] / pattern["total"]

        # Calculate feature importance
        self._calculate_feature_importance()

        self.logger.info(
            f"🤖 ML training complete: {decisions_processed} decisions, "
            f"{len(self.pattern_success_rates)} unique patterns"
        )

        return {
            "status": "trained",
            "decisions_processed": decisions_processed,
            "unique_patterns": len(self.pattern_success_rates),
            "type_models": {k: v["win_rate"] for k, v in self.type_success_model.items()}
        }

    def _calculate_feature_importance(self):
        """Calculate which features most strongly correlate with wins."""
        # Simple importance: if feature value in winning trades > losing trades
        feature_scores = defaultdict(lambda: {"winning": 0, "losing": 0})

        for pattern_key, pattern in self.pattern_success_rates.items():
            if pattern["total"] == 0:
                continue

            win_rate = pattern["rate"]
            # Weight by number of occurrences
            weight = min(pattern["total"] / 10, 1.0)  # Normalize to 0-1

            # Extract features from pattern key
            parts = pattern_key.split("_")
            if len(parts) >= 5:
                hyp_type, asset, direction, momentum, trend = parts[0], parts[1], parts[2], parts[3], parts[4]

                if win_rate > 0.5:
                    feature_scores[f"type_{hyp_type}"]["winning"] += weight
                    feature_scores[f"asset_{asset}"]["winning"] += weight
                    feature_scores[f"direction_{direction}"]["winning"] += weight
                    feature_scores[f"momentum_{momentum}"]["winning"] += weight
                    feature_scores[f"trend_{trend}"]["winning"] += weight
                else:
                    feature_scores[f"type_{hyp_type}"]["losing"] += weight
                    feature_scores[f"asset_{asset}"]["losing"] += weight
                    feature_scores[f"direction_{direction}"]["losing"] += weight
                    feature_scores[f"momentum_{momentum}"]["losing"] += weight
                    feature_scores[f"trend_{trend}"]["losing"] += weight

        # Calculate importance as (winning_score - losing_score)
        for feature, scores in feature_scores.items():
            self.feature_importance[feature] = scores["winning"] - scores["losing"]

    def predict_hypothesis_success(self, hypothesis: Dict, state: Dict) -> Dict:
        """
        Predict probability of success for a hypothesis before backtesting.
        Uses trained ML models.
        """
        hyp_type = hypothesis.get("type", "unknown")
        backtest_score = hypothesis.get("backtest_score", 0.5)

        # Get success rate for this type
        type_model = self.type_success_model.get(hyp_type, {})
        type_win_rate = type_model.get("win_rate", 0.5)

        # Get pattern-specific rate
        pattern_key = self._create_pattern_key(hypothesis, state)
        pattern = self.pattern_success_rates.get(pattern_key, {})
        pattern_win_rate = pattern.get("rate", 0.5) if pattern.get("total", 0) >= 3 else 0.5

        # Blend predictions: weight historical + backtest_score
        historical_weight = 0.4
        backtest_weight = 0.6

        predicted_success = (
            (type_win_rate * 0.2 + pattern_win_rate * 0.2) * historical_weight +
            backtest_score * backtest_weight
        )

        confidence = "LOW"
        if pattern.get("total", 0) >= 10:
            confidence = "HIGH"
        elif pattern.get("total", 0) >= 5:
            confidence = "MEDIUM"

        return {
            "predicted_success_rate": predicted_success,
            "type_historical_rate": type_win_rate,
            "pattern_historical_rate": pattern_win_rate,
            "pattern_sample_size": pattern.get("total", 0),
            "prediction_confidence": confidence,
            "recommendation": "STRONG BUY" if predicted_success > 0.60 else
                            "BUY" if predicted_success > 0.55 else
                            "HOLD" if predicted_success > 0.50 else
                            "AVOID"
        }

    def format_ml_report(self) -> str:
        """Generate human-readable ML model report."""
        report = "🤖 MACHINE LEARNING REPORT (NIVEL 8)\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        if not self.type_success_model or all(m["total_decisions"] == 0 for m in self.type_success_model.values()):
            report += "\n⏳ Waiting for training data (min 5 decisions per type)\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            return report

        report += "\n📊 HYPOTHESIS TYPE MODELS:\n"
        for hyp_type, model in self.type_success_model.items():
            if model["total_decisions"] == 0:
                continue
            report += f"  {hyp_type}:\n"
            report += f"    Decisions: {model['total_decisions']}\n"
            report += f"    Win rate: {model['win_rate']:.1%}\n"

        report += "\n🔝 TOP FEATURE IMPORTANCE:\n"
        sorted_features = sorted(self.feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for feature, importance in sorted_features:
            direction = "🟢 +" if importance > 0 else "🔴 -"
            report += f"  {direction} {feature} ({importance:+.2f})\n"

        report += f"\n📈 UNIQUE PATTERNS LEARNED: {len(self.pattern_success_rates)}\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        return report
