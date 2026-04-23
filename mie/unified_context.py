"""
Unified Context Provider - Single source of truth for all interactions
Reads from DB on every request - never stale, never missing data
Used by both commands and dialogue for consistent state
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List


class UnifiedContextProvider:
    """
    Provides real-time market context from DB for both commands and dialogue.
    No caching - always fresh data from source.
    """

    def __init__(self, db, logger=None):
        self.db = db
        self.logger = logger

    def get_market_context(self) -> Dict:
        """
        Get latest market state from DB.
        Used by both commands (/btc, /eth, /market) and dialogue ("como está btc?")
        """
        try:
            # Get latest 24h observations
            btc_obs = self.db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
            eth_obs = self.db.get_observations(asset="ETH", lookback_hours=24, observation_type="price")

            if not btc_obs or not eth_obs:
                return {
                    "error": "Insufficient data",
                    "btc": None,
                    "eth": None,
                    "observation_count": {
                        "btc": len(btc_obs) if btc_obs else 0,
                        "eth": len(eth_obs) if eth_obs else 0,
                    }
                }

            # Extract latest prices
            btc_price = btc_obs[-1]["value"] if btc_obs else None
            eth_price = eth_obs[-1]["value"] if eth_obs else None

            # Calculate simple momentum (last 3 points)
            btc_momentum = self._calculate_momentum(btc_obs[-3:] if len(btc_obs) >= 3 else btc_obs)
            eth_momentum = self._calculate_momentum(eth_obs[-3:] if len(eth_obs) >= 3 else eth_obs)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "btc": {
                    "price": btc_price,
                    "momentum": btc_momentum,
                    "observation_count": len(btc_obs),
                    "latest_observation": btc_obs[-1] if btc_obs else None,
                },
                "eth": {
                    "price": eth_price,
                    "momentum": eth_momentum,
                    "observation_count": len(eth_obs),
                    "latest_observation": eth_obs[-1] if eth_obs else None,
                }
            }

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error getting market context: {e}")
            return {"error": str(e)}

    def get_decision_context(self) -> Dict:
        """
        Get active decisions and hypotheses from DB.
        Used by /validation, /hypothesis, and dialogue about predictions.
        """
        try:
            # This assumes decision_registry has a way to query from DB
            # If not, we'll need to implement it
            return {
                "note": "Decision context requires decision_registry implementation"
            }
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error getting decision context: {e}")
            return {"error": str(e)}

    def get_dialogue_prompt_context(self, message: str) -> str:
        """
        Build context string for Claude based on user message.
        Analyzes message to determine what data is relevant.
        """
        market_data = self.get_market_context()

        if "error" in market_data:
            return f"[SIN DATOS DE MERCADO: {market_data['error']}]"

        btc = market_data.get("btc", {})
        eth = market_data.get("eth", {})

        # Build context based on what user is asking about
        context = "CONTEXTO ACTUAL DEL MERCADO (datos en tiempo real de BD):\n"

        # Always include both if they exist
        if btc.get("price"):
            context += f"- BTC: ${btc['price']:,.2f} | Trend: {btc['momentum']}\n"

        if eth.get("price"):
            context += f"- ETH: ${eth['price']:,.2f} | Trend: {eth['momentum']}\n"

        context += f"- Actualizado: {market_data.get('timestamp', 'unknown')}\n"
        context += f"- Observaciones: BTC={btc.get('observation_count', 0)}, ETH={eth.get('observation_count', 0)}\n"

        return context

    def _calculate_momentum(self, observations: List[Dict]) -> str:
        """Calculate simple momentum from price series"""
        if not observations or len(observations) < 2:
            return "INSUFFICIENT_DATA"

        prices = [obs["value"] for obs in observations]

        if len(prices) < 3:
            # Just check if last > first
            if prices[-1] > prices[0]:
                return "UP"
            elif prices[-1] < prices[0]:
                return "DOWN"
            else:
                return "FLAT"

        # Check if consistently moving up or down
        changes = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]

        if all(c > 0 for c in changes):
            return "STRONG_UP"
        elif all(c < 0 for c in changes):
            return "STRONG_DOWN"
        elif sum(c > 0 for c in changes) > sum(c < 0 for c in changes):
            return "UP"
        elif sum(c < 0 for c in changes) > sum(c > 0 for c in changes):
            return "DOWN"
        else:
            return "SIDEWAYS"
