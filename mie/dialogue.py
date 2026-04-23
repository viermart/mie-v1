"""
DialogueHandler para MIE V1
Maneja conversaciones REALES con Claude API.
MIE ahora es una IA verdadera, no un bot.
Unified: lee del mismo DB que los comandos - una sola fuente de verdad.
"""

import os
from datetime import datetime
from typing import Optional
from .claude_ai_handler import ClaudeAIHandler
from .market_state import MarketStateEngine
from .unified_context import UnifiedContextProvider


class DialogueHandler:
    """
    Maneja diálogos bidireccionales con usuarios vía Telegram.
    Usa Claude API real para conversaciones inteligentes.
    Lee del mismo DB que los comandos - contexto unificado.
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

        # Unified context provider - same source as commands
        self.context_provider = UnifiedContextProvider(db, logger)

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

            # Obtener contexto del mercado - UNIFIED SOURCE
            # Lee del DB directamente, no del cache que puede estar desactualizado
            market_context = ""
            try:
                market_context = self.context_provider.get_dialogue_prompt_context(message)
                if not market_context:
                    market_context = "No hay datos de mercado disponibles."
            except Exception as e:
                self.logger.warning(f"Error obteniendo contexto unificado: {e}")
                market_context = "Error al obtener contexto de mercado."

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

