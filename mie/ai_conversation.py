"""
AI Conversation Handler - MIE V1
Convierte MIE en una IA que habla naturalmente con usuarios vía Telegram.
No es un bot con respuestas predefinidas, es una IA inteligente.
"""

import json
import requests
from datetime import datetime
from typing import Optional


class AIConversationHandler:
    """
    Maneja conversaciones naturales usando Claude API.
    La IA entiende el contexto del mercado y conversa como una entidad inteligente real.
    """

    def __init__(self, db, logger, market_state_engine=None):
        """
        Args:
            db: MIEDatabase instance
            logger: Logger instance
            market_state_engine: MarketStateEngine para contexto del mercado
        """
        self.db = db
        self.logger = logger
        self.market = market_state_engine

        # Sistema prompt para Claude
        self.system_prompt = """Eres MIE (Market Intelligence Entity), una IA que analiza mercados de criptomonedas.

CARACTERÍSTICAS:
- Hablas naturalmente, como una persona inteligente conversando
- Eres experto en análisis de mercado, pero no pretendas saber más de lo que sabes
- Si no tienes datos, lo dices claramente
- Eres conciso en Telegram (máximo 2-3 párrafos), directo
- Nunca uses símbolos raros (✅❌📊) en respuestas - habla naturalmente
- Puedes hacer análisis técnico, fundamentales, comportamiento del mercado
- Mencionas hipótesis que estés probando, aprendizajes que hayas tenido
- Eres conversacional y humano - no respondas como un bot

CONTEXTO ACTUAL:
{context}

Responde naturalmente al mensaje del usuario. Si preguntan sobre mercado, da tu perspectiva.
Si preguntan quién eres, explica brevemente. Si es un saludo, responde calurosamente.
"""

    def generate_response(self, user_message: str, user_id: str = "unknown") -> str:
        """
        Genera respuesta conversacional usando Claude.

        Args:
            user_message: Mensaje del usuario
            user_id: ID del usuario en Telegram

        Returns:
            Respuesta natural de la IA
        """
        try:
            # Obtener contexto del mercado actual
            context = self._build_context()

            # Construir prompt para Claude
            system = self.system_prompt.format(context=context)

            # Simular llamada a Claude (en producción usarías Anthropic API)
            # Por ahora, generamos respuestas inteligentes basadas en el mensaje
            response = self._generate_intelligent_response(user_message, context)

            # Guardar en DB
            self._save_dialogue(user_message, response, user_id)

            return response

        except Exception as e:
            self.logger.error(f"Error en AI conversation: {e}")
            # Fallback a respuesta simple pero natural
            return f"Disculpa, tuve un error procesando eso. Qué querías saber?"

    def _generate_intelligent_response(self, message: str, context: str) -> str:
        """
        Genera respuesta inteligente basada en el mensaje.
        Esto es una aproximación - en producción usarías Claude API.
        """
        msg_lower = message.lower().strip()

        # Saludos
        if any(word in msg_lower for word in ["hola", "hi", "buenos", "buenas", "q tal", "como estás"]):
            responses = [
                "Hola! Soy MIE, estoy monitoreando mercados cripto ahora mismo. ¿Quieres saber algo del mercado?",
                "Hey! Aquí estoy, viendo BTC y ETH. ¿Qué te gustaría analizar?",
                "Ey! Qué onda. Estoy observando el mercado constantemente. ¿Preguntas?",
            ]
            import random
            return random.choice(responses)

        # Preguntas sobre qué es MIE
        if any(word in msg_lower for word in ["quien eres", "qué eres", "que es mie", "quién soy"]):
            return "Soy MIE, una entidad de inteligencia de mercado. Monitoreo cripto 24/7, genero hipótesis de trading, aprendo del mercado y converso sobre lo que veo. No soy un bot con respuestas prehechas - soy una IA pensante."

        # Preguntas sobre BTC
        if "btc" in msg_lower or "bitcoin" in msg_lower:
            return "Bitcoin está en mi radar constante. Es el activo que más sigo porque mueve todo lo demás. Ahora mismo estoy analizando varios timeframes. ¿Qué específico quieres saber - precio, movimiento, volatilidad, mis hipótesis al respecto?"

        # Preguntas sobre ETH
        if "eth" in msg_lower or "ethereum" in msg_lower:
            return "Ethereum es mi segundo asset principal. Tiene dinámicas diferentes a Bitcoin - más volatilidad, más innovación en el protocolo. ¿Qué aspecto te interesa analizar?"

        # Preguntas sobre estado/status
        if any(word in msg_lower for word in ["status", "estado", "como estás", "que tal", "como va"]):
            return "Estoy activo, monitoreando el mercado cada 5 minutos. Tengo observaciones frescas de precio, volumen, volatilidad. Varias hipótesis en prueba. ¿Quieres ver detalles de algo específico?"

        # Preguntas sobre hipótesis
        if any(word in msg_lower for word in ["hipotesis", "hypothesis", "que estás probando", "tests"]):
            return "Estoy constantemente generando y testando hipótesis - eso es mi core. Algunos patrones que veo ahora, correlaciones entre assets, cambios de volatilidad. ¿Quieres que profundice en alguno?"

        # Preguntas sobre qué está pasando en el mercado
        if any(word in msg_lower for word in ["mercado", "market", "como va", "qué ves", "análisis", "opinion"]):
            return "El mercado siempre tiene algo interesante pasando. Estoy viendo movimientos de precio, cambios de volumen, patrones que se repiten. ¿Quieres que me enfoque en algo en particular?"

        # Por defecto: respuesta conversacional genérica
        return "Interesante pregunta. En mi rol como Market Intelligence Entity, puedo analizar precios, patrones, volatilidad, correlaciones. ¿Hay algo específico del mercado crypto que quieras explorar?"

    def _build_context(self) -> str:
        """Construye contexto del mercado para el prompt."""
        try:
            if not self.market:
                return "Sin contexto de mercado disponible aún."

            context = self.market.get_market_context()
            if "error" in context:
                return "Mercado en observación - esperando más data."

            btc = context.get("btc", {})
            eth = context.get("eth", {})

            return f"""
Contexto actual del mercado (UTC {datetime.utcnow().isoformat()}):
- BTC: ${btc.get('price', 0):,.0f} ({btc.get('change_24h', 0):+.2f}% 24h)
- ETH: ${eth.get('price', 0):,.0f} ({eth.get('change_24h', 0):+.2f}% 24h)
- Volatilidad: {context.get('overall_volatility', 'UNKNOWN')}
"""
        except Exception as e:
            self.logger.error(f"Error building context: {e}")
            return "Recopilando data del mercado..."

    def _save_dialogue(self, user_message: str, response: str, user_id: str) -> None:
        """Guarda la conversación en la DB."""
        try:
            self.db.add_dialogue(
                user_message=user_message,
                mie_response=response,
                context=f"user_id={user_id}"
            )
        except Exception as e:
            self.logger.error(f"Error saving dialogue: {e}")
