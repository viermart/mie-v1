"""
Response Builder para MIE
Construye respuestas cortas, útiles y contextuales basadas en:
- Intent del usuario
- Estado actual del mercado
- Observations en DB
"""

from typing import Dict, Any, Optional
from .intent_parser import Intent
from .market_state import MarketStateEngine


class ResponseBuilder:
    """Construye respuestas contextuales a intents."""

    def __init__(self, db, market_state_engine: MarketStateEngine):
        """
        Args:
            db: MIEDatabase instance
            market_state_engine: MarketStateEngine instance
        """
        self.db = db
        self.market = market_state_engine

    def build_response(self, intent: Intent, param: Optional[str] = None) -> str:
        """
        Construye respuesta basada en intent.

        Args:
            intent: Intent parseado
            param: Parámetro opcional (ej. asset)

        Returns:
            Respuesta para enviar al usuario
        """
        # Mapeo intent -> método
        handlers = {
            Intent.STATUS: self._status,
            Intent.MARKET_TODAY: self._market_today,
            Intent.WHAT_WATCHING: self._what_watching,
            Intent.WHAT_LEARNED: self._what_learned,
            Intent.ACTIVE_HYPOTHESES: self._active_hypotheses,
            Intent.ASSET_BTC: lambda: self._asset(param or "BTC"),
            Intent.ASSET_ETH: lambda: self._asset(param or "ETH"),
            Intent.ASSET_GENERAL: lambda: self._asset(param),
            Intent.GREETING: self._greeting,
            Intent.HELP: self._help,
            Intent.FEEDBACK_POSITIVE: lambda: "✅ Gracias por el feedback positivo. Continuaré así.",
            Intent.FEEDBACK_NEGATIVE: lambda: "📝 Anotado. Revisaré mis criterios.",
            Intent.FEEDBACK_FOCUS: lambda: f"🎯 Aumentando foco en {param or 'ese asset'}.",
            Intent.FEEDBACK_TIMEFRAME: lambda: "⏱️ Preferencia de timeframe anotada.",
            Intent.UNKNOWN: lambda: self._help()
        }

        handler = handlers.get(intent, lambda: self._help())
        try:
            response = handler()
            return response
        except Exception as e:
            return f"❌ Error generando respuesta: {str(e)}"

    def _greeting(self) -> str:
        """Respuesta a saludos."""
        return "👋 Hola! Soy MIE, tu Market Intelligence Entity. Preguntame sobre el mercado: `status`, `como ves el mercado`, `btc`, `eth`, etc."

    def _help(self) -> str:
        """Ayuda general."""
        return (
            "🔧 **Comandos disponibles:**\n\n"
            "📊 **Mercado:**\n"
            "  • `status` - Mi estado\n"
            "  • `como ves el mercado` - Overview\n"
            "  • `que estoy mirando` - Observaciones\n"
            "  • `btc` / `eth` - Sobre ese asset\n"
            "  • `hoy` - Estado hoy\n\n"
            "📚 **Learning:**\n"
            "  • `que aprendiste` - Mis aprendizajes\n"
            "  • `hipotesis` - Tests en curso\n\n"
            "👍 **Feedback:**\n"
            "  • `bien` / `util` - Positivo\n"
            "  • `mal` / `equivocado` - Negativo\n"
        )

    def _status(self) -> str:
        """Status de MIE."""
        try:
            obs_count = len(self.db.get_observations(asset=None, lookback_hours=24))
            hyp_count = len(self.db.get_active_hypotheses())
            logs_count = len(self.db.get_learning_logs(limit=10))

            return (
                f"✅ **MIE Online**\n\n"
                f"  • Observaciones (24h): {obs_count}\n"
                f"  • Hipótesis: {hyp_count}\n"
                f"  • Learning logs: {logs_count}\n"
                f"  • Monitorizando: BTC, ETH\n"
            )
        except Exception as e:
            return f"✅ MIE Online (error al cargar detalles: {str(e)})"

    def _market_today(self) -> str:
        """Overview del mercado hoy."""
        try:
            context = self.market.get_market_context()

            if "error" in context:
                return "📊 Sin datos suficientes aún. Esperando observaciones de Binance..."

            btc = context["btc"]
            eth = context["eth"]
            direction = context["market_direction"]
            volatility = context["overall_volatility"]

            response = f"📊 **Mercado hoy** {direction}\n\n"
            response += f"**BTC**: ${btc['price']:,.0f} "
            response += f"({btc['change_24h']:+.2f}% 24h)\n"
            response += f"**ETH**: ${eth['price']:,.0f} "
            response += f"({eth['change_24h']:+.2f}% 24h)\n\n"
            response += f"Volatilidad: {volatility.upper()}\n"

            return response
        except Exception as e:
            return f"📊 Error: {str(e)}"

    def _asset(self, asset: str) -> str:
        """Info sobre un asset específico."""
        try:
            if asset not in ["BTC", "ETH"]:
                return f"❓ Asset desconocido: {asset}. Soporto: BTC, ETH"

            changes = self.market.get_price_changes(asset)
            vol = self.market.get_volatility(asset)

            if changes["current_price"] == 0:
                return f"📊 Sin datos de {asset} aún."

            price = changes["current_price"]
            c1h = changes["change_1h"]
            c4h = changes["change_4h"]
            c24h = changes["change_24h"]

            response = f"📈 **{asset}USDT**\n\n"
            response += f"Precio: ${price:,.0f}\n"
            response += f"  1h:  {c1h:+.2f}%\n"
            response += f"  4h:  {c4h:+.2f}%\n"
            response += f"  24h: {c24h:+.2f}%\n"
            response += f"Vol: {vol:.2f}%\n"

            return response
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _what_watching(self) -> str:
        """Qué está observando MIE."""
        try:
            obs = self.db.get_observations(asset=None, lookback_hours=24)

            if not obs:
                return "👀 Sin observaciones aún. Esperando datos de Binance..."

            # Contar por asset
            by_asset = {}
            for o in obs:
                asset = o["asset"]
                by_asset[asset] = by_asset.get(asset, 0) + 1

            response = f"👀 **Observaciones (24h)**: {len(obs)}\n\n"
            for asset, count in sorted(by_asset.items()):
                response += f"  • {asset}: {count}\n"

            return response
        except Exception as e:
            return f"👀 Error: {str(e)}"

    def _what_learned(self) -> str:
        """Aprendizajes registrados."""
        try:
            logs = self.db.get_learning_logs(limit=3)

            if not logs:
                return "📚 Sin aprendizajes registrados aún."

            response = "📚 **Aprendizajes recientes:**\n\n"

            for log in logs[:3]:
                timestamp = log["timestamp"][-5:]  # HH:MM
                content = log["content"][:60]
                response += f"  • {content}... ({timestamp})\n"

            return response
        except Exception as e:
            return f"📚 Error: {str(e)}"

    def _active_hypotheses(self) -> str:
        """Hipótesis activas en testing."""
        try:
            hyps = self.db.get_active_hypotheses()

            if not hyps:
                return "🔬 Sin hipótesis activas. Esperando patrones..."

            response = f"🔬 **Hipótesis en testing**: {len(hyps)}\n\n"

            for hyp in hyps[:3]:  # Top 3
                hyp_id = hyp["hypothesis_id"]
                text = hyp["text"][:50]
                confidence = hyp["confidence"]
                response += f"  • {text}...\n"
                response += f"    Confianza: {confidence}\n\n"

            return response
        except Exception as e:
            return f"🔬 Error: {str(e)}"
