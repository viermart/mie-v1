"""
MIE Command Handler - NIVEL 1 Commands
Handles: /status, /btc, /eth, /market, /what_are_you_seeing, /alerts, /diagnostic
Only uses data that exists in DB. No improvisation.
Uses state_cache for fast responses.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime


class CommandHandler:
    """Process MIE commands and return real data from DB."""

    def __init__(self, db, logger: Optional[logging.Logger] = None, cache=None):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
            cache: MIEStateCache instance (optional)
        """
        self.db = db
        self.logger = logger or logging.getLogger("CommandHandler")
        self.cache = cache

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
        elif command == "/alerts":
            return self._cmd_alerts()
        elif command == "/diagnostic":
            return self._cmd_diagnostic()
        else:
            return f"❌ Comando desconocido: {command}\n\n📋 Disponibles:\n/status\n/btc\n/eth\n/market\n/alerts\n/what_are_you_seeing\n/diagnostic"

    def _cmd_status(self) -> str:
        """Return system status - do we have recent data?"""
        try:
            btc_obs = self.db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
            eth_obs = self.db.get_observations(asset="ETH", lookback_hours=1, observation_type="price")

            if not btc_obs or not eth_obs:
                return "⏳ Todavía no tengo datos recientes. Esperando primer ciclo de ingestión..."

            btc_count = self.db.get_observation_count(asset="BTC")
            eth_count = self.db.get_observation_count(asset="ETH")

            # Use cache if available for freshness
            if self.cache and self.cache.last_update:
                freshness = self.cache.last_update
            else:
                freshness = "checking..."

            return (
                f"✅ MIE SYSTEM STATUS\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 BTC: {btc_count} observaciones\n"
                f"📊 ETH: {eth_count} observaciones\n"
                f"🔄 Ciclo: cada 5 minutos\n"
                f"🕐 Estado actualizado: {freshness}\n"
                f"\n💡 Usa: /btc, /eth, /market, /alerts, /what_are_you_seeing"
            )
        except Exception as e:
            self.logger.error(f"Error in /status: {e}")
            return f"❌ Error en status: {e}"

    def _cmd_asset(self, asset: str) -> str:
        """Show asset price with momentum + 1h/24h changes."""
        try:
            # Get 24h observations for changes
            obs_24h = self.db.get_observations(
                asset=asset,
                lookback_hours=24,
                observation_type="price"
            )

            # Get 1h observations for 1h change
            obs_1h = self.db.get_observations(
                asset=asset,
                lookback_hours=1,
                observation_type="price"
            )

            if not obs_24h:
                return f"📭 Sin datos para {asset} todavía."

            current_price = obs_24h[-1]["value"]
            timestamp = obs_24h[-1].get("timestamp", "unknown")

            # Calculate changes
            change_24h = 0.0
            if len(obs_24h) >= 2:
                price_24h_ago = obs_24h[0]["value"]
                change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100

            change_1h = 0.0
            if obs_1h and len(obs_1h) >= 2:
                price_1h_ago = obs_1h[0]["value"]
                change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100

            # Get momentum from cache if available
            momentum = "?"
            if self.cache:
                momentum = self.cache.momentum_4h.get(asset, "?")

            trend = "?"
            if self.cache:
                trend = self.cache.trend.get(asset, "?")

            # Determine direction emoji
            dir_24h = "📈" if change_24h > 0 else "📉"
            dir_1h = "📈" if change_1h > 0 else "📉"

            return (
                f"💰 {asset}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Price: ${current_price:,.2f}\n"
                f"\n📊 Changes:\n"
                f"  1h:   {dir_1h} {change_1h:+.2f}%\n"
                f"  24h:  {dir_24h} {change_24h:+.2f}%\n"
                f"\n🎯 Momentum: {momentum}\n"
                f"📈 Trend: {trend}\n"
                f"\n⏰ Last update: {timestamp[-8:]}"
            )
        except Exception as e:
            self.logger.error(f"Error in /{asset.lower()}: {e}")
            return f"❌ Error obteniendo datos de {asset}: {e}"

    def _cmd_market(self) -> str:
        """Market overview - serious summary."""
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

            # Get momentum from cache
            btc_momentum = "?"
            eth_momentum = "?"
            if self.cache:
                btc_momentum = self.cache.momentum_4h.get("BTC", "?")
                eth_momentum = self.cache.momentum_4h.get("ETH", "?")

            # Get volatility
            btc_vol = "?"
            eth_vol = "?"
            if self.cache:
                btc_vol = self.cache.volatility_signal.get("BTC", "?")
                eth_vol = self.cache.volatility_signal.get("ETH", "?")

            btc_dir = "↑" if btc_change > 0 else "↓"
            eth_dir = "↑" if eth_change > 0 else "↓"
            rel_dir = "📊" if relative_strength > 0 else "📊"

            return (
                f"🌍 MARKET SNAPSHOT\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"\n💰 BTC: ${btc_latest:,.0f} {btc_dir} {btc_change:+.2f}% (24h)\n"
                f"   Momentum: {btc_momentum}\n"
                f"   Volatility: {btc_vol}\n"
                f"\n💰 ETH: ${eth_latest:,.0f} {eth_dir} {eth_change:+.2f}% (24h)\n"
                f"   Momentum: {eth_momentum}\n"
                f"   Volatility: {eth_vol}\n"
                f"\n📊 Market Ratio: ETH {('over' if relative_strength > 0 else 'under')}performing by {abs(relative_strength):.2f}%\n"
                f"📌 Data: {len(btc_obs)} BTC, {len(eth_obs)} ETH observations"
            )
        except Exception as e:
            self.logger.error(f"Error in /market: {e}")
            return f"❌ Error obteniendo mercado: {e}"

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
            return f"❌ Error: {e}"

    def _cmd_alerts(self) -> str:
        """Show detected patterns + active alerts (NIVEL 3)."""
        try:
            if not self.cache:
                return "⚠️  Alert system not initialized yet."

            # Get detected patterns
            patterns = self.cache.detected_patterns or []
            alerts = self.cache.active_alerts

            if not patterns and not alerts:
                return (
                    f"🚨 ALERTS & PATTERNS\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ No patterns detected\n"
                    f"✅ No active alerts\n"
                    f"Last scan: {self.cache.last_pattern_scan or 'never'}"
                )

            alert_text = f"🚨 ALERTS & PATTERNS\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Show detected patterns
            if patterns:
                alert_text += "\n🔍 DETECTED PATTERNS:\n"
                for pattern in patterns:
                    asset = pattern.get("asset", "UNKNOWN")
                    ptype = pattern.get("type", "?")

                    if ptype == "momentum_shift":
                        direction = pattern.get("direction", "?")
                        change = pattern.get("change_pct", 0)
                        alert_text += f"  {asset}: Momentum {direction} ({change:+.2f}%)\n"
                    elif ptype == "volatility_spike":
                        ratio = pattern.get("ratio", 0)
                        alert_text += f"  {asset}: Volatility spike ({ratio:.1f}x normal)\n"
                    elif ptype == "breakout":
                        direction = pattern.get("direction", "?")
                        price = pattern.get("current_price", 0)
                        alert_text += f"  {asset}: Breakout {direction} (${price:,.2f})\n"

            # Show manual alerts
            total_alerts = sum(len(v) for v in alerts.values())
            if total_alerts > 0:
                alert_text += "\n⚠️  ACTIVE ALERTS:\n"
                for asset in ["BTC", "ETH"]:
                    if asset in alerts and alerts[asset]:
                        for alert in alerts[asset]:
                            alert_text += f"  {asset}: {alert.get('message', '?')}\n"

            alert_text += f"\n📋 Total patterns: {len(patterns)}, Manual alerts: {total_alerts}\n"
            alert_text += f"🔔 Last scan: {self.cache.last_pattern_scan or 'never'}"
            return alert_text

        except Exception as e:
            self.logger.error(f"Error in /alerts: {e}")
            return f"❌ Error obteniendo alerts: {e}"

    def _cmd_diagnostic(self) -> str:
        """Deployment diagnostic - check if code and data are in sync."""
        try:
            btc_count = self.db.get_observation_count(asset="BTC")
            eth_count = self.db.get_observation_count(asset="ETH")
            btc_recent = self.db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
            eth_recent = self.db.get_observations(asset="ETH", lookback_hours=1, observation_type="price")
            btc_all = self.db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
            eth_all = self.db.get_observations(asset="ETH", lookback_hours=24, observation_type="price")

            diagnosis = "🔍 DIAGNOSTIC REPORT\n"
            diagnosis += "━━━━━━━━━━━━━━━━━━\n"
            diagnosis += f"✅ Code version: 20260422-BINANCE-FIX\n"
            diagnosis += f"📊 Total observations: BTC={btc_count}, ETH={eth_count}\n"
            diagnosis += f"📊 Recent (< 1h): BTC={len(btc_recent or [])}, ETH={len(eth_recent or [])}\n"
            diagnosis += f"📊 Last 24h: BTC={len(btc_all or [])}, ETH={len(eth_all or [])}\n"

            if btc_count == 0:
                diagnosis += "\n❌ ISSUE: No observations at all - fast_loop never ran"
            elif not btc_recent and not btc_all:
                diagnosis += "\n❌ ISSUE: No data at all"
            elif not btc_recent:
                if btc_all and btc_all[-1]:
                    latest = btc_all[-1]
                    diagnosis += f"\n⚠️  ISSUE: Data exists but all older than 1h"
                    diagnosis += f"\n  Last BTC: ${latest.get('value', 0):,.2f} @ {latest.get('timestamp', 'unknown')[-5:]}"
            elif btc_recent and btc_recent[-1].get('value', 0) == 0:
                diagnosis += "\n⚠️  ISSUE: Recent data shows $0 - Binance fetch failing"
            else:
                diagnosis += "\n✅ STATUS: Everything OK - data flowing"
                if btc_recent and btc_recent[-1]:
                    latest_btc = btc_recent[-1]
                    diagnosis += f"\n  Latest BTC: ${latest_btc.get('value', 0):,.2f} @ {latest_btc.get('timestamp', 'unknown')[-5:]}"
                if eth_recent and eth_recent[-1]:
                    latest_eth = eth_recent[-1]
                    diagnosis += f"\n  Latest ETH: ${latest_eth.get('value', 0):,.2f} @ {latest_eth.get('timestamp', 'unknown')[-5:]}"

            return diagnosis

        except Exception as e:
            self.logger.error(f"Error in /diagnostic: {e}")
            return f"❌ Error en diagnostic: {e}"
