"""
DialogueHandler para MIE V1
Maneja conversaciones naturales con usuarios vía Telegram.
MIE es una IA inteligente que conversa, no un bot con respuestas predefinidas.
"""

import json
from datetime import datetime
from typing import Tuple, Optional
from .ai_conversation import AIConversationHandler
from .market_state import MarketStateEngine


class DialogueHandler:
    """
    Maneja diálogos bidireccionales con usuarios vía Telegram.
    Usa AIConversationHandler para conversaciones naturales en lugar de respuestas template.
    """

    def __init__(self, db, logger):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger

        # Inicializar componentes
        self.market_state = MarketStateEngine(db)
        self.ai_handler = AIConversationHandler(db, logger, self.market_state)

    def handle_message(self, message: str, user_id: str = "unknown") -> str:
        """
        Procesa un mensaje de usuario y genera respuesta natural.

        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (Telegram)

        Returns:
            Respuesta natural de la IA
        """
        try:
            self.logger.info(f"💬 Mensaje de {user_id}: {message}")

            # Generar respuesta usando AI (no ResponseBuilder predefinido)
            response = self.ai_handler.generate_response(message, user_id)

            self.logger.info(f"🤖 Respuesta IA: {response[:50]}...")
            return response

        except Exception as e:
            self.logger.error(f"Error en handle_message: {e}", exc_info=True)
            return "Disculpa, ocurrió un error procesando tu mensaje. Intenta de nuevo."

