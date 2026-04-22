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

    def __init__(self, db, logger):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger

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

            # Obtener contexto del mercado para Claude
            try:
                context_data = self.market_state.get_market_context()
                if "error" not in context_data:
                    market_context = (
                        f"Contexto actual del mercado:\n"
                        f"- BTC: ${context_data.get('btc', {}).get('price', 0):,.0f}\n"
                        f"- ETH: ${context_data.get('eth', {}).get('price', 0):,.0f}\n"
                        f"- Volatilidad: {context_data.get('overall_volatility', 'UNKNOWN')}"
                    )
                else:
                    market_context = ""
            except:
                market_context = ""

            # Generar respuesta con Claude API
            response = self.claude_handler.generate_response(message, market_context)

            # Guardar en DB
            self._save_dialogue(message, response, user_id)

            self.logger.info(f"🤖 Respuesta Claude: {response[:80]}...")
            return response

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

