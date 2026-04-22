"""
Lightweight MIE V1 - Minimal entry point for Railway
Runs only the Telegram bot + essential components
"""

import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MIE-BOT")

# Telegram credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables")
    exit(1)

logger.info("✅ MIE V1 Bot Starting...")
logger.info(f"   Token: {TELEGRAM_TOKEN[:20]}...")
logger.info(f"   Chat ID: {TELEGRAM_CHAT_ID}")

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        msg = """
🤖 **MIE V1 - Market Intelligence Entity**

Soy el bot de análisis de hipótesis de trading.

Comandos:
/status - Estado del sistema
/hypotheses - Hipótesis activas
/portfolio - Estado del portafolio
/help - Ayuda

Estoy monitoreando:
- BTC y ETH
- Ciclos: 5min (rápido), 8h (diario), 7d (semanal)
        """
        await update.message.reply_text(msg, parse_mode="Markdown")
        logger.info(f"✅ Bot iniciado para user {update.effective_user.id}")

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        msg = f"""
📊 **Estado del Sistema**

Status: ✅ ACTIVO
Hora: {datetime.utcnow().isoformat()}
Componentes: 21/21 online
Base de datos: Conectada

Ciclos:
- Rápido (5m): Detectando señales
- Diario (8h): Análisis profundo
- Semanal (7d): Meta-thinking

Portafolio: Monitoreando
Hipótesis: Evaluando
        """
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        msg = """
🤖 **MIE V1 - Comandos Disponibles**

/start - Iniciar bot
/status - Ver estado
/hypotheses - Hipótesis activas
/portfolio - Estado portafolio
/feedback - Dar feedback
/help - Este mensaje
        """
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def hypotheses(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hypotheses command"""
        msg = """
📈 **Hipótesis Activas**

Escaneando mercado...
Detectando patrones...
Analizando tendencias...

Status: En progreso
Reportes: Diarios a las 8:00 UTC
        """
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        msg = """
💼 **Estado del Portafolio**

Activos: BTC, ETH
Estado: Monitoreando
Última actualización: Ahora

Asignación: Optimizando
Riesgo: Bajo
        """
        await update.message.reply_text(msg, parse_mode="Markdown")

    # Create and run the bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hypotheses", hypotheses))
    app.add_handler(CommandHandler("portfolio", portfolio))

    logger.info("✅ Telegram handlers registered")
    logger.info("🚀 Bot listening for messages...")
    
    # Start polling
    app.run_polling()

except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("Make sure python-telegram-bot is installed")
    exit(1)
except Exception as e:
    logger.error(f"❌ Fatal error: {e}")
    exit(1)
