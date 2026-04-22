import re
import json
from enum import Enum
from datetime import datetime
from typing import Tuple, Dict, Any, Optional


class QueryType(Enum):
    """Tipos de consultas y feedback que MIE puede procesar."""
    MARKET_OVERVIEW = "market_overview"          # "como ves el mercado"
    WHAT_WATCHING = "what_watching"              # "que estas mirando"
    WHAT_LEARNED = "what_learned"                # "que aprendiste"
    ACTIVE_HYPOTHESES = "active_hypotheses"      # "hipotesis activas"
    STATUS = "status"                            # "status", "como vas"
    ASSET_QUERY = "asset_query"                  # "btc", "eth", "como ves btc"
    FEEDBACK_POSITIVE = "feedback_positive"      # "esto fue util", "bien"
    FEEDBACK_NEGATIVE = "feedback_negative"      # "esto fue ruido", "mal"
    FEEDBACK_FOCUS = "feedback_focus"            # "enfocate mas en btc", "menos eth"
    FEEDBACK_TIMEFRAME = "feedback_timeframe"    # "menos intradia", "mas diario"
    UNKNOWN = "unknown"                          # No clasificado


class DialogueHandler:
    """
    Maneja diálogo con usuarios vía Telegram.
    Clasifica queries, genera respuestas contextuales, y procesa feedback.
    """

    def __init__(self, db, logger):
        """
        Args:
            db: MIEDatabase instance para acceso a estado
            logger: Logger instance para logs
        """
        self.db = db
        self.logger = logger

        # Patrones regex para clasificación de queries
        self.query_patterns = {
            QueryType.MARKET_OVERVIEW: [
                r"como ves el mercado",
                r"que tal el mercado",
                r"estado del mercado",
                r"overview",
                r"mercado ahora",
                r"que pasa en el mercado",
            ],
            QueryType.WHAT_WATCHING: [
                r"que estas mirando",
                r"que observas",
                r"en que te enfocas",
                r"que observaciones",
                r"monitoring",
                r"watching",
            ],
            QueryType.WHAT_LEARNED: [
                r"que aprendiste",
                r"que descubriste",
                r"insights",
                r"hallazgos",
                r"conclusiones",
                r"que encontraste",
            ],
            QueryType.ACTIVE_HYPOTHESES: [
                r"hipotesis activas",
                r"hipótesis activas",
                r"que hipotesis",
                r"hypothesis",
                r"investigaciones",
                r"que estoy testando",
            ],
            QueryType.STATUS: [
                r"^status$",
                r"^status\?",
                r"como vas",
                r"estoy vivo",
                r"funciono",
                r"todo bien",
            ],
            QueryType.ASSET_QUERY: [
                r"^btc$",
                r"^eth$",
                r"^bitcoin$",
                r"^ethereum$",
                r"como ves btc",
                r"como ves eth",
                r"status btc",
                r"status eth",
                r"btc ahora",
                r"eth ahora",
            ],
            QueryType.FEEDBACK_POSITIVE: [
                r"esto fue util",
                r"esto fue útil",
                r"bien",
                r"good",
                r"useful",
                r"exacto",
                r"acertaste",
                r"buen analisis",
                r"buen análisis",
            ],
            QueryType.FEEDBACK_NEGATIVE: [
                r"esto fue ruido",
                r"esto fue noise",
                r"mal",
                r"bad",
                r"no sirve",
                r"equivocado",
                r"equivocada",
                r"fallaste",
            ],
            QueryType.FEEDBACK_FOCUS: [
                r"enfocate mas en (\w+)",
                r"enfócate mas en (\w+)",
                r"menos (\w+)",
                r"mas (\w+)",
                r"más (\w+)",
                r"prioriza (\w+)",
            ],
            QueryType.FEEDBACK_TIMEFRAME: [
                r"menos intradia",
                r"menos intraday",
                r"mas diario",
                r"más diario",
                r"mas semanal",
                r"más semanal",
                r"enfocate en daily",
                r"enfócate en daily",
            ],
        }

    def classify_query(self, message: str) -> Tuple[QueryType, Optional[str]]:
        """
        Clasifica un mensaje de usuario.

        Args:
            message: Mensaje del usuario

        Returns:
            (QueryType, param): tipo de query + parámetro (ej. asset para asset_query)
        """
        message_lower = message.lower().strip()

        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    # Extraer parámetro si existe (ej. asset en feedback_focus)
                    param = None
                    if query_type == QueryType.ASSET_QUERY:
                        # Extraer asset (btc, eth, etc)
                        asset_match = re.search(r"(btc|eth|bitcoin|ethereum)", message_lower)
                        if asset_match:
                            asset = asset_match.group(1)
                            param = "BTC" if asset in ["btc", "bitcoin"] else "ETH"
                    elif query_type == QueryType.FEEDBACK_FOCUS:
                        # Extraer asset a priorizar
                        focus_match = re.search(r"mas en (\w+)|más en (\w+)|en (\w+)", message_lower)
                        if focus_match:
                            param = focus_match.group(1) or focus_match.group(2) or focus_match.group(3)

                    return (query_type, param)

        return (QueryType.UNKNOWN, None)

    def _market_overview(self) -> str:
        """Genera resumen del estado del mercado hoy."""
        try:
            # Obtener observaciones de últimas 24h
            obs = self.db.get_observations(asset=None, lookback_hours=24, observation_type=None)

            # Agrupar por asset
            by_asset = {}
            for o in obs:
                asset = o["asset"]
                if asset not in by_asset:
                    by_asset[asset] = []
                by_asset[asset].append(o)

            if not by_asset:
                return "📊 Sin observaciones en las últimas 24h. Esperando datos..."

            response = "📊 **Overview del mercado (últimas 24h):**\n\n"

            for asset, observations in by_asset.items():
                prices = [o["value"] for o in observations if o["observation_type"] == "price"]
                if prices:
                    current = prices[-1]
                    min_price = min(prices)
                    max_price = max(prices)
                    change_pct = ((current - prices[0]) / prices[0] * 100) if prices[0] else 0

                    response += f"**{asset}USDT**\n"
                    response += f"  Precio actual: ${current:,.2f}\n"
                    response += f"  Rango: ${min_price:,.2f} - ${max_price:,.2f}\n"
                    response += f"  Cambio 24h: {change_pct:+.2f}%\n"
                    response += f"  Observaciones: {len(prices)}\n\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en market_overview: {e}")
            return f"❌ Error generando overview: {str(e)}"

    def _what_watching(self) -> str:
        """Explica qué está observando MIE."""
        try:
            obs = self.db.get_observations(asset=None, lookback_hours=24, observation_type=None)

            if not obs:
                return "👀 Sin observaciones aún. Esperando datos de Binance..."

            # Contar observaciones por tipo
            by_type = {}
            by_asset = {}
            for o in obs:
                obs_type = o["observation_type"]
                asset = o["asset"]
                by_type[obs_type] = by_type.get(obs_type, 0) + 1
                by_asset[asset] = by_asset.get(asset, 0) + 1

            response = "👀 **Estoy observando (últimas 24h):**\n\n"
            response += f"**Total de observaciones**: {len(obs)}\n\n"
            response += "**Por tipo:**\n"
            for obs_type, count in sorted(by_type.items()):
                response += f"  • {obs_type}: {count}\n"

            response += "\n**Por asset:**\n"
            for asset, count in sorted(by_asset.items()):
                response += f"  • {asset}: {count}\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en what_watching: {e}")
            return f"❌ Error: {str(e)}"

    def _what_learned(self) -> str:
        """Muestra aprendizajes de learning logs."""
        try:
            logs = self.db.get_learning_logs(limit=5)

            if not logs:
                return "📚 Aún sin learning logs. Esperando reflexiones..."

            response = "📚 **Aprendizajes registrados:**\n\n"

            for log in logs:
                log_type = log["log_type"].upper()
                timestamp = log["timestamp"]
                try:
                    content = json.loads(log["content"])
                    summary = content.get("summary", "Sin resumen")
                    response += f"**{log_type}** ({timestamp})\n"
                    response += f"  {summary}\n\n"
                except:
                    response += f"**{log_type}** ({timestamp})\n"
                    response += f"  {log['content'][:100]}...\n\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en what_learned: {e}")
            return f"❌ Error: {str(e)}"

    def _active_hypotheses(self) -> str:
        """Lista hipótesis activas en testing."""
        try:
            hypotheses = self.db.get_active_hypotheses()

            if not hypotheses:
                return "🔬 Sin hipótesis activas. Esperando patrones..."

            response = "🔬 **Hipótesis activas:**\n\n"

            for hyp in hypotheses:
                hyp_id = hyp["hypothesis_id"]
                text = hyp["text"]
                status = hyp["status"]
                confidence = hyp["confidence"]
                obs_count = hyp["observation_count"]

                response += f"**{hyp_id}**\n"
                response += f"  Texto: {text}\n"
                response += f"  Status: {status}\n"
                response += f"  Confianza: {confidence}\n"
                response += f"  Observaciones: {obs_count}\n\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en active_hypotheses: {e}")
            return f"❌ Error: {str(e)}"

    def _status(self) -> str:
        """Status general de MIE."""
        try:
            obs_count = len(self.db.get_observations(asset=None, lookback_hours=24, observation_type=None))
            hyp_count = len(self.db.get_active_hypotheses())
            logs = self.db.get_learning_logs(limit=1)

            response = "✅ **MIE V1 Status:**\n\n"
            response += f"  • Observaciones (24h): {obs_count}\n"
            response += f"  • Hipótesis activas: {hyp_count}\n"
            response += f"  • Learning logs: {len(logs)}\n"
            response += f"  • Assets monitorizados: BTC, ETH\n"
            response += f"  • Loops: Fast (5min), Daily (08:00 UTC), Weekly (Dom)\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en status: {e}")
            return f"❌ Error: {str(e)}"

    def _asset_query(self, asset: Optional[str]) -> str:
        """Query específico sobre un asset."""
        if not asset:
            return "❓ Asset no especificado. Usa: btc, eth"

        try:
            obs = self.db.get_observations(asset=asset, lookback_hours=24, observation_type="price")

            if not obs:
                return f"📊 Sin observaciones de {asset} en 24h"

            prices = [o["value"] for o in obs]
            current = prices[-1]
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)
            change = ((current - prices[0]) / prices[0] * 100) if prices[0] else 0

            response = f"📈 **{asset}USDT - Últimas 24h:**\n\n"
            response += f"  Precio actual: ${current:,.2f}\n"
            response += f"  Promedio: ${avg_price:,.2f}\n"
            response += f"  Rango: ${min_price:,.2f} - ${max_price:,.2f}\n"
            response += f"  Cambio: {change:+.2f}%\n"
            response += f"  Observaciones: {len(prices)}\n"

            # Hipótesis activas sobre este asset
            hyp_list = self.db.get_active_hypotheses()
            asset_hyps = [h for h in hyp_list if asset in h["text"].upper()]
            if asset_hyps:
                response += f"\n  **Hipótesis activas:**\n"
                for hyp in asset_hyps:
                    response += f"    • {hyp['hypothesis_id']}: {hyp['text']}\n"

            return response
        except Exception as e:
            self.logger.error(f"Error en asset_query: {e}")
            return f"❌ Error: {str(e)}"

    def _unknown_response(self, message: str) -> str:
        """Respuesta cuando no se clasifica el query."""
        return (
            "❓ No entiendo ese comando.\n\n"
            "**Prueba:**\n"
            "  • `como ves el mercado` - Overview del estado\n"
            "  • `que estoy mirando` - Qué observo\n"
            "  • `que aprendiste` - Mis aprendizajes\n"
            "  • `hipotesis activas` - Tests en curso\n"
            "  • `status` - Mi estado\n"
            "  • `btc` o `eth` - Sobre ese asset\n"
            "  • `esto fue util` - Feedback positivo\n"
            "  • `esto fue ruido` - Feedback negativo\n"
            "  • `enfocate mas en btc` - Cambiar prioridades\n"
        )

    def handle_feedback(self, feedback_type: QueryType, message: str, user_id: str) -> str:
        """
        Procesa feedback del usuario.

        Args:
            feedback_type: Tipo de feedback (positive, negative, focus, timeframe)
            message: Mensaje completo del usuario
            user_id: ID del usuario en Telegram

        Returns:
            Confirmación de feedback procesado
        """
        try:
            # Guardar feedback en base de datos
            self.db.add_user_feedback(
                feedback_type=feedback_type.value,
                context=message
            )

            # Procesar según tipo
            if feedback_type == QueryType.FEEDBACK_POSITIVE:
                response = "✅ Feedback positivo registrado. Continuaré así."
            elif feedback_type == QueryType.FEEDBACK_NEGATIVE:
                response = "📝 Feedback negativo registrado. Revisaré mis criterios."
            elif feedback_type == QueryType.FEEDBACK_FOCUS:
                # Extraer asset a priorizar
                focus_match = re.search(r"mas en (\w+)|más en (\w+)", message.lower())
                if focus_match:
                    asset = (focus_match.group(1) or focus_match.group(2)).upper()
                    response = f"🎯 Aumentando prioridad en {asset}. Lo haré."
                else:
                    response = "📝 Feedback de prioridad registrado."
            elif feedback_type == QueryType.FEEDBACK_TIMEFRAME:
                response = "⏱️ Preferencia de timeframe registrada."
            else:
                response = "📝 Feedback registrado."

            self.logger.info(f"Feedback procesado: {feedback_type.value} de {user_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error procesando feedback: {e}")
            return f"❌ Error registrando feedback: {str(e)}"

    def handle_message(self, message: str, user_id: str) -> str:
        """
        Maneja un mensaje de usuario completo.

        Args:
            message: Mensaje del usuario
            user_id: ID del usuario en Telegram (usado para logging)

        Returns:
            Respuesta de MIE
        """
        try:
            # Clasificar query
            query_type, param = self.classify_query(message)

            # Generar respuesta según tipo
            if query_type == QueryType.MARKET_OVERVIEW:
                response = self._market_overview()
            elif query_type == QueryType.WHAT_WATCHING:
                response = self._what_watching()
            elif query_type == QueryType.WHAT_LEARNED:
                response = self._what_learned()
            elif query_type == QueryType.ACTIVE_HYPOTHESES:
                response = self._active_hypotheses()
            elif query_type == QueryType.STATUS:
                response = self._status()
            elif query_type == QueryType.ASSET_QUERY:
                response = self._asset_query(param)
            elif query_type == QueryType.FEEDBACK_POSITIVE:
                response = self.handle_feedback(query_type, message, user_id)
            elif query_type == QueryType.FEEDBACK_NEGATIVE:
                response = self.handle_feedback(query_type, message, user_id)
            elif query_type == QueryType.FEEDBACK_FOCUS:
                response = self.handle_feedback(query_type, message, user_id)
            elif query_type == QueryType.FEEDBACK_TIMEFRAME:
                response = self.handle_feedback(query_type, message, user_id)
            else:
                response = self._unknown_response(message)

            # Guardar diálogo en BD
            try:
                self.db.add_dialogue(message, response, context=query_type.value)
            except Exception as db_error:
                self.logger.warning(f"Could not save dialogue to DB: {db_error}")

            self.logger.info(f"Diálogo procesado: {query_type.value} de {user_id}")

            return response

        except Exception as e:
            self.logger.error(f"Error en handle_message: {e}")
            return f"❌ Error procesando tu mensaje: {str(e)}"
