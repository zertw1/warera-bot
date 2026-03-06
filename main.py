import asyncio
import logging
import os

from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# -------- TELEGRAM COMMANDS --------

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot activo correctamente.\nUsa /status para comprobar estado."
    )


async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot funcionando correctamente.")


async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot detenido.")


# -------- HEALTHCHECK --------

async def health(request):
    return web.Response(text="OK")


# -------- BACKGROUND TASK --------

async def background_job(app):
    while True:
        logger.info("Background job running...")
        await asyncio.sleep(20)


# -------- STARTUP --------

async def start_background_tasks(app):

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    tg_application = ApplicationBuilder().token(telegram_token).build()

    tg_application.add_handler(CommandHandler("start", tg_start))
    tg_application.add_handler(CommandHandler("status", tg_status))
    tg_application.add_handler(CommandHandler("stop", tg_stop))

    await tg_application.initialize()
    await tg_application.start()

    # polling
    await tg_application.bot.initialize()
    await tg_application.bot.delete_webhook(drop_pending_updates=True)

    app["tg_app"] = tg_application

    # background worker
    app["worker"] = asyncio.create_task(background_job(app))


# -------- CLEANUP --------

async def cleanup_background_tasks(app):

    if "worker" in app:
        app["worker"].cancel()

    if "tg_app" in app:
        await app["tg_app"].stop()


# -------- APP FACTORY --------

def init_app():

    app = web.Application()

    app.router.add_get("/health", health)

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app








