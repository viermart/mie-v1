"""
MIE Command Handler - FASE 1 Minimal Commands
Handles: /status, /btc, /eth, /market, /what_are_you_seeing
Only uses data that exists in DB. No improvisation.
"""

import logging
from typing import Optional, Dict
from datetime import datetime


class CommandHandler:
    """Process MIE commands and return real data from DB."""

    def __init__(self, db, logger: Optional[logging.Logger] = None):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger or logging.getLogger("CommandHandler")

    def handle_command(self, message: str, user_id: str = "unknown") -> Optional[str]:
        """
        Process commands if message starts with /.
        Return None if not a command - let DialogueHandler handle it.
        """
        message = message.strip()
        if not message.startswith("/"):
            return None

        parts = message.split()
        command = parts[0].lower()

        if command == "/status":
            return self._cmd_status()
        elif command == "/btc":
            return self._cmd_asset("BTC")
        elif command == "/eth":
            return self._cmd_asset("ETH")
        elif command == "/market":
            return self._cmd_market()
        elif command == "/what_are_you_seeing":
            return self._cmd_what_seeing()
        elif command == "/diagnostic":
            return self._cmd_diagnostic()
        else:
            return f"Comando desconocido: {command}\nDisponibles: /status, /btc, /eth, /market, /what_are_you_seeing, /diagnostic"

    def _cmd_status(self) -> str:
        """Return system status - do we have recent data?"""
        try:
            btc_obs = self.db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
            eth_obs = self.db.get_observations(asset="ETH", lookback_hours=1, observation_type="price")

            if not btc_obs or not eth_obs:
                return "⏳ Todavía no tengo datos recientes. Esperando primer ciclo de ingestión..."

            btc_count = self.db.get_observation_count(asset="BTC")
            eth_count = self.db.get_observation_count(asset="ETH")

            return (
                f"✅ MIE está activa\n"
                f"📊 BTC: {btc_count} observaciones\n"
                f"📊 ETH: {eth_count} observaciones\n"
                f"🔄 Ciclo: cada 5 minutos\n"
                f"📌 Último update: ahora\n"
                f"\nUsa /btc, /eth, /market, o /what_are_you_seeing"
            )
        except Exception as e:
            self.logger.error(f"Error in /status: {e}")
            return f"Error en status: {e}"

    def _cmd_asset(self, asset: str) -> str:
        """Show current asset price and recent changes."""
        try:
            # Get latest price observation
            obs = self.db.get_observations(
                asset=asset,
                lookback_hours=24,
                observation_type="price"
            )

            if not obs:
                return f"📭 Sin datos para {asset} todavía."

            # Get latest
            latest = obs[-1]
            current_price = latest["value"]

            # Calculate changes
            if len(obs) >= 2:
                price_24h_ago = obs[0]["value"]
                change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
            else:
                change_24h = 0.0

            return (
                f"💰 {asset}\n"
                f"📈 Price: ${current_price:,.2f}\n"
                f"📊 Change 24h: {change_24h:+.2f}%\n"
                f"⏰ Updated: {latest['timestamp']}\n"
                f"📍 Source: {latest['source']}"
            )
        except Exception as e:
            self.logger.error(f"Error in /{asset.lower()}: {e}")
            return f"Error obteniendo datos de {asset}: {e}"

    def _cmd_market(self) -> str:
        """Market overview - BTC, ETH, relative strength."""
        try:
            btc_obs = self.db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
            eth_obs = self.db.get_observations(asset="ETH", lookback_hours=24, observation_type="price")

            if not btc_obs or not eth_obs:
                return "📭 Todavía no hay suficiente historial de mercado."

            btc_latest = btc_obs[-1]["value"]
            eth_latest = eth_obs[-1]["value"]

            btc_24h_ago = btc_obs[0]["value"]
            eth_24h_ago = eth_obs[0]["value"]

            btc_change = ((btc_latest - btc_24h_ago) / btc_24h_ago) * 100
            eth_change = ((eth_latest - eth_24h_ago) / eth_24h_ago) * 100

            # ETH relative strength vs BTC
            relative_strength = eth_change - btc_change

            return (
                f"🌍 MARKET SNAPSHOT\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"💰 BTC: ${btc_latest:,.0f} ({btc_change:+.2f}%)\n"
                f"💰 ETH: ${eth_latest:,.0f} ({eth_change:+.2f}%)\n"
                f"📊 ETH vs BTC: {relative_strength:+.2f}%\n"
                f"📌 Data points: {len(btc_obs)} BTC, {len(eth_obs)} ETH"
            )
        except Exception as e:
            self.logger.error(f"Error in /market: {e}")
            return f"Error obteniendo mercado: {e}"

    def _cmd_what_seeing(self) -> str:
        """What is MIE seeing right now?"""
        try:
            btc_obs = self.db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
            eth_obs = self.db.get_observations(asset="ETH", lookback_hours=1, observation_type="price")

            if not btc_obs:
                return "👀 Todavía no veo datos de BTC."
            if not eth_obs:
                return "👀 Todavía no veo datos de ETH."

            btc_latest = btc_obs[-1]
            eth_latest = eth_obs[-1]

            return (
                f"👁️  WHAT I'M SEEING NOW\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"BTC: ${btc_latest['value']:,.0f}\n"
                f"   source: {btc_latest['source']}\n"
                f"   timestamp: {btc_latest['timestamp']}\n"
                f"   context: {btc_latest['context'] or 'no context'}\n\n"
                f"ETH: ${eth_latest['value']:,.0f}\n"
                f"   source: {eth_latest['source']}\n"
                f"   timestamp: {eth_latest['timestamp']}\n"
                f"   context: {eth_latest['context'] or 'no context'}\n"
                f"\n✅ Datos reales de DB, no inventados."
            )
        except Exception as e:
            self.logger.error(f"Error in /what_are_you_seeing: {e}")
            return f"Error: {e}"

    def _cmd_diagnostic(self) -> str:
        """Deployment diagnostic - check if code and data are in sync."""
        try:
            btc_count = self.db.get_observation_count(asset="BTC")
            eth_count = self.db.get_observation_count(asset="ETH")
            btc_recent = self.db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
            eth_recent = self.db.get_observations(asset="ETH", lookback_hours=1, observation_type="price")

            diagnosis = "🔍 DIAGNOSTIC REPORT\n"
            diagnosis += "━━━━━━━━━━━━━━━━━━\n"
            diagnosis += f"✅ Code version: 20260422-BINANCE-FIX\n"
            diagnosis += f"📊 Total observations: BTC={btc_count}, ETH={eth_count}\n"
            diagnosis += f"📊 Recent (< 1h): BTC={len(btc_recent or [])}, ETH={len(eth_recent or [])}\n"

            if btc_count == 0:
                diagnosis += "\n❌ ISSUE: No observations at all - fast_loop never ran"
            elif not btc_recent:
                diagnosis += "\n⚠️  ISSUE: Data exists but all older than 1h - fast_loop not running regularly"
            elif btc_recent and btc_recent[-1].get('value', 0) == 0:
                diagnosis += "\n⚠️  ISSUE: Recent data shows $0 - Binance fetch failing"
            else:
                diagnosis += "\n✅ STATUS: Everything OK - data flowing"
                if btc_recent and btc_recent[-1]:
                    latest_btc = btc_recent[-1]
                    diagnosis += f"\n  Latest BTC: ${latest_btc.get('value', 0):,.2f}"

            return diagnosis

        except Exception as e:
            self.logger.error(f"Error in /diagnostic: {e}")
            return f"Error en diagnostic: {e}"
