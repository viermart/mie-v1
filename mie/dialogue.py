"""
DialogueHandler para MIE V1
Maneja conversaciones REALES con Claude API.
MIE ahora es una IA verdadera, no un bot.
"""

import os
from datetime import datetime
from typing import Optional
from .claude_ai_handler import ClaudeAIHandler
from .market_state import MarketStateEngine


class DialogueHandler:
    """
    Maneja diálogos bidireccionales con usuarios vía Telegram.
    Usa Claude API real para conversaciones inteligentes.
    """

    def __init__(self, db, logger, cache=None):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
            cache: MIEStateCache instance (optional)
        """
        self.db = db
        self.logger = logger
        self.cache = cache

        # Obtener API key de environment - con debugging
        api_key = os.getenv("ANTHROPIC_API_KEY")

        # DEBUG: Mostrar si está configurada
        if api_key:
            self.logger.info(f"✅ ANTHROPIC_API_KEY encontrada (longitud: {len(api_key)})")
        else:
            self.logger.error("❌ ANTHROPIC_API_KEY NO ENCONTRADA en environment")
            self.logger.error(f"Variables disponibles: {list(os.environ.keys())[:5]}...")

        if not api_key:
            self.logger.warning("⚠️ ANTHROPIC_API_KEY no configurada - MIE usará respuestas fallback")
            self.claude_handler = None
        else:
            self.logger.info("✅ Usando Claude API para conversaciones reales")
            try:
                self.claude_handler = ClaudeAIHandler(api_key, db, logger)
            except Exception as e:
                self.logger.error(f"❌ Error inicializando ClaudeAIHandler: {e}")
                self.claude_handler = None

        # Inicializar market state para contexto
        self.market_state = MarketStateEngine(db)

    def handle_message(self, message: str, user_id: str = "unknown") -> str:
        """
        Procesa un mensaje de usuario y genera respuesta con Claude API.

        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (Telegram)

        Returns:
            Respuesta generada por Claude
        """
        try:
            self.logger.info(f"💬 Mensaje de {user_id}: {message}")

            if not self.claude_handler:
                self.logger.error("Claude handler no disponible")
                return "No tengo Claude API configurada. Disculpa."

            # Obtener contexto del mercado para Claude - SIEMPRE usar datos reales de cache/DB
            market_context = ""
            try:
                if self.cache and self.cache.last_btc_obs and self.cache.last_eth_obs:
                    # Usar cache con datos actualizados
                    btc_price = self.cache.last_btc_obs.get('value', 0)
                    eth_price = self.cache.last_eth_obs.get('value', 0)
                    btc_momentum = self.cache.momentum_4h.get('BTC', 'UNKNOWN')
                    eth_momentum = self.cache.momentum_4h.get('ETH', 'UNKNOWN')
                    btc_trend = self.cache.trend.get('BTC', 'UNKNOWN')
                    eth_trend = self.cache.trend.get('ETH', 'UNKNOWN')

                    market_context = (
                        f"CONTEXTO ACTUAL DEL MERCADO (datos reales de BD):\n"
                        f"- BTC: ${btc_price:,.2f} | Momentum 4h: {btc_momentum} | Trend: {btc_trend}\n"
                        f"- ETH: ${eth_price:,.2f} | Momentum 4h: {eth_momentum} | Trend: {eth_trend}\n"
                        f"- Actualizado: {self.cache.last_update}\n"
                        f"\nIMPORTANTE: Usa SOLO estos datos para análisis. No inventes otros números."
                    )
                else:
                    # Fallback a market_state si cache no está disponible
                    context_data = self.market_state.get_market_context()
                    if "error" not in context_data:
                        market_context = (
                            f"CONTEXTO ACTUAL DEL MERCADO (datos de BD):\n"
                            f"- BTC: ${context_data.get('btc', {}).get('price', 0):,.0f}\n"
                            f"- ETH: ${context_data.get('eth', {}).get('price', 0):,.0f}\n"
                            f"- Volatilidad: {context_data.get('overall_volatility', 'UNKNOWN')}\n"
                            f"\nIMPORTANTE: Usa SOLO estos datos. No inventes números."
                        )
            except Exception as e:
                self.logger.warning(f"Error obteniendo contexto: {e}")
                market_context = "No tengo contexto de mercado disponible ahora."

            # Generar respuesta con Claude API
            response = self.claude_handler.generate_response(message, market_context)

            # Guardar en DB
            self._save_dialogue(message, response, user_id)

            self.logger.info(f"🤖 Respuesta Claude: {response[:80]}...")
            # Add production marker for validation
            return f"[MIE-SINGLE-RUNTIME-CHECK] {response}"

        except Exception as e:
            self.logger.error(f"Error en handle_message: {e}", exc_info=True)
            return "Disculpa, ocurrió un error. Intenta de nuevo."

    def _save_dialogue(self, user_message: str, response: str, user_id: str) -> None:
        """Guarda la conversación en la DB."""
        try:
            self.db.add_dialogue(
                user_message=user_message,
                mie_response=response,
                context=f"user_id={user_id},timestamp={datetime.utcnow().isoformat()}"
            )
        except Exception as e:
            self.logger.error(f"Error guardando diálogo: {e}")

