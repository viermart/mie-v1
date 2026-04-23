"""
MIE State Cache - In-memory snapshot of current market state
Updated by fast_loop every 5 minutes
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from statistics import mean, stdev


class MIEStateCache:
    """In-memory cache of current market state for fast command responses."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("StateCache")

        # Latest observations
        self.last_btc_obs = None
        self.last_eth_obs = None
        self.last_update = None

        # Momentum signals
        self.momentum_1h = {}      # {asset: "STRONG" | "MODERATE" | "WEAK" | "NEUTRAL"}
        self.momentum_4h = {}
        self.momentum_24h = {}

        # Volatility
        self.volatility = {}       # {asset: float (std dev)}
        self.volatility_signal = {} # {asset: "HIGH" | "MODERATE" | "LOW"}

        # Trend
        self.trend = {}            # {asset: "BULLISH" | "BEARISH" | "NEUTRAL"}

        # Alert state
        self.active_alerts = {}    # {asset: [alert_dict, ...]}
        self.last_alert_scan = None

    def update_from_observations(self, btc_obs_list: List[Dict], eth_obs_list: List[Dict]):
        """Update cache from latest observations from DB."""
        try:
            # Update latest observations
            if btc_obs_list:
                self.last_btc_obs = btc_obs_list[-1]
            if eth_obs_list:
                self.last_eth_obs = eth_obs_list[-1]

            self.last_update = datetime.utcnow().isoformat()

            # Calculate momentum for both assets
            if btc_obs_list:
                self._calc_momentum("BTC", btc_obs_list)
            if eth_obs_list:
                self._calc_momentum("ETH", eth_obs_list)

            self.logger.debug("✅ State cache updated")
        except Exception as e:
            self.logger.error(f"Error updating state cache: {e}")

    def _calc_momentum(self, asset: str, obs_list: List[Dict]):
        """Calculate momentum signals for 1h, 4h, 24h."""
        if len(obs_list) < 2:
            self.momentum_1h[asset] = "NEUTRAL"
            self.momentum_4h[asset] = "NEUTRAL"
            self.momentum_24h[asset] = "NEUTRAL"
            self.trend[asset] = "NEUTRAL"
            return

        current_price = obs_list[-1]["value"]

        # 1h: Last 12 observations (5 min each = 60 min)
        if len(obs_list) >= 12:
            price_1h_ago = obs_list[-12]["value"]
            change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
            self.momentum_1h[asset] = self._signal_from_change(change_1h)
        else:
            self.momentum_1h[asset] = "NEUTRAL"

        # 4h: Last 48 observations (5 min each = 240 min)
        if len(obs_list) >= 48:
            price_4h_ago = obs_list[-48]["value"]
            change_4h = ((current_price - price_4h_ago) / price_4h_ago) * 100
            self.momentum_4h[asset] = self._signal_from_change(change_4h)
        else:
            self.momentum_4h[asset] = "NEUTRAL"

        # 24h: All observations (should be ~288 for perfect 5min intervals in 24h)
        if len(obs_list) >= 2:
            price_24h_ago = obs_list[0]["value"]
            change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
            self.momentum_24h[asset] = self._signal_from_change(change_24h)
        else:
            self.momentum_24h[asset] = "NEUTRAL"

        # Overall trend based on 4h momentum
        self.trend[asset] = "BULLISH" if self.momentum_4h[asset] in ["STRONG", "MODERATE"] else \
                           "BEARISH" if self.momentum_4h[asset] == "WEAK" else \
                           "NEUTRAL"

        # Calculate volatility
        self._calc_volatility(asset, obs_list)

    def _signal_from_change(self, change_pct: float) -> str:
        """Convert % change to signal strength."""
        abs_change = abs(change_pct)

        if abs_change > 2.0:
            return "STRONG"
        elif abs_change > 0.5:
            return "MODERATE"
        elif abs_change > 0.1:
            return "WEAK"
        else:
            return "NEUTRAL"

    def _calc_volatility(self, asset: str, obs_list: List[Dict]):
        """Calculate volatility (std dev of 1h changes)."""
        try:
            if len(obs_list) < 3:
                self.volatility[asset] = 0.0
                self.volatility_signal[asset] = "LOW"
                return

            # Use last 12 observations for 1h volatility
            window = min(12, len(obs_list))
            prices = [obs["value"] for obs in obs_list[-window:]]

            if len(prices) < 2:
                self.volatility[asset] = 0.0
                self.volatility_signal[asset] = "LOW"
                return

            # Calculate 1min changes
            changes = []
            for i in range(1, len(prices)):
                pct_change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
                changes.append(pct_change)

            if changes:
                volatility_value = stdev(changes) if len(changes) > 1 else 0.0
                self.volatility[asset] = volatility_value

                # Signal
                if volatility_value > 0.5:
                    self.volatility_signal[asset] = "HIGH"
                elif volatility_value > 0.1:
                    self.volatility_signal[asset] = "MODERATE"
                else:
                    self.volatility_signal[asset] = "LOW"
        except Exception as e:
            self.logger.error(f"Error calculating volatility for {asset}: {e}")
            self.volatility[asset] = 0.0
            self.volatility_signal[asset] = "UNKNOWN"

    def set_active_alerts(self, asset: str, alerts: List[Dict]):
        """Update active alerts for an asset."""
        self.active_alerts[asset] = alerts
        self.last_alert_scan = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        """Export cache state as dict for debugging."""
        return {
            "timestamp": self.last_update,
            "btc": {
                "latest_price": self.last_btc_obs["value"] if self.last_btc_obs else None,
                "momentum_1h": self.momentum_1h.get("BTC"),
                "momentum_4h": self.momentum_4h.get("BTC"),
                "momentum_24h": self.momentum_24h.get("BTC"),
                "trend": self.trend.get("BTC"),
                "volatility": self.volatility.get("BTC"),
                "volatility_signal": self.volatility_signal.get("BTC"),
            },
            "eth": {
                "latest_price": self.last_eth_obs["value"] if self.last_eth_obs else None,
                "momentum_1h": self.momentum_1h.get("ETH"),
                "momentum_4h": self.momentum_4h.get("ETH"),
                "momentum_24h": self.momentum_24h.get("ETH"),
                "trend": self.trend.get("ETH"),
                "volatility": self.volatility.get("ETH"),
                "volatility_signal": self.volatility_signal.get("ETH"),
            },
            "alerts": self.active_alerts,
            "last_alert_scan": self.last_alert_scan,
        }
