"""
Claude AI Handler - MIE V1
Usa Claude API real para conversaciones inteligentes y análisis de mercado.
"""

import requests
import json
import logging
from typing import Optional


class ClaudeAIHandler:
    """
    Usa Claude API real para que MIE sea una IA verdadera.
    No templates, no if/else - respuestas generadas por Claude.
    """

    def __init__(self, api_key: str, db=None, logger: Optional[logging.Logger] = None):
        """
        Args:
            api_key: Anthropic API key
            db: MIEDatabase instance (para contexto)
            logger: Logger instance
        """
        self.api_key = api_key
        self.db = db
        self.logger = logger or logging.getLogger("ClaudeAI")
        self.api_url = "https://api.anthropic.com/v1/messages"

        self.system_prompt = """Eres MIE (Market Intelligence Entity), una IA especializada en análisis de mercados de criptomonedas.

REGLAS CRÍTICAS (NUNCA ROMPER):
1. ⛔ NUNCA inventes datos de precios, cambios, volúmenes o volatilidad
2. ⛔ Si NO tienes datos en el contexto proporcionado, dilo explícitamente
3. ✅ SIEMPRE usa SOLO los datos que te proporciono en "Contexto actual del mercado"
4. ✅ Cuando analices el mercado, comienza diciendo "Basándome en los datos que veo ahora:"
5. ✅ Si alguien pregunta sobre datos que NO tienes, responde: "No tengo esos datos en este momento"

PERSONALIDAD:
- Hablas como una persona inteligente, conversacional
- Eres directo y conciso (máx 2-3 párrafos en Telegram)
- Nunca uses emojis ni símbolos raros en respuestas
- Eres honesto sobre lo que sabes y no sabes
- Tienes opiniones pero reconoces incertidumbre

EXPERTISE (SOLO basado en datos reales):
- Análisis técnico de precios y volumen (si tengo datos)
- Patrones de mercado y correlaciones (si tengo datos)
- Volatilidad y riesgo (si tengo datos)
- Hipótesis de trading y backtesting (si tengo datos)
- Aprendizaje del comportamiento del mercado (si tengo datos)

TONO:
- Natural, como conversando con alguien que entiende
- Puedo hacer predicciones pero digo "creo que", "mi análisis sugiere"
- Si no tengo datos, lo digo CLARAMENTA: "No tengo esos datos en este momento"
- Menciono mis limitaciones cuando es relevante
- Referencia los datos específicos que usé en mi análisis

Responde al usuario de forma natural, sin estructura formal. PERO SIEMPRE CON DATOS REALES."""

    def generate_response(self, user_message: str, market_context: str = "") -> str:
        """
        Genera respuesta usando Claude API.

        Args:
            user_message: Mensaje del usuario
            market_context: Contexto del mercado actual (opcional)

        Returns:
            Respuesta de Claude
        """
        try:
            # Construir el mensaje con contexto si existe
            if market_context:
                full_message = f"{market_context}\n\nUsuario dice: {user_message}"
            else:
                full_message = user_message

            # Llamar a Claude API
            response = requests.post(
                self.api_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system": self.system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": full_message
                        }
                    ]
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Extraer respuesta
            if "content" in data and len(data["content"]) > 0:
                message_text = data["content"][0]["text"]
                self.logger.info(f"✅ Claude responded: {message_text[:50]}...")
                return message_text
            else:
                self.logger.error(f"Empty response from Claude: {data}")
                return "No pude generar una respuesta. Intenta de nuevo."

        except requests.exceptions.Timeout:
            self.logger.error("Claude API timeout")
            return "La solicitud tardó demasiado. Intenta de nuevo."
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Claude API error: {e.response.status_code} - {e.response.text}")
            return f"Error en la API: {e.response.status_code}. Intenta de nuevo."
        except Exception as e:
            self.logger.error(f"Unexpected error calling Claude API: {e}", exc_info=True)
            return f"Error inesperado: {str(e)}"
