"""
MIE Orchestrator - Coordinador de loops

Maneja tres ciclos:
├─ Fast Loop (cada 5 min): Ingesta de observaciones
├─ Daily Loop (08:00 UTC): Reflexión + investigación
└─ Weekly Loop (domingo): Meta-thinking + hypothesis review
"""

import schedule
import time
import logging
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from mie.database import MIEDatabase
from mie.hypothesis_analyzer import HypothesisAnalyzer
from mie.feedback_learner import FeedbackLearner
from mie.multi_timeframe_validator import MultiTimeframeValidator
from mie.enhanced_telegram_reporter import EnhancedTelegramReporter
from mie.readiness_calculator import ReadinessCalculator
from mie.hypothesis_predictor import HypothesisPredictor
from mie.asset_correlation import AssetCorrelationAnalyzer
from mie.binance_client import BinanceClient
from mie.research_layer import ResearchLayer
from mie.reporter import Reporter
from mie.dialogue import DialogueHandler


class MIEOrchestrator:
    def __init__(self, db_path: str = "mie.db", telegram_token: str = None,
                 telegram_chat_id: str = None):
        self.db = MIEDatabase(db_path)
        self.binance = BinanceClient()
        self.research = ResearchLayer(self.db)
        self.reporter = Reporter(telegram_token, telegram_chat_id)
        self.dialogue = DialogueHandler(self.db, self._setup_logger())
        self.logger = self._setup_logger()

        # Telegram config
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.analyzer = HypothesisAnalyzer(logger=self.logger)
        self.feedback_learner = FeedbackLearner(db=self.db, logger=self.logger)
        self.validator_mtf = MultiTimeframeValidator(db=self.db, logger=self.logger)
        self.enhanced_reporter = EnhancedTelegramReporter(
            telegram_token=self.telegram_token,
            telegram_chat_id=self.telegram_chat_id,
            analyzer=self.analyzer,
            learner=self.feedback_learner,
            validator=self.validator_mtf,
            logger=self.logger
        )
        self.readiness = ReadinessCalculator(db=self.db, logger=self.logger)
        self.predictor = HypothesisPredictor(db=self.db, logger=self.logger)
        self.correlation = AssetCorrelationAnalyzer(db=self.db, logger=self.logger)

        # Assets a observar (V1)
        self.assets = ["BTC", "ETH"]

        # Banderas de control
        self.running = False
        self.last_daily = None
        self.last_weekly = None
        self.last_message_id = 0

    def _setup_logger(self):
        """Configura logger"""
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)

        logger = logging.getLogger("MIE")
        logger.setLevel(logging.INFO)

        fh = logging.FileHandler(log_path / "mie.log")
        ch = logging.StreamHandler()

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _check_telegram_messages(self):
        """Verifica y procesa mensajes nuevos de Telegram"""
        if not self.telegram_token:
            return  # Sin Telegram configurado

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
            params = {"offset": self.last_message_id + 1}

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            if not data.get("ok"):
                self.logger.error(f"Telegram API error: {data.get('description')}")
                return

            updates = data.get("result", [])
            for update in updates:
                self.last_message_id = max(self.last_message_id, update["update_id"])

                # Solo procesa mensajes de texto
                if "message" in update and "text" in update["message"]:
                    message = update["message"]
                    user_id = str(message["from"]["id"])
                    text = message["text"]

                    self.logger.info(f"💬 Mensaje de {user_id}: {text}")

                    # Intercepta comandos /debug
                    if text.startswith("/debug"):
                        response = self._handle_debug_command(text, user_id)
                        # Debug messages sin markdown parsing
                        self._send_telegram_message(response, use_markdown=False)
                    else:
                        # Procesa con DialogueHandler
                        response = self.dialogue.handle_message(text, user_id)
                        # Diálogo normal con markdown
                        self._send_telegram_message(response, use_markdown=True)

        except requests.RequestException as e:
            self.logger.error(f"Error checking Telegram messages: {e}")
        except Exception as e:
            self.logger.error(f"Error processing Telegram message: {e}")

    def _send_telegram_message(self, text: str, use_markdown: bool = True):
        """Envía un mensaje a Telegram. Convierte dicts a string si es necesario."""
        if not self.telegram_token or not self.telegram_chat_id:
            self.logger.warning("Telegram no configurado, mensaje no enviado")
            return

        try:
            # Convierte dict a string si es necesario
            if isinstance(text, dict):
                text = str(text)
            
            # Limita a 4096 chars (límite de Telegram)
            text = str(text)[:4096]
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {
                "chat_id": self.telegram_chat_id,
                "text": text,
            }
            
            # Solo usa Markdown si está habilitado
            if use_markdown:
                params["parse_mode"] = "Markdown"

            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()

            self.logger.info("✅ Respuesta enviada a Telegram")

        except requests.RequestException as e:
            self.logger.error(f"Error sending Telegram message: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending message: {e}")

    def fast_loop(self):
        """Ejecuta cada 5 minutos: ingesta de observaciones + check mensajes"""
        try:
            self.logger.info("▶️  FAST LOOP iniciando...")

            # Chequea mensajes de Telegram
            self._check_telegram_messages()

            for asset in self.assets:
                try:
                    # Obtiene datos crudos de Binance
                    raw_obs = self.binance.ingest_observation(asset)
                    parsed = self.binance.parse_observation(raw_obs)

                    # Persiste precio como observación
                    self.db.add_observation(
                        asset=asset,
                        observation_type="price",
                        value=parsed["price"],
                        context=f"24h_change: {parsed['price_24h_change']:.2f}%, vol: {parsed['volume_24h']:.0f}"
                    )

                    # Persiste funding rate si existe
                    if parsed["funding_rate"] is not None:
                        self.db.add_observation(
                            asset=asset,
                            observation_type="funding_rate",
                            value=parsed["funding_rate"],
                            context=f"funding_time: {parsed['funding_time']}"
                        )

                    # Persiste OI si existe
                    if parsed["open_interest"] is not None:
                        self.db.add_observation(
                            asset=asset,
                            observation_type="open_interest",
                            value=parsed["open_interest"],
                            context=f"value_usdt: {parsed['open_interest_value']:.0f}"
                        )

                    self.logger.info(f"✅ {asset}: price=${parsed['price']:.2f}, "
                                   f"funding={parsed['funding_rate']:.6f}" if parsed["funding_rate"] else "")

                except Exception as e:
                    self.logger.error(f"❌ Error ingesting {asset}: {e}")

            # Detecta si hay oportunidad de generar nuevas hipótesis
            # (basado en 2+ observaciones de mismo tipo para mismo asset)
            self.research.check_hypothesis_triggers()

            self.logger.info("✅ FAST LOOP completado")

        except Exception as e:
            self.logger.error(f"FAST LOOP error: {e}")
            self.reporter.send_error(f"Fast loop error: {e}")

    def daily_loop(self):
        """Ejecuta a las 08:00 UTC: reflexion + investigacion + research layer"""
        try:
            self.logger.info("\n🔄 DAILY LOOP iniciando...")
            summary = self._reflect_on_observations(lookback_hours=24)
            new_hyps = self.research.generate_micro_hypotheses()
            self.logger.info(f"Generated {len(new_hyps)} micro-hypotheses")
            
            registry = self.research._load_hypothesis_registry()
            active_hyps = self.db.get_active_hypotheses()
            
            self.db.add_learning_log(
                log_type="daily",
                content=json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "summary": summary,
                    "new_hypotheses": len(new_hyps),
                    "active": len(active_hyps)
                })
            )
            
            self.reporter.send_daily_report(summary, active_hyps)
            self.logger.info("✅ DAILY LOOP completado\n")
            self.last_daily = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"DAILY LOOP error: {e}", exc_info=True)
            self.reporter.send_error(f"Daily loop error: {e}")

    def weekly_loop(self):
        """Ejecuta domingo 20:00 UTC: research review + hypothesis management"""
        try:
            self.logger.info("\n🌙 WEEKLY LOOP iniciando...")
            experiment_summary = self.research.get_experiment_summary()
            self.logger.info(f"Experiments this week: {experiment_summary['this_week']}")
            
            registry = self.research._load_hypothesis_registry()
            all_hyps = self.db.get_active_hypotheses()
            demoted_count = 0
            
            for hyp in all_hyps:
                if hyp.get("confidence") == "falsified":
                    self.research.finalize_hypothesis(hyp["hypothesis_id"], "falsified", "Success rate < 60%")
                    demoted_count += 1
            
            self.db.add_learning_log(
                log_type="weekly",
                content=json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "active": len(all_hyps),
                    "demoted": demoted_count
                })
            )
            
            weekly_summary = self._reflect_on_observations(lookback_hours=24*7)
            self.reporter.send_weekly_report(weekly_summary, all_hyps)
            self.logger.info("✅ WEEKLY LOOP completado\n")
            self.last_weekly = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"WEEKLY LOOP error: {e}", exc_info=True)
            self.reporter.send_error(f"Weekly loop error: {e}")

    def monthly_loop(self):
        """Ejecuta 1st of month 18:00 UTC: research health check"""
        try:
            self.logger.info("\n📅 MONTHLY LOOP iniciando...")
            registry = self.research._load_hypothesis_registry()
            hypotheses_active = len(registry.get("active", []))
            supported_count = sum(1 for h in registry.get("active", []) if h.get("confidence") in ["supported", "strongly_supported"])
            
            self.logger.info(f"Active: {hypotheses_active}, Supported: {supported_count}")
            
            self.db.add_learning_log(
                log_type="monthly",
                content=json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "active": hypotheses_active,
                    "supported": supported_count
                })
            )
            
            month_summary = self._reflect_on_observations(lookback_hours=24*30)
            self.reporter.send_monthly_report(month_summary, self.db.get_active_hypotheses())
            self.logger.info("✅ MONTHLY LOOP completado\n")
            self.last_monthly = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"MONTHLY LOOP error: {e}", exc_info=True)
            self.reporter.send_error(f"Monthly loop error: {e}")

    def dialogue_loop(self):
        """Ejecuta constantemente: chequea y procesa mensajes de Telegram"""
        try:
            self._check_telegram_messages()
        except Exception as e:
            self.logger.error(f"Dialogue loop error: {e}")

    def _reflect_on_observations(self, lookback_hours: int) -> Dict:
        """Reflexiona sobre observaciones recientes"""
        summary = {}

        for asset in self.assets:
            obs_price = self.db.get_observations(
                asset, lookback_hours=lookback_hours, observation_type="price"
            )

            if obs_price:
                prices = [o["value"] for o in obs_price]
                summary[asset] = {
                    "obs_count": len(obs_price),
                    "current_price": prices[0],  # más reciente
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "avg_price": sum(prices) / len(prices)
                }

        return summary

    def schedule_loops(self):
        """Configura schedule con tres ciclos + dialogue"""
        # Fast loop: cada 5 minutos
        schedule.every(5).minutes.do(self.fast_loop)

        # Daily loop: 08:00 UTC
        schedule.every().day.at("08:00").do(self.daily_loop)

        # Weekly loop: domingo a las 08:00 UTC
        schedule.every().sunday.at("08:00").do(self.weekly_loop)

        # Monthly loop: 1º de mes 18:00 UTC
        schedule.every().day.at("18:00").do(self._check_monthly_schedule)

        # Dialogue loop: cada 30 segundos (chequea Telegram)
        schedule.every(30).seconds.do(self.dialogue_loop)

        self.logger.info("✅ Loops programados:")
        self.logger.info("  - Fast: cada 5 minutos")
        self.logger.info("  - Daily: 08:00 UTC")
        self.logger.info("  - Weekly: domingo 08:00 UTC")
        self.logger.info("  - Dialogue: cada 30 segundos (Telegram)")



    def _check_monthly_schedule(self):
        """Helper para ejecutar monthly_loop el 1º de cada mes a las 18:00 UTC"""
        from datetime import datetime
        if datetime.utcnow().day == 1 and datetime.utcnow().hour == 18:
            self.monthly_loop()

    def run(self):
        """Loop principal: ejecuta scheduler"""
        self.running = True
        self.logger.info("🚀 MIE V1 iniciando...")
        self.logger.info(f"   Assets: {self.assets}")
        self.logger.info(f"   DB: {self.db.db_path}")

        self.schedule_loops()

        # Envía heartbeat inicial
        self.reporter.send_heartbeat("MIE V1 iniciado correctamente")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("⏹️  MIE detenido por usuario")
            self.reporter.send_heartbeat("MIE V1 detenido")
        finally:
            self.db.close()

    def stop(self):
        """Detiene ejecución"""
        self.running = False

    def _handle_debug_command(self, text: str, user_id: str) -> str:
        """
        Maneja comandos /debug directamente sin pasar por intent_parser.
        Parsing simple y directo.
        """
        try:
            # Normalizar: strip, lowercase, remover / inicial
            clean = text.strip().lower()
            if clean.startswith("/"):
                clean = clean[1:]
            
            # Split por espacios
            parts = clean.split()
            cmd = parts[0] if len(parts) > 0 else ""
            arg = parts[1].lower() if len(parts) > 1 else "status"
            
            # Log del parsing
            self.logger.info(f"🔧 Debug raw text: '{text}'")
            self.logger.info(f"🔧 Debug parts: {parts}")
            self.logger.info(f"🔧 Debug arg: '{arg}'")
            
            # Llama a DebugService basado en arg - dispatch explícito
            from mie.debug_service import DebugService
            debug_service = DebugService(self.db, self.binance, self.logger)
            
            if arg == "btc":
                response = debug_service.test_binance_fetch("BTCUSDT")
            elif arg == "eth":
                response = debug_service.test_binance_fetch("ETHUSDT")
            elif arg == "all":
                response = debug_service.full_diagnostic()
            elif arg == "status":
                response = f"✅ MIE V1 running\nAssets: {self.assets}\nDB: {self.db_path}"
            else:
                response = f"✅ MIE V1 running\nAssets: {self.assets}\nDB: {self.db_path}"
            
            # Debug route temporario
            return f"DEBUG ROUTE = {arg}\n\n{response}"
            
        except Exception as e:
            self.logger.error(f"Error in debug command: {e}")
            return f"❌ Debug error: {str(e)}"

