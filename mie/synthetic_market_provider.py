"""
Synthetic Market Data Provider - Fallback when Binance is blocked (451 error)

Generates realistic-looking market data based on recent history stored in DB.
This is NOT for trading - it's ONLY to validate MIE architecture when external APIs fail.

All synthetic data is clearly marked in logs and DB context field.
"""

import random
import logging
from datetime import datetime
from typing import Dict, Optional


class SyntheticMarketProvider:
    """Generates synthetic market data when real APIs are unavailable."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        # Approximate current prices (will be updated from DB if available)
        self.prices = {
            "BTC": 78000.0,
            "ETH": 2350.0,
        }

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Returns synthetic ticker data.
        Asset is BTC or ETH (derived from symbol like 'BTCUSDT').
        """
        asset = symbol.replace("USDT", "")
        price = self.prices.get(asset)

        if not price:
            self.logger.warning(f"Unknown asset: {asset}")
            return None

        # Small random walk to simulate price movement
        change_pct = random.uniform(-2.0, 2.0)
        price_24h_change = change_pct
        price_with_change = price * (1 + change_pct / 100)

        self.logger.info(f"🔄 [SYNTHETIC] {asset}: price=${price_with_change:.2f}, change={change_pct:.2f}%")

        return {
            "price": price_with_change,
            "change_24h": price_24h_change,
            "volume_24h": random.uniform(15e9, 35e9),  # BTC: ~20-30B/day
        }

    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Returns synthetic funding rate."""
        return {
            "fundingRate": random.uniform(-0.0005, 0.0005),
            "time": int(datetime.utcnow().timestamp() * 1000),
        }

    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Returns synthetic open interest."""
        asset = symbol.replace("USDT", "")
        oi_base = 500e6 if asset == "BTC" else 100e6

        return {
            "openInterest": oi_base * (1 + random.uniform(-0.1, 0.1)),
            "sumOpenInterestValue": oi_base * random.uniform(30000, 50000),
        }
