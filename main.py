import asyncio
import logging
import os

from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -------- Logging --------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------- Telegram Commands --------

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot activo correctamente.\nUsa /status para comprobar estado."
    )

async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot funcionando correctamente.")

async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot detenido temporalmente.")


# -------- Healthcheck Endpoint --------

async def health(request):
    return web.Response(text="OK")


# -------- Background Task --------

async def background_job(app):
    while True:
        logger.info("Background job ejecutándose...")
        await asyncio.sleep(20)


# -------- Startup --------

async def start_background_tasks(app):
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN no está configurado")

    tg_app = ApplicationBuilder().token(telegram_token).build()

    tg_app.add_handler(CommandHandler("start", tg_start))
    tg_app.add_handler(CommandHandler("status", tg_status))
    tg_app.add_handler(CommandHandler("stop", tg_stop))

    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.initialize()
    await tg_app.bot.delete_webhook(drop_pending_updates=True)

    app["tg_app"] = tg_app
    app["worker"] = asyncio.create_task(background_job(app))


# -------- Cleanup --------

async def cleanup_background_tasks(app):
    if "worker" in app:
        app["worker"].cancel()
        try:
            await app["worker"]
        except asyncio.CancelledError:
            pass

    if "tg_app" in app:
        await app["tg_app"].stop()


# -------- App Factory --------

def init_app():
    app = web.Application()

    app.router.add_get("/health", health)

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app









