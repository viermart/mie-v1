"""
Market Data Provider Layer
Implementa primary + fallback providers para obtener datos de mercado.
"""

import requests
import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod


class MarketProvider(ABC):
    """Interfaz base para proveedores de datos de mercado."""
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Obtiene ticker de mercado. Retorna dict con price, change_24h, volume_24h, etc."""
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor."""
        pass


class BinanceProvider(MarketProvider):
    """Proveedor Binance (primary)."""
    
    def __init__(self, logger=None):
        self.base_url = "https://api.binance.com/api/v3"
        self.logger = logger or logging.getLogger(__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
    
    def name(self) -> str:
        return "Binance"
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """symbol = 'BTCUSDT'"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            params = {"symbol": symbol}
            response = requests.get(url, params=params, headers=self.headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return {
                "symbol": symbol,
                "price": float(data["lastPrice"]),
                "change_24h": float(data["priceChangePercent"]),
                "volume_24h": float(data["quoteAssetVolume"]),
                "high_24h": float(data["highPrice"]),
                "low_24h": float(data["lowPrice"]),
            }
        except Exception as e:
            self.logger.error(f"Binance fetch error ({symbol}): {e}")
            return None


class CoinGeckoProvider(MarketProvider):
    """Proveedor CoinGecko (fallback). API pública, sin autenticación."""
    
    def __init__(self, logger=None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.logger = logger or logging.getLogger(__name__)
    
    def name(self) -> str:
        return "CoinGecko"
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """symbol = 'BTCUSDT' o 'ETHUSDT'. Mapea a coin_id de CoinGecko."""
        try:
            # Mapeo simple: BTCUSDT -> bitcoin, ETHUSDT -> ethereum
            coin_map = {
                "BTCUSDT": "bitcoin",
                "ETHUSDT": "ethereum",
            }
            coin_id = coin_map.get(symbol)
            if not coin_id:
                self.logger.warning(f"CoinGecko: Unknown symbol {symbol}")
                return None
            
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currency": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_high_low_24h": "true",
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            coin_data = data.get(coin_id, {})
            
            if not coin_data:
                return None
            
            return {
                "symbol": symbol,
                "price": float(coin_data.get("usd", 0)),
                "change_24h": float(coin_data.get("usd_24h_change", 0)),
                "volume_24h": float(coin_data.get("usd_24h_vol", 0)),
                "high_24h": float(coin_data.get("usd_24h_high", 0)),
                "low_24h": float(coin_data.get("usd_24h_low", 0)),
            }
        except Exception as e:
            self.logger.error(f"CoinGecko fetch error ({symbol}): {e}")
            return None


class MarketDataManager:
    """Gestor de providers con fallback automático."""
    
    def __init__(self, primary_provider: MarketProvider, fallback_provider: MarketProvider, logger=None):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.logger = logger or logging.getLogger(__name__)
    
    def get_ticker(self, symbol: str) -> Dict:
        """Intenta primary, luego fallback. Retorna datos + provider usado."""
        # Intenta primary
        data = self.primary.get_ticker(symbol)
        if data:
            data["provider"] = self.primary.name()
            return data
        
        self.logger.warning(f"Primary provider ({self.primary.name()}) failed, trying fallback...")
        
        # Intenta fallback
        data = self.fallback.get_ticker(symbol)
        if data:
            data["provider"] = self.fallback.name()
            self.logger.info(f"Fallback provider ({self.fallback.name()}) successful for {symbol}")
            return data
        
        self.logger.error(f"Both providers failed for {symbol}")
        return {
            "symbol": symbol,
            "price": 0,
            "change_24h": 0,
            "volume_24h": 0,
            "provider": "NONE",
            "error": "All providers failed"
        }
