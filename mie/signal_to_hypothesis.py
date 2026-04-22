"""
Signal-to-Hypothesis Engine for MIE V1 Research Layer
Converts market scanner signals into research hypotheses.

Components:
- SignalInterpreter: Translate signal type to research question
- HypothesisGenerator: Generate hypothesis from signal + context
- ContextualAnalyzer: Enrich signal with multi-asset context
- TriggerManager: Track which signals have been processed
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from mie.market_scanner import Signal, SignalType


class HypothesisType(Enum):
    """Hypothesis origin types."""
    SIGNAL_DRIVEN = "signal_driven"
    CONTEXT_DRIVEN = "context_driven"
    CORRELATION_DRIVEN = "correlation_driven"
    SCHEDULED = "scheduled"


@dataclass
class SignalContext:
    """Rich context around a signal."""
    signal: Signal
    asset: str
    timeframe: str
    current_price: float
    price_change_24h: float
    volume_ratio: float
    correlation_other_assets: Dict[str, float]
    recent_signals: List[Signal]
    market_regime: str  # bullish, bearish, neutral


class SignalInterpreter:
    """Translate signal types to research questions."""

    def __init__(self):
        self.signal_questions = {
            SignalType.SUPPORT_BREAK: [
                f"{{asset}} breaking below support: Is this the start of a downtrend?",
                f"{{asset}} support break on {{volume_context}}: How deep will it retrace?",
            ],
            SignalType.RESISTANCE_BREAK: [
                f"{{asset}} breaking above resistance: Is this sustainable?",
                f"{{asset}} resistance break: Will it hold above {{level}}?",
            ],
            SignalType.CONSOLIDATION: [
                f"{{asset}} consolidating for {{duration}}: Which direction will it break?",
                f"{{asset}} range-bound: Is this accumulation or distribution?",
            ],
            SignalType.VOLUME_SPIKE: [
                f"{{asset}} volume spike: Is this accumulation or panic selling?",
                f"{{asset}} volume surge: How does this correlate to price action?",
            ],
            SignalType.ACCUMULATION: [
                f"{{asset}} accumulation pattern: Will this lead to upside breakout?",
                f"{{asset}} rising price on high volume: Strength indicator?",
            ],
            SignalType.VOLATILITY_EXPANSION: [
                f"{{asset}} volatility expanding: Is a breakout imminent?",
                f"{{asset}} volatility surge: What's the directional bias?",
            ],
            SignalType.MEAN_REVERSION_SETUP: [
                f"{{asset}} volatility compression: When will the breakout occur?",
                f"{{asset}} trapped volatility: What's the likely direction?",
            ],
            SignalType.CORRELATION_SHIFT: [
                f"{{asset}} correlation shift: Does this indicate regime change?",
                f"{{asset}} decoupling from {{other_asset}}: What's driving the divergence?",
            ],
            SignalType.DIVERGENCE: [
                f"{{asset}} price/indicator divergence: Reversal signal?",
                f"{{asset}} divergence detected: What's the likelihood of correction?",
            ],
        }

    def get_research_questions(self, signal: Signal) -> List[str]:
        """Generate research questions for a signal."""
        questions = self.signal_questions.get(signal.signal_type, [])
        
        # Simple templating
        formatted = []
        for q in questions:
            q = q.replace("{asset}", signal.asset)
            q = q.replace("{timeframe}", signal.timeframe)
            formatted.append(q)
        
        return formatted

    def interpret_signal_strength(self, signal: Signal) -> str:
        """Interpret signal strength as text."""
        if signal.strength > 0.85:
            return "very_strong"
        elif signal.strength > 0.70:
            return "strong"
        elif signal.strength > 0.55:
            return "moderate"
        else:
            return "weak"


class ContextualAnalyzer:
    """Enrich signals with market context."""

    def __init__(self, logger=None):
        self.logger = logger

    def build_context(self, signal: Signal, 
                     current_price: float,
                     price_history: List[float],
                     volume_history: List[float],
                     other_assets_prices: Optional[Dict[str, float]] = None) -> SignalContext:
        """Build enriched context for a signal."""
        
        # Calculate price change
        price_change_24h = 0
        if len(price_history) > 24:
            price_change_24h = (price_history[-1] - price_history[-24]) / price_history[-24]

        # Calculate volume ratio
        volume_ratio = 1.0
        if len(volume_history) > 1:
            avg_volume = sum(volume_history[-20:]) / 20 if len(volume_history) >= 20 else sum(volume_history) / len(volume_history)
            volume_ratio = volume_history[-1] / avg_volume if avg_volume > 0 else 1.0

        # Detect correlations
        correlations = {}
        if other_assets_prices:
            # Simple correlation proxy
            for asset, price in other_assets_prices.items():
                correlations[asset] = 0.5  # Placeholder

        # Determine regime
        regime = "neutral"
        if price_change_24h > 0.02:
            regime = "bullish"
        elif price_change_24h < -0.02:
            regime = "bearish"

        return SignalContext(
            signal=signal,
            asset=signal.asset,
            timeframe=signal.timeframe,
            current_price=current_price,
            price_change_24h=price_change_24h,
            volume_ratio=volume_ratio,
            correlation_other_assets=correlations,
            recent_signals=[],
            market_regime=regime
        )


class HypothesisGenerator:
    """Generate hypotheses from signals."""

    def __init__(self, logger=None):
        self.logger = logger
        self.interpreter = SignalInterpreter()

    def generate_from_signal(self, context: SignalContext) -> Dict[str, Any]:
        """Generate hypothesis from signal context."""
        signal = context.signal
        
        questions = self.interpreter.get_research_questions(signal)
        strength_text = self.interpreter.interpret_signal_strength(signal)
        
        hypothesis_id = f"SH_{signal.asset}_{signal.signal_type.value}_{int(datetime.utcnow().timestamp())}"

        hypothesis = {
            "id": hypothesis_id,
            "origin_type": HypothesisType.SIGNAL_DRIVEN.value,
            "signal_type": signal.signal_type.value,
            "asset": signal.asset,
            "timeframe": signal.timeframe,
            "created_at": datetime.utcnow().isoformat(),
            "created_from_signal": signal.detected_at,
            
            # Research focus
            "primary_question": questions[0] if questions else "Market signal detected",
            "research_questions": questions,
            
            # Initial confidence
            "initial_confidence": min(0.85, signal.confidence + 0.1),
            "signal_strength": strength_text,
            
            # Context
            "market_context": {
                "regime": context.market_regime,
                "price_change_24h": context.price_change_24h,
                "volume_ratio": context.volume_ratio,
                "current_price": context.current_price
            },
            
            # Signal metadata
            "signal_metadata": signal.metadata,
            
            # Success criteria (provisional)
            "success_criteria": self._generate_success_criteria(signal, context),
            
            # Validation strategy
            "validation_strategy": self._generate_validation_strategy(signal, context),
            
            # Status
            "status": "queued",
            "priority": self._calculate_priority(signal, context)
        }

        return hypothesis

    def _generate_success_criteria(self, signal: Signal, context: SignalContext) -> List[str]:
        """Generate testable success criteria."""
        criteria = []
        
        if signal.signal_type == SignalType.RESISTANCE_BREAK:
            criteria.append(f"Price sustains above {signal.metadata.get('sr_level', 'resistance')} for 4h+")
            criteria.append(f"Volume confirms breakout (>1.5x average)")
        elif signal.signal_type == SignalType.SUPPORT_BREAK:
            criteria.append(f"Price stays below {signal.metadata.get('sr_level', 'support')} for 4h+")
            criteria.append(f"Volume confirms breakdown (>1.5x average)")
        elif signal.signal_type == SignalType.ACCUMULATION:
            criteria.append("Price breaks above consolidation within 7 days")
            criteria.append("Volume sustains elevated during breakout")
        elif signal.signal_type == SignalType.VOLATILITY_EXPANSION:
            criteria.append("Volatility-driven move >2% within 24h")
            criteria.append("Direction aligns with previous trend")
        
        return criteria if criteria else ["Signal validates over defined timeframe"]

    def _generate_validation_strategy(self, signal: Signal, context: SignalContext) -> Dict[str, Any]:
        """Define how to validate this hypothesis."""
        return {
            "primary_metric": "price_movement",
            "timeframes": ["1h", "4h", "1d"],
            "lookback": 7,  # days
            "validation_window": 14,  # days
            "backtest_period": "3m",  # Backtest on 3 months of history
            "required_data": ["price", "volume", "correlation"],
            "confidence_thresholds": {
                "weak": 0.3,
                "moderate": 0.6,
                "strong": 0.8
            }
        }

    def _calculate_priority(self, signal: Signal, context: SignalContext) -> str:
        """Determine hypothesis priority."""
        score = signal.confidence * signal.strength
        
        # Boost priority for high-regime-alignment signals
        if context.market_regime == "bullish" and signal.signal_type in [
            SignalType.RESISTANCE_BREAK, SignalType.ACCUMULATION
        ]:
            score += 0.15
        elif context.market_regime == "bearish" and signal.signal_type in [
            SignalType.SUPPORT_BREAK
        ]:
            score += 0.15

        if score > 0.80:
            return "critical"
        elif score > 0.65:
            return "high"
        elif score > 0.50:
            return "normal"
        else:
            return "low"


class TriggerManager:
    """Track signal processing and prevent duplicate hypotheses."""

    def __init__(self, storage_dir: str = "data/triggers"):
        from pathlib import Path
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.processed_signals: Dict[str, str] = {}  # signal_hash -> hypothesis_id
        self._load_history()

    def _load_history(self):
        """Load processed signal history."""
        history_file = self.storage_dir / "signal_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.processed_signals = data.get("processed", {})
            except:
                pass

    def _save_history(self):
        """Persist signal processing history."""
        try:
            history_file = self.storage_dir / "signal_history.json"
            with open(history_file, 'w') as f:
                json.dump({"processed": self.processed_signals}, f, indent=2)
        except:
            pass

    def create_signal_hash(self, signal: Signal) -> str:
        """Create unique identifier for signal."""
        # Hash based on type, asset, timeframe, and approximate timestamp
        ts = signal.detected_at[:13]  # hour-level granularity
        return f"{signal.signal_type.value}_{signal.asset}_{signal.timeframe}_{ts}"

    def is_duplicate(self, signal: Signal) -> bool:
        """Check if signal already generated hypothesis."""
        sig_hash = self.create_signal_hash(signal)
        return sig_hash in self.processed_signals

    def mark_processed(self, signal: Signal, hypothesis_id: str) -> None:
        """Record that signal has been processed."""
        sig_hash = self.create_signal_hash(signal)
        self.processed_signals[sig_hash] = hypothesis_id
        self._save_history()

    def get_processed_count(self) -> int:
        """Get total signals processed."""
        return len(self.processed_signals)


class SignalToHypothesisEngine:
    """Unified engine: signals → hypotheses."""

    def __init__(self, logger=None):
        self.logger = logger
        self.interpreter = SignalInterpreter()
        self.analyzer = ContextualAnalyzer(logger=logger)
        self.generator = HypothesisGenerator(logger=logger)
        self.trigger_manager = TriggerManager()

    def process_signal(self, signal: Signal,
                      current_price: float,
                      price_history: List[float],
                      volume_history: List[float],
                      other_assets: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
        """End-to-end: signal → hypothesis."""
        
        # Check if duplicate
        if self.trigger_manager.is_duplicate(signal):
            return None

        # Build context
        context = self.analyzer.build_context(
            signal, current_price, price_history, volume_history, other_assets
        )

        # Generate hypothesis
        hypothesis = self.generator.generate_from_signal(context)

        # Mark as processed
        self.trigger_manager.mark_processed(signal, hypothesis["id"])

        return hypothesis

    def process_signal_batch(self, signals: List[Signal],
                            market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process multiple signals."""
        hypotheses = []
        
        for signal in signals:
            if signal.asset not in market_data:
                continue

            asset_data = market_data[signal.asset]
            hyp = self.process_signal(
                signal=signal,
                current_price=asset_data.get("current_price", 0),
                price_history=asset_data.get("price_history", []),
                volume_history=asset_data.get("volume_history", []),
                other_assets={k: v.get("current_price", 0) 
                            for k, v in market_data.items() if k != signal.asset}
            )

            if hyp:
                hypotheses.append(hyp)

        return hypotheses
