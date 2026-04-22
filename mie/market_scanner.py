"""
Market Scanner for MIE V1 Research Layer
Detects high-quality signals across multiple assets and timeframes.

Components:
- PriceActionScanner: Identify support/resistance, breakouts, consolidations
- VolumeScanner: Volume spikes, accumulation/distribution patterns
- VolatilityScanner: Volatility expansion, mean-reversion setups
- CorrelationScanner: Lead-lag relationships, divergence detection
- SignalAggregator: Combine signals with quality scoring
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class SignalType(Enum):
    """Enumeration of detectable signal types."""
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"
    CONSOLIDATION = "consolidation"
    VOLUME_SPIKE = "volume_spike"
    ACCUMULATION = "accumulation"
    VOLATILITY_EXPANSION = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    MEAN_REVERSION_SETUP = "mean_reversion_setup"
    CORRELATION_SHIFT = "correlation_shift"
    DIVERGENCE = "divergence"


class SignalStrength(Enum):
    """Signal quality rating."""
    WEAK = 0.4
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.95


@dataclass
class Signal:
    """Structure for a detected market signal."""
    signal_type: SignalType
    asset: str
    timeframe: str
    detected_at: str
    price: float
    strength: float
    confidence: float
    metadata: Dict[str, Any]
    summary: str

    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type.value,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "detected_at": self.detected_at,
            "price": self.price,
            "strength": self.strength,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "summary": self.summary
        }


class PriceActionScanner:
    """Detect price action patterns."""

    def __init__(self, lookback: int = 50):
        self.lookback = lookback

    def detect_support_resistance(self, prices: List[float]) -> Dict[str, float]:
        """Identify support and resistance levels."""
        if len(prices) < self.lookback:
            return {}

        recent = prices[-self.lookback:]
        
        # Simple: recent highs and lows as S/R
        support = min(recent)
        resistance = max(recent)
        midpoint = (support + resistance) / 2

        return {
            "support": support,
            "resistance": resistance,
            "midpoint": midpoint,
            "range": resistance - support
        }

    def detect_breakout(self, prices: List[float], sr_level: float, 
                       direction: str = "up") -> Optional[Signal]:
        """Detect breakout above/below support/resistance."""
        if len(prices) < 3:
            return None

        current = prices[-1]
        previous = prices[-2]

        if direction == "up" and previous <= sr_level < current:
            return Signal(
                signal_type=SignalType.RESISTANCE_BREAK,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=current,
                strength=0.7,
                confidence=0.75,
                metadata={
                    "sr_level": sr_level,
                    "breakout_magnitude": current - sr_level,
                    "previous_price": previous
                },
                summary=f"Breakout above {sr_level:.2f}"
            )
        elif direction == "down" and current < sr_level <= previous:
            return Signal(
                signal_type=SignalType.SUPPORT_BREAK,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=current,
                strength=0.7,
                confidence=0.75,
                metadata={
                    "sr_level": sr_level,
                    "breakout_magnitude": sr_level - current,
                    "previous_price": previous
                },
                summary=f"Breakout below {sr_level:.2f}"
            )

        return None

    def detect_consolidation(self, prices: List[float], threshold: float = 0.02) -> Optional[Signal]:
        """Detect consolidation/range-bound movement."""
        if len(prices) < 10:
            return None

        recent = prices[-10:]
        range_pct = (max(recent) - min(recent)) / min(recent)

        if range_pct < threshold:
            return Signal(
                signal_type=SignalType.CONSOLIDATION,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=prices[-1],
                strength=0.6,
                confidence=0.8,
                metadata={
                    "range_pct": range_pct,
                    "high": max(recent),
                    "low": min(recent),
                    "days": 10
                },
                summary=f"Consolidation: {range_pct*100:.2f}% range"
            )

        return None


class VolumeScanner:
    """Detect volume patterns."""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def calculate_avg_volume(self, volumes: List[float]) -> float:
        """Calculate average volume over lookback period."""
        if not volumes:
            return 0
        return sum(volumes[-self.lookback:]) / min(len(volumes), self.lookback)

    def detect_volume_spike(self, volumes: List[float], 
                           multiplier: float = 1.5) -> Optional[Signal]:
        """Detect abnormal volume spike."""
        if len(volumes) < self.lookback + 1:
            return None

        avg = self.calculate_avg_volume(volumes[:-1])
        current = volumes[-1]

        if current > avg * multiplier:
            return Signal(
                signal_type=SignalType.VOLUME_SPIKE,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=0,
                strength=0.75,
                confidence=min(0.95, (current / avg) * 0.5),
                metadata={
                    "current_volume": current,
                    "avg_volume": avg,
                    "ratio": current / avg
                },
                summary=f"Volume spike: {(current/avg):.2f}x average"
            )

        return None

    def detect_accumulation(self, closes: List[float], volumes: List[float]) -> Optional[Signal]:
        """Detect accumulation (rising price on high volume)."""
        if len(closes) < 5 or len(volumes) < 5:
            return None

        recent_closes = closes[-5:]
        recent_volumes = volumes[-5:]

        price_rising = recent_closes[-1] > recent_closes[0]
        volume_high = recent_volumes[-1] > sum(recent_volumes[:-1]) / 4

        if price_rising and volume_high:
            return Signal(
                signal_type=SignalType.ACCUMULATION,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=closes[-1],
                strength=0.7,
                confidence=0.8,
                metadata={
                    "price_change": recent_closes[-1] - recent_closes[0],
                    "avg_volume": sum(recent_volumes) / 5,
                    "current_volume": recent_volumes[-1]
                },
                summary="Accumulation pattern detected"
            )

        return None


class VolatilityScanner:
    """Detect volatility patterns."""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility as percentage change std dev."""
        if len(prices) < 2:
            return 0

        changes = [(prices[i] - prices[i-1]) / prices[i-1] 
                   for i in range(1, len(prices))]

        if not changes:
            return 0

        avg = sum(changes) / len(changes)
        variance = sum((x - avg) ** 2 for x in changes) / len(changes)
        return variance ** 0.5

    def detect_volatility_expansion(self, prices: List[float], 
                                   multiplier: float = 1.5) -> Optional[Signal]:
        """Detect volatility increase."""
        if len(prices) < self.lookback + 5:
            return None

        historical_vol = self.calculate_volatility(prices[:-5])
        recent_vol = self.calculate_volatility(prices[-5:])

        if historical_vol > 0 and recent_vol > historical_vol * multiplier:
            return Signal(
                signal_type=SignalType.VOLATILITY_EXPANSION,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=prices[-1],
                strength=0.8,
                confidence=0.85,
                metadata={
                    "historical_vol": historical_vol,
                    "recent_vol": recent_vol,
                    "ratio": recent_vol / historical_vol if historical_vol > 0 else 0
                },
                summary=f"Volatility expansion: {(recent_vol/historical_vol):.2f}x"
            )

        return None

    def detect_mean_reversion_setup(self, prices: List[float]) -> Optional[Signal]:
        """Detect extreme volatility contraction (potential breakout setup)."""
        if len(prices) < 20:
            return None

        vol = self.calculate_volatility(prices[-20:])
        historical_vol = self.calculate_volatility(prices[-40:-20])

        if historical_vol > 0 and vol < historical_vol * 0.5:
            return Signal(
                signal_type=SignalType.MEAN_REVERSION_SETUP,
                asset="",
                timeframe="",
                detected_at=datetime.utcnow().isoformat(),
                price=prices[-1],
                strength=0.65,
                confidence=0.7,
                metadata={
                    "current_vol": vol,
                    "historical_vol": historical_vol,
                    "compression_ratio": vol / historical_vol
                },
                summary="Volatility compression detected - potential breakout"
            )

        return None


class CorrelationScanner:
    """Detect correlation and divergence patterns."""

    def detect_correlation_shift(self, asset1_prices: List[float],
                                asset2_prices: List[float],
                                lookback: int = 20) -> Optional[Signal]:
        """Detect significant change in asset correlation."""
        if len(asset1_prices) < lookback or len(asset2_prices) < lookback:
            return None

        try:
            # Simple correlation calculation
            a1 = asset1_prices[-lookback:]
            a2 = asset2_prices[-lookback:]

            mean1 = sum(a1) / len(a1)
            mean2 = sum(a2) / len(a2)

            cov = sum((a1[i] - mean1) * (a2[i] - mean2) for i in range(len(a1))) / len(a1)
            std1 = (sum((x - mean1) ** 2 for x in a1) / len(a1)) ** 0.5
            std2 = (sum((x - mean2) ** 2 for x in a2) / len(a2)) ** 0.5

            if std1 > 0 and std2 > 0:
                corr = cov / (std1 * std2)

                if abs(corr) > 0.7:
                    return Signal(
                        signal_type=SignalType.CORRELATION_SHIFT,
                        asset="",
                        timeframe="",
                        detected_at=datetime.utcnow().isoformat(),
                        price=0,
                        strength=0.7,
                        confidence=0.8,
                        metadata={
                            "correlation": corr,
                            "strength": "strong" if abs(corr) > 0.85 else "moderate"
                        },
                        summary=f"Strong correlation detected: {corr:.3f}"
                    )
        except:
            pass

        return None


class SignalAggregator:
    """Combine signals and rank by quality."""

    def __init__(self, logger=None):
        self.logger = logger
        self.signals: List[Signal] = []

    def add_signal(self, signal: Signal) -> None:
        """Add detected signal to aggregation."""
        if signal:
            self.signals.append(signal)

    def get_quality_score(self, signal: Signal) -> float:
        """Calculate overall signal quality (0-1)."""
        # Weight: confidence (60%) + strength (40%)
        return signal.confidence * 0.6 + signal.strength * 0.4

    def get_top_signals(self, limit: int = 10) -> List[Signal]:
        """Return highest-quality signals."""
        scored = [(sig, self.get_quality_score(sig)) for sig in self.signals]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [sig for sig, _ in scored[:limit]]

    def get_signals_by_asset(self, asset: str) -> List[Signal]:
        """Filter signals by asset."""
        return [sig for sig in self.signals if sig.asset == asset]

    def get_signals_by_type(self, signal_type: SignalType) -> List[Signal]:
        """Filter signals by type."""
        return [sig for sig in self.signals if sig.signal_type == signal_type]

    def clear_old_signals(self, hours: int = 24) -> int:
        """Remove signals older than N hours."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        before = len(self.signals)
        self.signals = [sig for sig in self.signals if sig.detected_at > cutoff]
        return before - len(self.signals)

    def get_scan_report(self) -> Dict[str, Any]:
        """Generate scanning report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_signals": len(self.signals),
            "by_type": {
                st.value: len(self.get_signals_by_type(st))
                for st in SignalType
            },
            "top_10": [
                {
                    **sig.to_dict(),
                    "quality_score": self.get_quality_score(sig)
                }
                for sig in self.get_top_signals(10)
            ],
            "average_confidence": sum(s.confidence for s in self.signals) / len(self.signals) if self.signals else 0
        }
