"""
Debug Service para MIE
Diagnóstico en tiempo real del pipeline de observación end-to-end.

Stages:
1. Data ingestion (Binance API)
2. Parsing
3. Persistence (SQLite)
4. Query layer
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path


class DebugService:
    """Sistema de diagnósticos para debugging del pipeline."""

    def __init__(self, db, binance_client, logger=None):
        self.db = db
        self.binance = binance_client
        self.logger = logger or logging.getLogger("MIE.Debug")
        self.debug_log_path = Path("logs") / "debug.log"
        self.debug_log_path.parent.mkdir(exist_ok=True)

    def _log_debug(self, stage: str, asset: str, data: Dict, status: str = "INFO"):
        """Guarda debug log con timestamp."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "stage": stage,
            "asset": asset,
            "status": status,
            "data": data
        }

        with open(self.debug_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        self.logger.info(f"[{stage}] {asset}: {status} - {json.dumps(data)[:100]}")

    def test_binance_fetch(self, symbol: str = "BTCUSDT") -> str:
        """Test market data fetch con inspeccion de raw response."""
        try:
            result = self.binance.market_manager.get_ticker(symbol)
            
            lines = []
            lines.append(f"DEBUG: Market Data for {symbol}")
            lines.append("")
            lines.append(f"Provider: {result.get('provider', 'unknown')}")
            lines.append(f"HTTP Code: {result.get('http_code', 'N/A')}")
            lines.append(f"Status: {result.get('status', 'N/A')}")
            lines.append("")
            
            if 'raw_response' in result and isinstance(result.get('raw_response'), dict):
                raw = result['raw_response']
                lines.append(f"Raw Response Keys: {list(raw.keys())}")
                lines.append(f"Raw Data (truncated): {str(raw)[:500]}")
                lines.append("")
            
            lines.append(f"Parsed Price: {result.get('price', 'N/A')}")
            lines.append(f"Parsed Volume: {result.get('volume_24h', 'N/A')}")
            lines.append(f"Parsed Change: {result.get('change_24h', 'N/A')}")
            lines.append("")
            
            if result.get('http_code') != 200:
                lines.append(f"WARNING - HTTP Error: {result.get('http_code')}")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"ERROR in test_binance_fetch: {str(e)}"

    def test_parsing(self, asset: str = "BTC") -> Dict:
        """
        STAGE 2: Verifica que el parsing funciona correctamente.
        Returns: {"status": "ok"|"error", "parsed_fields": {...}}
        """
        self.logger.info(f"🔍 STAGE 2: Parsing para {asset}...")

        try:
            raw = self.binance.ingest_observation(asset)
            parsed = self.binance.parse_observation(raw)

            required_fields = ["asset", "price", "timestamp"]
            missing = [f for f in required_fields if f not in parsed or parsed[f] is None]

            if missing:
                self._log_debug("STAGE2_PARSE", asset, {
                    "error": f"Missing fields: {missing}",
                    "parsed": parsed
                }, "ERROR")
                return {
                    "status": "error",
                    "message": f"Missing fields: {missing}"
                }

            self._log_debug("STAGE2_PARSE", asset, {
                "price": parsed["price"],
                "price_24h_change": parsed.get("price_24h_change"),
                "volume_24h": parsed.get("volume_24h"),
                "timestamp": parsed["timestamp"]
            }, "OK")

            return {
                "status": "ok",
                "parsed_fields": {k: v for k, v in parsed.items() if v is not None}
            }

        except Exception as e:
            self._log_debug("STAGE2_PARSE", asset, {"error": str(e)}, "ERROR")
            return {"status": "error", "message": str(e)}

    def test_persistence(self, asset: str = "BTC") -> Dict:
        """
        STAGE 3: Verifica que se persiste en SQLite correctamente.
        Returns: {"status": "ok"|"error", "rows_before": int, "rows_after": int}
        """
        self.logger.info(f"🔍 STAGE 3: Persistence para {asset}...")

        try:
            rows_before = self.db.count_observations(asset, lookback_hours=24)
            self.logger.info(f"   Rows before: {rows_before}")

            raw = self.binance.ingest_observation(asset)
            parsed = self.binance.parse_observation(raw)

            self.db.add_observation(
                asset=asset,
                observation_type="price",
                value=parsed["price"],
                context=f"24h_change: {parsed.get('price_24h_change', 0):.2f}%"
            )

            rows_after = self.db.count_observations(asset, lookback_hours=24)
            self.logger.info(f"   Rows after: {rows_after}")

            if rows_after > rows_before:
                self._log_debug("STAGE3_PERSIST", asset, {
                    "rows_before": rows_before,
                    "rows_after": rows_after,
                    "price_stored": parsed["price"]
                }, "OK")

                return {
                    "status": "ok",
                    "rows_before": rows_before,
                    "rows_after": rows_after,
                    "price_stored": parsed["price"]
                }
            else:
                self._log_debug("STAGE3_PERSIST", asset, {
                    "error": "No rows added to database",
                    "rows_before": rows_before,
                    "rows_after": rows_after
                }, "ERROR")

                return {
                    "status": "error",
                    "message": "No rows added to database"
                }

        except Exception as e:
            self._log_debug("STAGE3_PERSIST", asset, {"error": str(e)}, "ERROR")
            return {"status": "error", "message": str(e)}

    def test_query_layer(self, asset: str = "BTC") -> Dict:
        """
        STAGE 4: Verifica que se pueden queryar los datos guardados.
        Returns: {"status": "ok"|"error", "latest_price": float, "observation_count": int}
        """
        self.logger.info(f"🔍 STAGE 4: Query Layer para {asset}...")

        try:
            observations = self.db.get_observations(asset=asset, lookback_hours=24)

            if not observations:
                self._log_debug("STAGE4_QUERY", asset, {
                    "error": "No observations found in last 24h",
                    "count": 0
                }, "ERROR")

                return {
                    "status": "error",
                    "message": "No observations found in last 24h"
                }

            prices = [o.get("value") for o in observations if o.get("observation_type") == "price"]
            if not prices:
                self._log_debug("STAGE4_QUERY", asset, {
                    "error": "No price observations found",
                    "total_obs": len(observations),
                    "obs_types": list(set(o.get("observation_type") for o in observations))
                }, "ERROR")

                return {
                    "status": "error",
                    "message": "No price observations found"
                }

            latest_price = prices[-1]

            self._log_debug("STAGE4_QUERY", asset, {
                "observation_count": len(observations),
                "price_count": len(prices),
                "latest_price": latest_price
            }, "OK")

            return {
                "status": "ok",
                "observation_count": len(observations),
                "price_observations": len(prices),
                "latest_price": latest_price
            }

        except Exception as e:
            self._log_debug("STAGE4_QUERY", asset, {"error": str(e)}, "ERROR")
            return {"status": "error", "message": str(e)}

    def full_diagnostic(self, asset: str = "BTC") -> Dict:
        """
        Ejecuta diagnóstico completo end-to-end.
        Returns: {"overall_status": "ok"|"broken", "stages": {...}}
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔬 FULL DIAGNOSTIC START: {asset}")
        self.logger.info(f"{'='*60}\n")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "asset": asset,
            "stages": {}
        }

        self.logger.info("\n[1/4] Testing Binance fetch...")
        stage1 = self.test_binance_fetch(asset)
        results["stages"]["fetch"] = stage1

        if stage1["status"] != "ok":
            self.logger.error("❌ FETCH FAILED - Pipeline broken")
            results["overall_status"] = "broken"
            results["broken_at"] = "fetch"
            return results

        self.logger.info("\n[2/4] Testing parsing...")
        stage2 = self.test_parsing(asset)
        results["stages"]["parsing"] = stage2

        if stage2["status"] != "ok":
            self.logger.error("❌ PARSING FAILED - Pipeline broken")
            results["overall_status"] = "broken"
            results["broken_at"] = "parsing"
            return results

        self.logger.info("\n[3/4] Testing persistence...")
        stage3 = self.test_persistence(asset)
        results["stages"]["persistence"] = stage3

        if stage3["status"] != "ok":
            self.logger.error("❌ PERSISTENCE FAILED - Pipeline broken")
            results["overall_status"] = "broken"
            results["broken_at"] = "persistence"
            return results

        self.logger.info("\n[4/4] Testing query layer...")
        stage4 = self.test_query_layer(asset)
        results["stages"]["query"] = stage4

        if stage4["status"] != "ok":
            self.logger.error("❌ QUERY FAILED - Pipeline broken")
            results["overall_status"] = "broken"
            results["broken_at"] = "query"
            return results

        self.logger.info(f"\n✅ ALL STAGES PASSED FOR {asset}")
        results["overall_status"] = "ok"

        self.logger.info(f"{'='*60}")
        self.logger.info(f"✅ DIAGNOSTIC COMPLETE")
        self.logger.info(f"{'='*60}\n")

        return results

    def get_provider_status(self) -> Dict:
        """
        Retorna status de cada proveedor:
        - Binance API: last fetch timestamp, error count
        - SQLite: DB size, observation count
        - Scheduler: running status
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "binance": {
                "status": "unknown",
                "last_fetch": None,
                "error_count": 0
            },
            "database": {
                "status": "ok",
                "btc_observations_24h": self.db.count_observations("BTC", 24),
                "eth_observations_24h": self.db.count_observations("ETH", 24),
            },
            "scheduler": {
                "status": "unknown"
            }
        }

    def get_debug_summary(self) -> str:
        """Retorna un resumen amigable para Telegram."""
        status = self.get_provider_status()
        btc_count = status["database"]["btc_observations_24h"]
        eth_count = status["database"]["eth_observations_24h"]

        summary = f"""
🔍 **DEBUG SUMMARY**

📊 **Database Status:**
  • BTC observations (24h): {btc_count}
  • ETH observations (24h): {eth_count}

⚙️ **Scheduler:**
  • Status: Unknown (set by orchestrator)

🚀 **Next Step:**
  Send: `/debug btc` for full pipeline test
        """

        return summary
