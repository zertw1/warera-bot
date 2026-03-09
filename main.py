# main.py
import logging
import asyncio
from aiohttp import web

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
# Configuración
# ------------------------------
TELEGRAM_BOT_TOKEN = "8793147335:AAFeugzoGREOE9EtCh-YDkaLCF5J3qPD9k4"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://merc-tool-bot-up4g.onrender.com/" + WEBHOOK_PATH  # <- reemplaza TU_APP.onrender.com


# ------------------------------
# Handlers
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)


# ------------------------------
# Inicializar aplicación de Telegram
# ------------------------------
def init_app():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    return application


# ------------------------------
# Configuración de AIOHTTP para Render
# ------------------------------
app = web.Application()
telegram_app = init_app()

async def handle(request):
    """Recibir POST de Telegram"""
    if request.method == "POST":
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.update_queue.put(update)
        return web.Response(text="OK")
    return web.Response(status=405)

app.router.add_post(WEBHOOK_PATH, handle)


# ------------------------------
# Webhook y ciclo de vida
# ------------------------------
async def on_startup(app):
    try:
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook configurado: {WEBHOOK_URL}")
        asyncio.create_task(telegram_app.start())
    except Exception as e:
        logger.error(f"Error al configurar webhook: {e}")

async def on_cleanup(app):
    await telegram_app.stop()
    logger.info("Bot detenido")

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)
