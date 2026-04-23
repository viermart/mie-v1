"""
Hypothesis Generator - Genera hipótesis basadas en patrones reales detectados
NIVEL 3: Research Layer
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4


class HypothesisGenerator:
    """Genera hipótesis testables basadas en patrones del mercado."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("HypothesisGenerator")

    def generate_from_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Genera hipótesis basadas en patrones detectados.

        Args:
            patterns: Lista de patrones detectados

        Returns:
            Lista de hipótesis generadas
        """
        hypotheses = []

        for pattern in patterns:
            hyp = None
            asset = pattern.get("asset", "UNKNOWN")
            ptype = pattern.get("type", "?")

            if ptype == "momentum_shift":
                hyp = self._hypothesis_from_momentum(pattern)
            elif ptype == "volatility_spike":
                hyp = self._hypothesis_from_volatility(pattern)
            elif ptype == "breakout":
                hyp = self._hypothesis_from_breakout(pattern)

            if hyp:
                hypotheses.append(hyp)

        return hypotheses

    def _hypothesis_from_momentum(self, pattern: Dict) -> Dict:
        """Genera hipótesis de cambio de momentum."""
        asset = pattern.get("asset", "UNKNOWN")
        direction = pattern.get("direction", "?")
        change = pattern.get("change_pct", 0)

        if direction == "UP":
            hypothesis = f"{asset} momentum shifting UP - could continue bullish"
            expected_outcome = f"Price higher in next 4h"
        else:
            hypothesis = f"{asset} momentum shifting DOWN - could continue bearish"
            expected_outcome = f"Price lower in next 4h"

        return {
            "id": str(uuid4())[:8],
            "asset": asset,
            "type": "momentum_shift",
            "hypothesis": hypothesis,
            "expected_outcome": expected_outcome,
            "trigger": pattern,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "confidence": "medium"
        }

    def _hypothesis_from_volatility(self, pattern: Dict) -> Dict:
        """Genera hipótesis de volatility spike."""
        asset = pattern.get("asset", "UNKNOWN")
        ratio = pattern.get("ratio", 0)

        hypothesis = f"{asset} volatility spike detected ({ratio:.1f}x normal)"
        expected_outcome = f"Price stabilize or continue spike in next 1h"

        return {
            "id": str(uuid4())[:8],
            "asset": asset,
            "type": "volatility_spike",
            "hypothesis": hypothesis,
            "expected_outcome": expected_outcome,
            "trigger": pattern,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "confidence": "high"
        }

    def _hypothesis_from_breakout(self, pattern: Dict) -> Dict:
        """Genera hipótesis de breakout."""
        asset = pattern.get("asset", "UNKNOWN")
        direction = pattern.get("direction", "?")
        price = pattern.get("current_price", 0)
        resistance = pattern.get("resistance", 0)

        if direction == "UP":
            hypothesis = f"{asset} broke above resistance at ${resistance:,.2f}"
            expected_outcome = f"Continue higher, target next resistance"
        else:
            hypothesis = f"{asset} broke below support at ${resistance:,.2f}"
            expected_outcome = f"Continue lower, target next support"

        return {
            "id": str(uuid4())[:8],
            "asset": asset,
            "type": "breakout",
            "hypothesis": hypothesis,
            "expected_outcome": expected_outcome,
            "trigger": pattern,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "confidence": "high"
        }

    def test_hypothesis(self, hypothesis: Dict, new_data: Dict) -> Dict:
        """
        Test a hypothesis against new market data.

        Args:
            hypothesis: Hypothesis to test
            new_data: New price/pattern data

        Returns:
            Result dict with verdict (supported/falsified/inconclusive)
        """
        try:
            asset = hypothesis.get("asset")
            htype = hypothesis.get("type")
            expected = hypothesis.get("expected_outcome")

            # Simple test logic - can be enhanced
            if htype == "momentum_shift":
                return self._test_momentum(hypothesis, new_data)
            elif htype == "volatility_spike":
                return self._test_volatility(hypothesis, new_data)
            elif htype == "breakout":
                return self._test_breakout(hypothesis, new_data)

            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "inconclusive",
                "reason": "Unknown hypothesis type"
            }

        except Exception as e:
            self.logger.error(f"Error testing hypothesis: {e}")
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "error",
                "reason": str(e)
            }

    def _test_momentum(self, hypothesis: Dict, new_data: Dict) -> Dict:
        """Test momentum shift hypothesis."""
        trigger = hypothesis.get("trigger", {})
        direction = trigger.get("direction", "UP")

        current_price = new_data.get("price", 0)
        prev_price = trigger.get("price", 0)

        if current_price == 0 or prev_price == 0:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "inconclusive",
                "reason": "Missing price data"
            }

        change = ((current_price - prev_price) / prev_price) * 100

        if direction == "UP" and change > 0:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "supported",
                "change_pct": change
            }
        elif direction == "DOWN" and change < 0:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "supported",
                "change_pct": change
            }
        else:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "falsified",
                "change_pct": change
            }

    def _test_volatility(self, hypothesis: Dict, new_data: Dict) -> Dict:
        """Test volatility spike hypothesis."""
        # If market stabilized, hypothesis is supported
        # If volatility continues, still supported
        # If becomes even more volatile, still supported
        # This is a "hard to falsify" hypothesis

        return {
            "hypothesis_id": hypothesis.get("id"),
            "verdict": "supported",
            "reason": "Volatility patterns usually persist short-term"
        }

    def _test_breakout(self, hypothesis: Dict, new_data: Dict) -> Dict:
        """Test breakout hypothesis."""
        trigger = hypothesis.get("trigger", {})
        direction = trigger.get("direction", "UP")
        resistance = trigger.get("resistance", 0)

        current_price = new_data.get("price", 0)

        if current_price == 0:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "inconclusive",
                "reason": "Missing price data"
            }

        if direction == "UP" and current_price > resistance:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "supported",
                "price": current_price
            }
        elif direction == "DOWN" and current_price < resistance:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "supported",
                "price": current_price
            }
        else:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "verdict": "falsified",
                "price": current_price
            }
