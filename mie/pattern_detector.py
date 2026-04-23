"""
Pattern Detector - Detecta cambios importantes en el mercado
Usado por Research Layer para generar hipótesis
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime


class PatternDetector:
    """Detecta patrones y cambios importantes en observaciones."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("PatternDetector")

    def detect_momentum_shift(self, obs_list: List[Dict], asset: str) -> Optional[Dict]:
        """
        Detecta cambio de momentum (de STRONG a WEAK o viceversa).
        Retorna dict con detalles del cambio.
        """
        if len(obs_list) < 2:
            return None

        try:
            # Comparar últimas 2 observaciones
            prev_price = obs_list[-2]["value"]
            curr_price = obs_list[-1]["value"]

            change = ((curr_price - prev_price) / prev_price) * 100

            # Detectar cambios notables (>0.5%)
            if abs(change) > 0.5:
                direction = "UP" if change > 0 else "DOWN"
                return {
                    "asset": asset,
                    "type": "momentum_shift",
                    "direction": direction,
                    "change_pct": change,
                    "timestamp": obs_list[-1].get("timestamp"),
                    "price": curr_price
                }
        except Exception as e:
            self.logger.error(f"Error detecting momentum shift: {e}")

        return None

    def detect_volatility_spike(self, obs_list: List[Dict], asset: str) -> Optional[Dict]:
        """
        Detecta picos de volatilidad (cambios bruscos).
        """
        if len(obs_list) < 3:
            return None

        try:
            # Última observación
            last_change = 0.0
            if len(obs_list) >= 2:
                prev = obs_list[-2]["value"]
                curr = obs_list[-1]["value"]
                last_change = ((curr - prev) / prev) * 100

            # Volatilidad anterior (promedio de cambios previos)
            if len(obs_list) >= 12:
                recent_changes = []
                for i in range(-12, -1):
                    if i < -1:
                        p1 = obs_list[i]["value"]
                        p2 = obs_list[i+1]["value"]
                        change = ((p2 - p1) / p1) * 100
                        recent_changes.append(abs(change))

                avg_volatility = sum(recent_changes) / len(recent_changes) if recent_changes else 0

                # Si última observación es 3x más volátil que promedio
                if abs(last_change) > (avg_volatility * 3):
                    return {
                        "asset": asset,
                        "type": "volatility_spike",
                        "magnitude": abs(last_change),
                        "avg_volatility": avg_volatility,
                        "ratio": abs(last_change) / (avg_volatility + 0.001),
                        "timestamp": obs_list[-1].get("timestamp"),
                        "price": obs_list[-1]["value"]
                    }
        except Exception as e:
            self.logger.error(f"Error detecting volatility spike: {e}")

        return None

    def detect_breakout(self, obs_list: List[Dict], asset: str) -> Optional[Dict]:
        """
        Detecta si el precio rompió resistencia/soporte reciente.
        """
        if len(obs_list) < 3:
            return None

        try:
            current_price = obs_list[-1]["value"]

            # Encontrar high/low de últimas 12 observaciones
            if len(obs_list) >= 12:
                recent_prices = [obs["value"] for obs in obs_list[-12:]]
            else:
                recent_prices = [obs["value"] for obs in obs_list]

            high = max(recent_prices)
            low = min(recent_prices)

            # Si precio actual es new high o new low
            if current_price > high or current_price < low:
                breakout_type = "UP" if current_price > high else "DOWN"
                return {
                    "asset": asset,
                    "type": "breakout",
                    "direction": breakout_type,
                    "current_price": current_price,
                    "resistance": high if breakout_type == "UP" else low,
                    "timestamp": obs_list[-1].get("timestamp")
                }
        except Exception as e:
            self.logger.error(f"Error detecting breakout: {e}")

        return None

    def detect_all_patterns(self, asset_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Ejecuta todos los detectores para todos los assets.
        Retorna lista de patrones detectados.
        """
        patterns = []

        for asset, obs_list in asset_data.items():
            if not obs_list:
                continue

            # Detect momentum
            momentum = self.detect_momentum_shift(obs_list, asset)
            if momentum:
                patterns.append(momentum)

            # Detect volatility
            volatility = self.detect_volatility_spike(obs_list, asset)
            if volatility:
                patterns.append(volatility)

            # Detect breakout
            breakout = self.detect_breakout(obs_list, asset)
            if breakout:
                patterns.append(breakout)

        return patterns
