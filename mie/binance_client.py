"""
MIE Binance Integration - Observación de mercado

Obtiene datos en tiempo real de BTCUSDT y ETHUSDT:
- Price, Funding Rate, Open Interest, Volume
- Timestamps en UTC
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional


class BinanceClient:
    def __init__(self, timeout: int = 10):
        self.base_url = "https://api.binance.com/api/v3"
        self.futures_url = "https://fapi.binance.com/fapi/v1"
        self.timeout = timeout

    def get_ticker(self, symbol: str) -> Dict:
        """Obtiene ticker actual (price, volume, etc.)"""
        try:
            endpoint = f"{self.base_url}/ticker/24hr"
            params = {"symbol": symbol}
            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error obteniendo ticker para {symbol}: {e}")

    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Obtiene funding rate actual (solo futures)"""
        try:
            endpoint = f"{self.futures_url}/fundingRate"
            params = {"symbol": symbol, "limit": 1}
            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except requests.RequestException as e:
            raise Exception(f"Error obteniendo funding rate para {symbol}: {e}")

    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Obtiene open interest (solo futures)"""
        try:
            endpoint = f"{self.futures_url}/openInterest"
            params = {"symbol": symbol}
            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error obteniendo open interest para {symbol}: {e}")

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 24) -> List[List]:
        """Obtiene velas OHLCV histórico"""
        try:
            endpoint = f"{self.base_url}/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error obteniendo klines para {symbol}: {e}")

    def ingest_observation(self, asset: str) -> Dict:
        """
        Ingesta completa: obtiene ticker + funding + OI para un asset
        Retorna dict con todos los datos crudos para persistir
        """
        ticker = self.get_ticker(f"{asset}USDT")
        funding = self.get_funding_rate(f"{asset}USDT")
        oi = self.get_open_interest(f"{asset}USDT")

        return {
            "asset": asset,
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "funding_rate": funding,
            "open_interest": oi,
        }

    def parse_observation(self, raw: Dict) -> Dict:
        """
        Parsea observación cruda en campos atomizados para BD
        Retorna dict con valores individuales
        """
        ticker = raw["ticker"]
        funding = raw["funding_rate"]
        oi = raw["open_interest"]

        return {
            "asset": raw["asset"],
            "timestamp": raw["timestamp"],
            "price": float(ticker.get("lastPrice", 0)),
            "price_24h_change": float(ticker.get("priceChangePercent", 0)),
            "volume_24h": float(ticker.get("volume", 0)),
            "volume_usdt_24h": float(ticker.get("quoteAssetVolume", 0)),
            "funding_rate": float(funding.get("fundingRate", 0)) if funding else None,
            "funding_time": funding.get("time") if funding else None,
            "open_interest": float(oi.get("openInterest", 0)) if oi else None,
            "open_interest_value": float(oi.get("sumOpenInterestValue", 0)) if oi else None,
        }
