"""
Decision Registry - NIVEL 5
Logs EVERY signal, hypothesis, and score with full context
Later: Records actual outcomes and validates against reality

This makes MIE auditable and operationally honest.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class DecisionSnapshot:
    """Complete state at moment of decision"""
    timestamp: str
    asset: str
    current_price: float
    momentum_1h: str
    momentum_4h: str
    momentum_24h: str
    trend: str
    volatility: str
    volatility_signal: str


@dataclass
class DecisionRecord:
    """One complete decision event with context and (later) outcomes"""
    # Decision details
    decision_id: str  # UUID
    timestamp: str
    asset: str

    # State snapshot at decision time
    state_snapshot: Dict  # DecisionSnapshot as dict

    # Hypothesis that triggered
    hypothesis_id: str
    hypothesis_text: str
    hypothesis_type: str  # momentum_shift, volatility_spike, breakout
    hypothesis_direction: str  # UP, DOWN
    backtest_score: float  # 0-1
    expected_outcome: str

    # Alert candidate (shadow alert = no notification yet)
    alert_triggered: bool
    alert_confidence: float

    # Outcomes (filled in later by outcome tracker)
    outcome_1h: Optional[Dict] = None  # {price, change_pct, win}
    outcome_4h: Optional[Dict] = None
    outcome_24h: Optional[Dict] = None

    # Evaluation (filled after outcomes collected)
    evaluation_1h: Optional[Dict] = None  # {predicted, actual, correct}
    evaluation_4h: Optional[Dict] = None
    evaluation_24h: Optional[Dict] = None
    accuracy_score: Optional[float] = None


class DecisionRegistry:
    """
    Logs all MIE decisions and validates against reality.

    This is the "operational truth layer" that ensures MIE
    doesn't fool itself about what works.
    """

    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("DecisionRegistry")
        self.active_decisions = []  # Decisions waiting for outcomes
        self.completed_decisions = []  # Decisions with full evaluation

    def record_hypothesis_decision(self, hypothesis: Dict, state_cache, backtest_score: float) -> str:
        """
        Log a hypothesis decision with full context.

        Returns decision_id for later outcome tracking.
        """
        try:
            from uuid import uuid4
            decision_id = str(uuid4())[:8]

            # Create state snapshot
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "asset": hypothesis.get("asset", "UNKNOWN"),
                "current_price": 0.0,  # Will be filled from cache
                "momentum_1h": state_cache.momentum_1h.get(hypothesis.get("asset")) if state_cache else "?",
                "momentum_4h": state_cache.momentum_4h.get(hypothesis.get("asset")) if state_cache else "?",
                "momentum_24h": state_cache.momentum_24h.get(hypothesis.get("asset")) if state_cache else "?",
                "trend": state_cache.trend.get(hypothesis.get("asset")) if state_cache else "?",
                "volatility": state_cache.volatility.get(hypothesis.get("asset")) if state_cache else "?",
                "volatility_signal": state_cache.volatility_signal.get(hypothesis.get("asset")) if state_cache else "?",
            }

            # Create decision record
            record = DecisionRecord(
                decision_id=decision_id,
                timestamp=datetime.utcnow().isoformat(),
                asset=hypothesis.get("asset", "UNKNOWN"),
                state_snapshot=snapshot,
                hypothesis_id=hypothesis.get("id"),
                hypothesis_text=hypothesis.get("hypothesis", ""),
                hypothesis_type=hypothesis.get("type", "unknown"),
                hypothesis_direction=hypothesis.get("direction", "?"),
                backtest_score=backtest_score,
                expected_outcome=hypothesis.get("expected_outcome", ""),
                alert_triggered=True,  # All decisions are "alert candidates"
                alert_confidence=backtest_score,  # Use backtest score as confidence
            )

            # Store in active decisions
            self.active_decisions.append(asdict(record))

            # Log to DB if available
            if self.db:
                self._persist_decision(record)

            self.logger.info(
                f"📋 Decision recorded: {decision_id} - {record.asset} - "
                f"{record.hypothesis_type} (score={backtest_score:.2f})"
            )

            return decision_id

        except Exception as e:
            self.logger.error(f"Error recording decision: {e}")
            return None

    def record_outcome_1h(self, decision_id: str, price: float, previous_price: float) -> None:
        """Record what happened 1 hour later"""
        decision = self._find_decision(decision_id)
        if not decision:
            return

        change_pct = ((price - previous_price) / previous_price) * 100
        direction = decision.get("hypothesis_direction", "?")

        # Check if prediction was correct
        if direction == "UP":
            correct = price > previous_price
        elif direction == "DOWN":
            correct = price < previous_price
        else:
            correct = False

        decision["outcome_1h"] = {
            "price": price,
            "change_pct": change_pct,
            "win": correct
        }

        self.logger.debug(f"⏱️  Outcome recorded for {decision_id} at +1h")

    def record_outcome_4h(self, decision_id: str, price: float, entry_price: float) -> None:
        """Record what happened 4 hours later"""
        decision = self._find_decision(decision_id)
        if not decision:
            return

        change_pct = ((price - entry_price) / entry_price) * 100
        direction = decision.get("hypothesis_direction", "?")

        if direction == "UP":
            correct = price > entry_price
        elif direction == "DOWN":
            correct = price < entry_price
        else:
            correct = False

        decision["outcome_4h"] = {
            "price": price,
            "change_pct": change_pct,
            "win": correct
        }

        self.logger.debug(f"⏱️  Outcome recorded for {decision_id} at +4h")

    def record_outcome_24h(self, decision_id: str, price: float, entry_price: float) -> None:
        """Record what happened 24 hours later"""
        decision = self._find_decision(decision_id)
        if not decision:
            return

        change_pct = ((price - entry_price) / entry_price) * 100
        direction = decision.get("hypothesis_direction", "?")

        if direction == "UP":
            correct = price > entry_price
        elif direction == "DOWN":
            correct = price < entry_price
        else:
            correct = False

        decision["outcome_24h"] = {
            "price": price,
            "change_pct": change_pct,
            "win": correct
        }

        # Once we have 24h outcome, evaluate and archive
        self._evaluate_decision(decision)

    def get_shadow_alerts(self) -> List[Dict]:
        """Get all alerts that WOULD trigger (shadow = not sent yet)"""
        alerts = []
        for decision in self.active_decisions:
            if decision.get("alert_triggered"):
                alerts.append({
                    "decision_id": decision.get("decision_id"),
                    "asset": decision.get("asset"),
                    "hypothesis": decision.get("hypothesis_text"),
                    "confidence": decision.get("alert_confidence"),
                    "timestamp": decision.get("timestamp"),
                    "outcome": "pending"  # No outcome yet
                })
        return alerts

    def get_validation_metrics(self) -> Dict:
        """Calculate accuracy metrics from completed decisions"""
        if not self.completed_decisions:
            return {
                "total_decisions": 0,
                "accuracy_1h": 0.0,
                "accuracy_4h": 0.0,
                "accuracy_24h": 0.0,
                "false_alert_rate": 0.0,
                "avg_confidence": 0.0,
                "coherence": 0.0,
            }

        total = len(self.completed_decisions)

        # 1h accuracy
        decisions_1h = [d for d in self.completed_decisions if d.get("outcome_1h")]
        accuracy_1h = sum(1 for d in decisions_1h if d["outcome_1h"].get("win")) / len(decisions_1h) if decisions_1h else 0.0

        # 4h accuracy
        decisions_4h = [d for d in self.completed_decisions if d.get("outcome_4h")]
        accuracy_4h = sum(1 for d in decisions_4h if d["outcome_4h"].get("win")) / len(decisions_4h) if decisions_4h else 0.0

        # 24h accuracy
        decisions_24h = [d for d in self.completed_decisions if d.get("outcome_24h")]
        accuracy_24h = sum(1 for d in decisions_24h if d["outcome_24h"].get("win")) / len(decisions_24h) if decisions_24h else 0.0

        # Average confidence (backtest score)
        avg_confidence = sum(d.get("backtest_score", 0) for d in self.completed_decisions) / total if total > 0 else 0.0

        # Coherence: Do high-confidence predictions perform better?
        high_confidence = [d for d in self.completed_decisions if d.get("backtest_score", 0) >= 0.65]
        low_confidence = [d for d in self.completed_decisions if d.get("backtest_score", 0) < 0.65]

        high_conf_wins = sum(1 for d in high_confidence if d.get("outcome_24h", {}).get("win")) / len(high_confidence) if high_confidence else 0.0
        low_conf_wins = sum(1 for d in low_confidence if d.get("outcome_24h", {}).get("win")) / len(low_confidence) if low_confidence else 0.0

        coherence = high_conf_wins - low_conf_wins  # Positive = good coherence

        return {
            "total_decisions": total,
            "accuracy_1h": round(accuracy_1h, 3),
            "accuracy_4h": round(accuracy_4h, 3),
            "accuracy_24h": round(accuracy_24h, 3),
            "false_alert_rate": round(1.0 - accuracy_24h, 3),
            "avg_confidence": round(avg_confidence, 3),
            "coherence": round(coherence, 3),
            "high_confidence_wins": round(high_conf_wins, 3),
            "low_confidence_wins": round(low_conf_wins, 3),
        }

    def format_validation_report(self) -> str:
        """Generate human-readable validation report"""
        metrics = self.get_validation_metrics()

        if metrics["total_decisions"] == 0:
            return (
                "📊 VALIDATION REPORT\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⏳ No decisions recorded yet\n"
                "Waiting for first hypothesis..."
            )

        verdict = "✅ COHERENT" if metrics["coherence"] > 0.1 else "⚠️  INCOHERENT"

        return (
            f"📊 VALIDATION REPORT (NIVEL 5)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Total decisions: {metrics['total_decisions']}\n"
            f"\n📈 Accuracy by timeframe:\n"
            f"  +1h:   {metrics['accuracy_1h']:.1%}\n"
            f"  +4h:   {metrics['accuracy_4h']:.1%}\n"
            f"  +24h:  {metrics['accuracy_24h']:.1%}\n"
            f"\n🎯 Confidence Analysis:\n"
            f"  Avg score: {metrics['avg_confidence']:.2f}\n"
            f"  High-conf wins: {metrics['high_confidence_wins']:.1%}\n"
            f"  Low-conf wins: {metrics['low_confidence_wins']:.1%}\n"
            f"  Coherence: {metrics['coherence']:+.2f} {verdict}\n"
            f"\n🚨 False alert rate: {metrics['false_alert_rate']:.1%}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    def _find_decision(self, decision_id: str) -> Optional[Dict]:
        """Find decision in active or completed lists"""
        for decision in self.active_decisions:
            if decision.get("decision_id") == decision_id:
                return decision
        for decision in self.completed_decisions:
            if decision.get("decision_id") == decision_id:
                return decision
        return None

    def _evaluate_decision(self, decision: Dict) -> None:
        """
        Evaluate decision after 24h outcome collected.
        Move from active to completed.
        """
        if decision in self.active_decisions:
            self.active_decisions.remove(decision)

        self.completed_decisions.append(decision)
        self.logger.info(f"✅ Decision evaluated and archived: {decision.get('decision_id')}")

    def _persist_decision(self, record: DecisionRecord) -> None:
        """Store decision in database for audit trail"""
        try:
            if self.db:
                self.db.add_observation(
                    asset=record.asset,
                    observation_type="decision_record",
                    value=float(record.backtest_score),
                    context=json.dumps({
                        "decision_id": record.decision_id,
                        "hypothesis_id": record.hypothesis_id,
                        "hypothesis_type": record.hypothesis_type,
                        "alert_triggered": record.alert_triggered,
                        "timestamp": record.timestamp,
                    })
                )
        except Exception as e:
            self.logger.error(f"Error persisting decision: {e}")
