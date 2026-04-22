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

                    # Procesa con DialogueHandler
                    response = self.dialogue.handle_message(text, user_id)

                    # Envía respuesta
                    self._send_telegram_message(response)

        except requests.RequestException as e:
            self.logger.error(f"Error checking Telegram messages: {e}")
        except Exception as e:
            self.logger.error(f"Error processing Telegram message: {e}")

    def _send_telegram_message(self, text: str):
        """Envía un mensaje a Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            self.logger.warning("Telegram no configurado, mensaje no enviado")
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            params = {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }

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
        """Ejecuta a las 08:00 UTC: reflexión + investigación"""
        try:
            self.logger.info("\n🔄 DAILY LOOP iniciando...")

            # Reflexión: resume observaciones de 24h
            summary = self._reflect_on_observations(lookback_hours=24)
            self.logger.info(f"📊 Resumen 24h: {summary}")

            # Research: ejecuta experimentos pendientes
            active_hyps = self.db.get_active_hypotheses()
            self.logger.info(f"🔬 Hipótesis activas: {len(active_hyps)}")

            for hyp in active_hyps:
                if hyp["status"] == "testing":
                    result = self.research.run_experiment(hyp["hypothesis_id"])
                    self.logger.info(f"📈 Experimento para {hyp['hypothesis_id']}: {result}")

            # Learning log
            self.db.add_learning_log(
                log_type="daily",
                content=json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "observation_summary": summary,
                    "active_hypotheses": len(active_hyps)
                })
            )

            # Reportea
            self.reporter.send_daily_report(summary, active_hyps)

            self.logger.info("✅ DAILY LOOP completado\n")
            self.last_daily = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"DAILY LOOP error: {e}")
            self.reporter.send_error(f"Daily loop error: {e}")

    def weekly_loop(self):
        """Ejecuta domingo: meta-thinking + hypothesis review"""
        try:
            self.logger.info("\n🌙 WEEKLY LOOP iniciando...")

            # Meta-reflexión sobre la semana
            weekly_summary = self._reflect_on_observations(lookback_hours=24*7)
            self.logger.info(f"📊 Resumen semanal: {weekly_summary}")

            # Revisa todas las hipótesis
            all_hyps = self.db.get_active_hypotheses()

            # Clasifica hipótesis que terminaron testing
            for hyp in all_hyps:
                if hyp["status"] == "testing":
                    # Aquí iría lógica de clasificación (falsified/weakly/supported/strongly)
                    # Por ahora solo registra
                    self.logger.info(f"📋 Hipótesis {hyp['hypothesis_id']} aún en testing")

            # Learning log semanal
            self.db.add_learning_log(
                log_type="weekly",
                content=json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "weekly_summary": weekly_summary,
                    "total_hypotheses": len(all_hyps),
                    "observations_7d": len(self.db.get_observations("BTC", lookback_hours=24*7))
                })
            )

            # Reportea
            self.reporter.send_weekly_report(weekly_summary, all_hyps)

            self.logger.info("✅ WEEKLY LOOP completado\n")
            self.last_weekly = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"WEEKLY LOOP error: {e}")
            self.reporter.send_error(f"Weekly loop error: {e}")

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

        # Dialogue loop: cada 30 segundos (chequea Telegram)
        schedule.every(30).seconds.do(self.dialogue_loop)

        self.logger.info("✅ Loops programados:")
        self.logger.info("  - Fast: cada 5 minutos")
        self.logger.info("  - Daily: 08:00 UTC")
        self.logger.info("  - Weekly: domingo 08:00 UTC")
        self.logger.info("  - Dialogue: cada 30 segundos (Telegram)")


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
