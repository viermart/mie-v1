"""
Market State Engine para MIE
Calcula estado del mercado en tiempo real:
- cambio 1h/4h/24h
- volatilidad
- funding rate
- volumen relativo
- fuerza ETH vs BTC
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics


class MarketStateEngine:
    """Calcula métricas de mercado a partir de observaciones."""

    def __init__(self, db):
        """
        Args:
            db: MIEDatabase instance
        """
        self.db = db

    def get_price_changes(self, asset: str) -> Dict[str, float]:
        """
        Calcula cambios de precio en diferentes timeframes.

        Args:
            asset: "BTC" o "ETH"

        Returns:
            {
                "change_1h": float,
                "change_4h": float,
                "change_24h": float,
                "current_price": float
            }
        """
        try:
            obs_24h = self.db.get_observations(
                asset=asset,
                lookback_hours=24,
                observation_type="price"
            )
            obs_4h = self.db.get_observations(
                asset=asset,
                lookback_hours=4,
                observation_type="price"
            )
            obs_1h = self.db.get_observations(
                asset=asset,
                lookback_hours=1,
                observation_type="price"
            )

            if not obs_24h:
                return {
                    "change_1h": 0.0,
                    "change_4h": 0.0,
                    "change_24h": 0.0,
                    "current_price": 0.0
                }

            # Precios ordenados por tiempo (más antiguos primero)
            prices_24h = [o["value"] for o in sorted(obs_24h, key=lambda x: x["timestamp"])]
            prices_4h = [o["value"] for o in sorted(obs_4h, key=lambda x: x["timestamp"])]
            prices_1h = [o["value"] for o in sorted(obs_1h, key=lambda x: x["timestamp"])]

            current = prices_24h[-1] if prices_24h else 0
            price_1h_ago = prices_1h[0] if len(prices_1h) > 0 else current
            price_4h_ago = prices_4h[0] if len(prices_4h) > 0 else current
            price_24h_ago = prices_24h[0] if len(prices_24h) > 0 else current

            change_1h = self._calc_change(price_1h_ago, current)
            change_4h = self._calc_change(price_4h_ago, current)
            change_24h = self._calc_change(price_24h_ago, current)

            return {
                "change_1h": change_1h,
                "change_4h": change_4h,
                "change_24h": change_24h,
                "current_price": current
            }
        except Exception as e:
            return {
                "change_1h": 0.0,
                "change_4h": 0.0,
                "change_24h": 0.0,
                "current_price": 0.0,
                "error": str(e)
            }

    def get_volatility(self, asset: str, hours: int = 24) -> float:
        """
        Calcula volatilidad simple (std dev de cambios por hora).

        Args:
            asset: "BTC" o "ETH"
            hours: período en horas

        Returns:
            Volatilidad como porcentaje
        """
        try:
            obs = self.db.get_observations(
                asset=asset,
                lookback_hours=hours,
                observation_type="price"
            )

            if len(obs) < 2:
                return 0.0

            prices = [o["value"] for o in sorted(obs, key=lambda x: x["timestamp"])]

            # Calcular cambios horarios
            changes = []
            for i in range(1, len(prices)):
                change = self._calc_change(prices[i-1], prices[i])
                changes.append(change)

            if not changes:
                return 0.0

            # Desviación estándar de cambios = volatilidad
            if len(changes) > 1:
                vol = statistics.stdev(changes)
            else:
                vol = abs(changes[0])

            return abs(vol)
        except Exception as e:
            return 0.0

    def get_volume_change(self, asset: str) -> float:
        """
        Volumen relativo: cambio en volumen últimas 24h.

        Args:
            asset: "BTC" o "ETH"

        Returns:
            Cambio de volumen en %
        """
        try:
            obs_24h = self.db.get_observations(
                asset=asset,
                lookback_hours=24,
                observation_type="volume"
            )
            obs_12h = self.db.get_observations(
                asset=asset,
                lookback_hours=12,
                observation_type="volume"
            )

            if not obs_24h or not obs_12h:
                return 0.0

            vol_first_12h = sum([o["value"] for o in obs_24h if
                               o["timestamp"] < (datetime.utcnow() - timedelta(hours=12)).isoformat()])
            vol_last_12h = sum([o["value"] for o in obs_12h])

            if vol_first_12h == 0:
                return 0.0

            return ((vol_last_12h - vol_first_12h) / vol_first_12h) * 100
        except Exception:
            return 0.0

    def get_eth_btc_ratio(self) -> Optional[float]:
        """
        Calcula ratio de fuerza ETH vs BTC.
        Cuanto más alto, más fuerte ETH relativo a BTC.

        Returns:
            Ratio ETH/BTC como porcentaje
        """
        try:
            btc_data = self.get_price_changes("BTC")
            eth_data = self.get_price_changes("ETH")

            if btc_data["current_price"] == 0 or eth_data["current_price"] == 0:
                return None

            ratio = (eth_data["current_price"] / btc_data["current_price"]) * 100

            return ratio
        except Exception:
            return None

    def get_market_context(self) -> Dict[str, any]:
        """
        Genera contexto general del mercado.

        Returns:
            {
                "timestamp": str,
                "btc": { cambios, vol, precio },
                "eth": { cambios, vol, precio },
                "eth_btc_ratio": float,
                "overall_volatility": str,  # "low", "medium", "high"
                "market_direction": str,    # "bullish", "bearish", "neutral"
            }
        """
        try:
            btc_data = self.get_price_changes("BTC")
            eth_data = self.get_price_changes("ETH")
            btc_vol = self.get_volatility("BTC")
            eth_vol = self.get_volatility("ETH")
            eth_btc_ratio = self.get_eth_btc_ratio()

            # Determinar volatilidad general
            avg_vol = (btc_vol + eth_vol) / 2 if btc_vol and eth_vol else 0
            if avg_vol > 2.0:
                vol_level = "high"
            elif avg_vol > 0.8:
                vol_level = "medium"
            else:
                vol_level = "low"

            # Determinar dirección del mercado
            btc_24h = btc_data["change_24h"]
            eth_24h = eth_data["change_24h"]
            avg_change = (btc_24h + eth_24h) / 2

            if avg_change > 0.5:
                direction = "bullish 📈"
            elif avg_change < -0.5:
                direction = "bearish 📉"
            else:
                direction = "neutral ➡️"

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "btc": {
                    "price": btc_data["current_price"],
                    "change_1h": btc_data["change_1h"],
                    "change_4h": btc_data["change_4h"],
                    "change_24h": btc_data["change_24h"],
                    "volatility": btc_vol
                },
                "eth": {
                    "price": eth_data["current_price"],
                    "change_1h": eth_data["change_1h"],
                    "change_4h": eth_data["change_4h"],
                    "change_24h": eth_data["change_24h"],
                    "volatility": eth_vol
                },
                "eth_btc_ratio": eth_btc_ratio,
                "overall_volatility": vol_level,
                "market_direction": direction,
                "avg_24h_change": avg_change
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _calc_change(self, price_old: float, price_new: float) -> float:
        """Calcula cambio porcentual."""
        if price_old == 0:
            return 0.0
        return ((price_new - price_old) / price_old) * 100
