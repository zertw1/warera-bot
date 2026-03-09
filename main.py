# main.py
import asyncio
import logging
import httpx

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# Configuración exacta de tus variables
# ------------------------------
TELEGRAM_BOT_TOKEN = "8793147335:AAFeugzoGREOE9EtCh-YDkaLCF5J3qPD9k4"
WEBHOOK_URL = "https://TU_APP.onrender.com/webhook"


# ------------------------------
# Handlers básicos
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)


# ------------------------------
# Tareas periódicas
# ------------------------------

async def battle_checker():
    while True:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get("https://example.com/status")
                logger.info(f"Battle checker: {r.status_code}")
        except RuntimeError as e:
            logger.warning(f"Loop cerrado, ignorando: {e}")
        except Exception as e:
            logger.error(f"Error battle_checker: {e}")
        await asyncio.sleep(60)


# ------------------------------
# Inicio y paro de servicios
# ------------------------------

async def start_services(app):
    application: Application = app["application"]

    if WEBHOOK_URL.startswith("https://"):
        try:
            await application.bot.set_webhook(WEBHOOK_URL)
            logger.info(f"Webhook configurado en {WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Error al configurar webhook: {e}")

    if not application.is_running:
        await application.start()
        logger.info("Application started")

    app["battle_task"] = asyncio.create_task(battle_checker())


async def stop_services(app):
    application: Application = app.get("application")
    if application and application.is_running:
        await application.stop()
        logger.info("Application stopped")

    task = app.get("battle_task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("battle_checker cancelado")


# ------------------------------
# Main
# ------------------------------

async def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    app_context = {"application": application}

    try:
        await start_services(app_context)
        await application.updater.start_polling()
    finally:
        await stop_services(app_context)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido")
