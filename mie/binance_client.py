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
    def __init__(self, timeout: int = 10, logger=None):
        import logging
        from .market_provider import BinanceProvider, CoinGeckoProvider, MarketDataManager
        from .synthetic_market_provider import SyntheticMarketProvider

        self.base_url = "https://api.binance.com/api/v3"
        self.futures_url = "https://fapi.binance.com/fapi/v1"
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Inicializa market manager con fallback
        binance = BinanceProvider(self.logger)
        coingecko = CoinGeckoProvider(self.logger)
        self.market_manager = MarketDataManager(binance, coingecko, self.logger)

        # Synthetic provider como último recurso si APIs están bloqueadas
        self.synthetic_provider = SyntheticMarketProvider(self.logger)

    def get_ticker(self, symbol: str) -> Dict:
        """
        Obtiene ticker actual usando market_manager con fallback a synthetic.
        Si todas las APIs reales fallan (451, timeout, etc), usa datos sintéticos.
        """
        try:
            ticker = self.market_manager.get_ticker(symbol)
            if ticker:
                return ticker
        except Exception as e:
            self.logger.warning(f"market_manager failed for {symbol}: {e}")

        # Fallback a synthetic provider
        self.logger.warning(f"⚠️  Using SYNTHETIC data for {symbol}")
        return self.synthetic_provider.get_ticker(symbol)

    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene funding rate actual (solo futures).
        Fallback a synthetic si Binance Futures falla.
        """
        try:
            endpoint = f"{self.futures_url}/fundingRate"
            params = {"symbol": symbol, "limit": 1}
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except requests.RequestException as e:
            self.logger.warning(f"Binance Futures unavailable for {symbol}: {e}. Using synthetic funding rate.")
            return self.synthetic_provider.get_funding_rate(symbol)

    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene open interest (solo futures).
        Fallback a synthetic si Binance Futures falla.
        """
        try:
            endpoint = f"{self.futures_url}/openInterest"
            params = {"symbol": symbol}
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.warning(f"Binance Futures unavailable for {symbol}: {e}. Using synthetic open interest.")
            return self.synthetic_provider.get_open_interest(symbol)

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 24) -> List[List]:
        """Obtiene velas OHLCV histórico"""
        try:
            endpoint = f"{self.base_url}/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Error obteniendo klines para {symbol}: {e}")

    def ingest_observation(self, asset: str) -> Dict:
        """
        Ingesta completa: obtiene ticker + funding + OI para un asset
        Retorna dict con todos los datos crudos para persistir
        Si Binance falla (451, etc), retorna None y deja que fast_loop lo maneje gracefully
        """
        try:
            ticker = self.get_ticker(f"{asset}USDT")
            if not ticker:
                self.logger.warning(f"No ticker data for {asset}")
                return None

            funding = self.get_funding_rate(f"{asset}USDT")
            oi = self.get_open_interest(f"{asset}USDT")

            return {
                "asset": asset,
                "timestamp": datetime.utcnow().isoformat(),
                "ticker": ticker,
                "funding_rate": funding,
                "open_interest": oi,
            }
        except Exception as e:
            self.logger.error(f"Error ingesting {asset}: {e}")
            return None

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
            "price": float(ticker.get("price", 0)),
            "price_24h_change": float(ticker.get("change_24h", 0)),
            "volume_24h": float(ticker.get("volume_24h", 0)),
            "volume_usdt_24h": float(ticker.get("volume_24h", 0)),
            "funding_rate": float(funding.get("fundingRate", 0)) if funding else None,
            "funding_time": funding.get("time") if funding else None,
            "open_interest": float(oi.get("openInterest", 0)) if oi else None,
            "open_interest_value": float(oi.get("sumOpenInterestValue", 0)) if oi else None,
        }
