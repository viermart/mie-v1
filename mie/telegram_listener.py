"""
Telegram Listener for MIE V1
Listens for incoming messages and responds in real-time while scheduler runs in background.
"""

import logging
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Optional


class TelegramListener:
    """Handles real-time Telegram message listening and responses."""

    def __init__(self, telegram_token: str, orchestrator, logger: Optional[logging.Logger] = None):
        self.telegram_token = telegram_token
        self.orchestrator = orchestrator
        self.logger = logger or logging.getLogger("TelegramListener")
        self.application = None
        self.running = False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            message = (
                "✅ MIE V1 Sistema en línea\n\n"
                "Sistema inteligente de análisis de mercado activo.\n\n"
                "Comandos:\n"
                "/status - Ver estado del sistema\n"
                "/help - Ayuda\n\n"
                "El sistema está escaneando mercados continuamente..."
            )
            await update.message.reply_text(message)
            self.logger.info(f"Start command from {update.effective_user.id}")
        except Exception as e:
            self.logger.error(f"Error in start_command: {e}")
            try:
                await update.message.reply_text("❌ Error procesando comando")
            except:
                pass

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            scheduler_status = self.orchestrator.scheduler.get_status()
            message = (
                f"📊 Estado del Sistema\n\n"
                f"Tasks programadas: {scheduler_status.get('total_tasks', 0)}\n"
                f"Jobs activos: {scheduler_status.get('scheduled_jobs', 0)}\n"
                f"Estado: {'🟢 En línea' if scheduler_status.get('running') else '🔴 Parado'}\n"
            )
            await update.message.reply_text(message)
            self.logger.info(f"Status command from {update.effective_user.id}")
        except Exception as e:
            self.logger.error(f"Error in status_command: {e}")
            try:
                await update.message.reply_text("❌ Error obteniendo estado")
            except:
                pass

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
            message = (
                "🤖 MIE V1 - Comandos Disponibles\n\n"
                "/start - Iniciar sesión\n"
                "/status - Ver estado del sistema\n"
                "/help - Este mensaje\n\n"
                "El sistema ejecuta:\n"
                "• Fast Loop: Cada 5 minutos (escaneo de mercado)\n"
                "• Daily Loop: 08:00 UTC (análisis profundo)\n"
                "• Weekly Loop: Domingo 17:00 UTC (revisión semanal)\n"
                "• Monthly Loop: Primer día 00:00 UTC (revisión mensual)\n"
            )
            await update.message.reply_text(message)
            self.logger.info(f"Help command from {update.effective_user.id}")
        except Exception as e:
            self.logger.error(f"Error in help_command: {e}")
            try:
                await update.message.reply_text("❌ Error mostrando ayuda")
            except:
                pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages."""
        try:
            user_message = update.message.text
            user_id = update.effective_user.id

            self.logger.info(f"Message from {user_id}: {user_message}")

            # Simple response
            response = (
                f"✅ Mensaje recibido\n\n"
                f"El sistema MIE V1 está activo y monitoreando mercados.\n"
                f"Enviaste: {user_message[:50]}...\n\n"
                f"Usa /status para ver el estado o /help para más opciones."
            )

            await update.message.reply_text(response)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            try:
                await update.message.reply_text("❌ Error procesando mensaje")
            except:
                pass

    async def start_listening(self) -> None:
        """Start listening for Telegram messages."""
        try:
            self.logger.info("Iniciando Telegram listener...")

            self.application = Application.builder().token(self.telegram_token).build()

            # Register handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            self.running = True
            self.logger.info("✅ Telegram listener activo")

            # Start polling
            await self.application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            self.logger.error(f"Telegram listener error: {e}")
            self.running = False

    def start_in_thread(self) -> threading.Thread:
        """Start listener in background thread."""
        import asyncio

        def run_async_listener():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start_listening())
            finally:
                loop.close()

        thread = threading.Thread(target=run_async_listener, daemon=True)
        thread.start()
        self.logger.info("Telegram listener thread started")
        return thread

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        if self.application:
            self.application.stop_running()
        self.logger.info("Telegram listener stopped")
