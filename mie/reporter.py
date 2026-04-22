"""
MIE Reporter - Comunicación vía Telegram

Tres tipos de mensajes:
├─ Heartbeat: estado operacional
├─ Daily Report: reflexión + estado de hipótesis
└─ Weekly Report: meta-thinking
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime


class Reporter:
    def __init__(self, telegram_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        self.token = telegram_token
        self.chat_id = telegram_chat_id
        self.base_url = "https://api.telegram.org"
        self.logger = logging.getLogger("MIE.Reporter")

        if not self.token or not self.chat_id:
            self.logger.warning("⚠️  Telegram no configurado - reportes solo en logs")
            self.enabled = False
        else:
            self.enabled = True

    def send_heartbeat(self, message: str):
        """Envía heartbeat (estado operacional)"""
        text = f"❤️ MIE Heartbeat\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n{message}"
        self._send_message(text)

    def send_error(self, error_message: str):
        """Envía notificación de error"""
        text = f"❌ MIE ERROR\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n{error_message}"
        self._send_message(text)

    def send_daily_report(self, summary: Dict, hypotheses: List[Dict]):
        """Envía reporte diario"""
        text = "📊 MIE DAILY REPORT\n"
        text += f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        # Resumen de observaciones
        text += "📈 Market Snapshot (24h):\n"
        for asset, data in summary.items():
            if isinstance(data, dict):
                text += f"\n{asset}:\n"
                text += f"  Current: ${data.get('current_price', 0):.2f}\n"
                text += f"  24h Range: ${data.get('min_price', 0):.2f} - ${data.get('max_price', 0):.2f}\n"
                text += f"  Observations: {data.get('obs_count', 0)}\n"

        # Estado de hipótesis
        text += f"\n🔬 Research Status:\n"
        text += f"  Active hypotheses: {len(hypotheses)}\n"
        if hypotheses:
            for hyp in hypotheses[:3]:  # Top 3 por brevedad
                text += f"  • {hyp['hypothesis_id']}: {hyp['status']}\n"

        self._send_message(text)

    def send_weekly_report(self, summary: Dict, hypotheses: List[Dict]):
        """Envía reporte semanal"""
        text = "🌙 MIE WEEKLY REPORT\n"
        text += f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        # Meta-reflexión
        text += "📊 Weekly Analysis:\n"
        for asset, data in summary.items():
            if isinstance(data, dict):
                text += f"\n{asset} (7d):\n"
                text += f"  Current: ${data.get('current_price', 0):.2f}\n"
                text += f"  Weekly Range: ${data.get('min_price', 0):.2f} - ${data.get('max_price', 0):.2f}\n"
                text += f"  Average: ${data.get('avg_price', 0):.2f}\n"

        # Hipótesis clasificadas
        text += f"\n🔬 Hypothesis Summary:\n"
        text += f"  Total active: {len(hypotheses)}\n"

        supported = [h for h in hypotheses if h.get('status') == 'supported']
        if supported:
            text += f"  Supported: {len(supported)}\n"
            for hyp in supported[:2]:
                text += f"    • {hyp.get('hypothesis_id', 'unknown')}\n"

        self._send_message(text)

    def _send_message(self, text: str):
        """Envía mensaje a Telegram (o log si no configurado)"""
        if not self.enabled:
            self.logger.info(f"📭 [Telegram disabled] {text}")
            return

        try:
            url = f"{self.base_url}/bot{self.token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            self.logger.info("✅ Mensaje enviado a Telegram")
        except requests.RequestException as e:
            self.logger.error(f"❌ Error enviando Telegram: {e}")
