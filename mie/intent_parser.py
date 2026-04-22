"""
Intent Parser para MIE
Mapea mensajes de usuario a intents específicos con alta precisión.
Minimiza "unknown" con patrones flexibles pero precisos.
"""

import re
from enum import Enum
from typing import Tuple, Optional, Dict, List


class Intent(Enum):
    """Intents que MIE entiende."""
    # Queries de estado
    STATUS = "status"                          # "status", "como vas", "vivo", "funcionas"
    MARKET_TODAY = "market_today"              # "como ves el mercado", "mercado hoy", "que pasa"
    WHAT_WATCHING = "what_watching"            # "que estas mirando", "que ves", "observaciones"
    WHAT_LEARNED = "what_learned"              # "que aprendiste", "insights", "que encontraste"
    ACTIVE_HYPOTHESES = "active_hypotheses"    # "hipotesis", "investigaciones", "tests"

    # Queries de assets
    ASSET_BTC = "asset_btc"                    # "btc", "bitcoin", "como ves btc"
    ASSET_ETH = "asset_eth"                    # "eth", "ethereum", "como ves eth"
    ASSET_GENERAL = "asset_general"            # Asset query genérico

    # Feedback
    FEEDBACK_POSITIVE = "feedback_positive"    # "bien", "util", "acertaste"
    FEEDBACK_NEGATIVE = "feedback_negative"    # "mal", "no sirve", "equivocado"
    FEEDBACK_FOCUS = "feedback_focus"          # "enfocate en X"
    FEEDBACK_TIMEFRAME = "feedback_timeframe"  # "mas diario", "menos intradia"

    # Sociales
    GREETING = "greeting"                      # "hola", "que tal", "podes hablar"
    HELP = "help"                              # "ayuda", "help", "que puedo hacer"

    # Fallback
    UNKNOWN = "unknown"


class IntentParser:
    """Parser de intents con patrones ordenados por especificidad."""

    def __init__(self):
        """Inicializa patrones de reconocimiento."""
        # Orden importa: más específicos primero
        self.patterns: Dict[Intent, List[str]] = {
            # ===== GREETINGS =====
            Intent.GREETING: [
                r"^hola$",
                r"^hola\s+",
                r"que tal",
                r"buenos dias",
                r"buenas noches",
                r"buenas tardes",
                r"podes hablar",
                r"puedes hablar",
                r"sos vos",
                r"eres tu",
                r"quien eres",
            ],

            # ===== STATUS/HEALTH =====
            Intent.STATUS: [
                r"^status$",
                r"^status\?",
                r"^status\s*$",
                r"como vas",
                r"como estoy",
                r"estoy vivo",
                r"funcionas",
                r"funciono",
                r"todo bien",
                r"everything ok",
                r"estoy activo",
                r"sos vivo",
            ],

            # ===== MARKET STATE TODAY =====
            Intent.MARKET_TODAY: [
                r"como ves el mercado",
                r"como ve el mercado",
                r"mercado hoy",
                r"estado del mercado",
                r"que tal el mercado",
                r"que pasa en el mercado",
                r"overview",
                r"resumen del mercado",
                r"context actual",
                r"contexto actual",
                r"hoy",  # solo "hoy" = mercado hoy
            ],

            # ===== WHAT WATCHING =====
            Intent.WHAT_WATCHING: [
                r"que estoy mirando",
                r"que estas mirando",
                r"que ves",
                r"que observas",
                r"que observaciones",
                r"en que te enfocas",
                r"monitoring",
                r"watching",
                r"observando",
            ],

            # ===== WHAT LEARNED =====
            Intent.WHAT_LEARNED: [
                r"que aprendiste",
                r"que descubriste",
                r"insights",
                r"hallazgos",
                r"conclusiones",
                r"que encontraste",
                r"aprendizajes",
                r"learning",
            ],

            # ===== ACTIVE HYPOTHESES =====
            Intent.ACTIVE_HYPOTHESES: [
                r"hipotesis activas",
                r"hipótesis activas",
                r"hipotesis",
                r"hipótesis",
                r"que hipotesis",
                r"investigations",
                r"investigaciones",
                r"que estoy testando",
                r"tests en curso",
            ],

            # ===== BTC SPECIFIC =====
            Intent.ASSET_BTC: [
                r"^btc$",
                r"^btc\?",
                r"^btc\s*$",
                r"^bitcoin$",
                r"como ves btc",
                r"como ve btc",
                r"que tal btc",
                r"estado btc",
                r"btc ahora",
                r"btc hoy",
                r"btc status",
            ],

            # ===== ETH SPECIFIC =====
            Intent.ASSET_ETH: [
                r"^eth$",
                r"^eth\?",
                r"^eth\s*$",
                r"^ethereum$",
                r"como ves eth",
                r"como ve eth",
                r"que tal eth",
                r"estado eth",
                r"eth ahora",
                r"eth hoy",
                r"eth status",
            ],

            # ===== FEEDBACK POSITIVE =====
            Intent.FEEDBACK_POSITIVE: [
                r"esto fue util",
                r"esto fue útil",
                r"^bien$",
                r"muy bien",
                r"bien hecho",
                r"exacto",
                r"acertaste",
                r"buen analisis",
                r"buen análisis",
                r"good",
                r"useful",
                r"nice",
                r"gracias",
                r"thanks",
            ],

            # ===== FEEDBACK NEGATIVE =====
            Intent.FEEDBACK_NEGATIVE: [
                r"esto fue ruido",
                r"esto fue noise",
                r"^mal$",
                r"no sirve",
                r"equivocado",
                r"equivocada",
                r"fallaste",
                r"bad",
                r"wrong",
                r"incorrect",
                r"mistake",
            ],

            # ===== FEEDBACK FOCUS =====
            Intent.FEEDBACK_FOCUS: [
                r"enfocate.*(?:en|mas en)\s+(\w+)",
                r"enfócate.*(?:en|mas en)\s+(\w+)",
                r"mas.*en\s+(\w+)",
                r"más.*en\s+(\w+)",
                r"menos.*en\s+(\w+)",
                r"prioriza\s+(\w+)",
            ],

            # ===== FEEDBACK TIMEFRAME =====
            Intent.FEEDBACK_TIMEFRAME: [
                r"menos intradia",
                r"menos intraday",
                r"mas diario",
                r"más diario",
                r"mas semanal",
                r"más semanal",
                r"enfocate en daily",
                r"enfócate en daily",
            ],

            # ===== HELP =====
            Intent.HELP: [
                r"^help$",
                r"^ayuda$",
                r"que puedo hacer",
                r"como funcionas",
                r"how to use",
                r"comandos",
            ],
        }

    def parse(self, message: str) -> Tuple[Intent, Optional[str]]:
        """
        Parsea un mensaje de usuario y retorna (Intent, param).

        Args:
            message: Mensaje del usuario

        Returns:
            (Intent, param): Intent detectado + parámetro opcional
        """
        message_lower = message.lower().strip()

        # Orden de chequeo: más específicos primero
        priority_order = [
            Intent.STATUS,
            Intent.ASSET_BTC,
            Intent.ASSET_ETH,
            Intent.MARKET_TODAY,
            Intent.WHAT_WATCHING,
            Intent.WHAT_LEARNED,
            Intent.ACTIVE_HYPOTHESES,
            Intent.GREETING,
            Intent.HELP,
            Intent.FEEDBACK_POSITIVE,
            Intent.FEEDBACK_NEGATIVE,
            Intent.FEEDBACK_FOCUS,
            Intent.FEEDBACK_TIMEFRAME,
        ]

        for intent in priority_order:
            patterns = self.patterns[intent]
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    param = None

                    # Extraer parámetro si existe
                    if intent == Intent.FEEDBACK_FOCUS and match.groups():
                        param = match.group(1).upper()

                    return (intent, param)

        return (Intent.UNKNOWN, None)

    def get_intent_description(self, intent: Intent) -> str:
        """Retorna descripción legible del intent."""
        descriptions = {
            Intent.STATUS: "estado del sistema",
            Intent.MARKET_TODAY: "estado del mercado",
            Intent.WHAT_WATCHING: "observaciones actuales",
            Intent.WHAT_LEARNED: "aprendizajes",
            Intent.ACTIVE_HYPOTHESES: "hipótesis en testing",
            Intent.ASSET_BTC: "info de BTC",
            Intent.ASSET_ETH: "info de ETH",
            Intent.ASSET_GENERAL: "info de asset",
            Intent.GREETING: "saludo",
            Intent.HELP: "ayuda",
            Intent.FEEDBACK_POSITIVE: "feedback positivo",
            Intent.FEEDBACK_NEGATIVE: "feedback negativo",
            Intent.FEEDBACK_FOCUS: "cambio de prioridades",
            Intent.FEEDBACK_TIMEFRAME: "cambio de timeframe",
            Intent.UNKNOWN: "desconocido",
        }
        return descriptions.get(intent, "desconocido")
