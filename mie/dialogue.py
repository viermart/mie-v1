"""
DialogueHandler V2 para MIE
Maneja conversaciones con usuarios.
Integra: Intent Parser + Market State Engine + Response Builder
Memoria de diálogos para learning.
"""

import json
from datetime import datetime
from typing import Tuple, Optional
from .intent_parser import IntentParser, Intent
from .market_state import MarketStateEngine
from .response_builder import ResponseBuilder


class DialogueHandler:
    """
    Maneja diálogos bidireccionales con usuarios vía Telegram.
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
        self.intent_parser = IntentParser()
        self.market_state = MarketStateEngine(db)
        self.response_builder = ResponseBuilder(db, self.market_state)

    def handle_message(self, message: str, user_id: str = "unknown") -> str:
        """
        Procesa un mensaje de usuario end-to-end:
        1. Parsea intent
        2. Construye respuesta
        3. Guarda en memoria

        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (Telegram)

        Returns:
            Respuesta para enviar
        """
        try:
            # Parsear intent
            intent, param = self.intent_parser.parse(message)

            self.logger.info(
                f"💬 Intent detectado: {intent.value} (param={param}) de {user_id}"
            )

            # Construir respuesta
            response = self.response_builder.build_response(intent, param)

            # Guardar en memoria
            self._save_dialogue(message, response, intent, param)

            return response

        except Exception as e:
            self.logger.error(f"Error en handle_message: {e}")
            return f"❌ Error: {str(e)}"

    def _save_dialogue(self, user_message: str, mie_response: str,
                       intent: Intent, param: Optional[str]) -> None:
        """Guarda diálogo en la base de datos."""
        try:
            context = f"intent={intent.value}"
            if param:
                context += f",param={param}"

            self.db.add_dialogue(
                user_message=user_message,
                mie_response=mie_response,
                context=context
            )
            self.logger.info(f"✅ Diálogo guardado")
        except Exception as e:
            self.logger.error(f"Error guardando diálogo: {e}")

    # ===== COMPATIBILIDAD CON CÓDIGO ANTIGUO =====

    def classify_query(self, message: str) -> Tuple:
        """Mantener compatibilidad con orquestador antiguo."""
        intent, param = self.intent_parser.parse(message)
        return (intent, param)

    def handle_feedback(self, intent: Intent, message: str, user_id: str) -> str:
        """Procesa feedback del usuario."""
        try:
            self.db.add_user_feedback(
                feedback_type=intent.value,
                context=message
            )

            if intent == Intent.FEEDBACK_POSITIVE:
                return "✅ Gracias por el feedback positivo."
            elif intent == Intent.FEEDBACK_NEGATIVE:
                return "📝 Anotado. Revisaré mis criterios."
            elif intent == Intent.FEEDBACK_FOCUS:
                return "🎯 Cambio de prioridades anotado."
            elif intent == Intent.FEEDBACK_TIMEFRAME:
                return "⏱️ Cambio de timeframe anotado."
            else:
                return "📝 Feedback registrado."

        except Exception as e:
            self.logger.error(f"Error en handle_feedback: {e}")
            return f"❌ Error procesando feedback: {str(e)}"
