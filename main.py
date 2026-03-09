import os
import asyncio
import logging
import httpx

from aiohttp import web
from telegram.ext import Application, CommandHandler

from database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Leer token desde Render environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")


# -----------------------
# Telegram commands
# -----------------------

async def start(update, context):
    await update.message.reply_text("✅ Bot is running")

async def help_cmd(update, context):
    await update.message.reply_text(
        "Commands:\n"
        "/start\n"
        "/help"
    )


# -----------------------
# Health route (Render)
# -----------------------

async def health(request):
    return web.Response(text="OK")


# -----------------------
# Battle checker
# -----------------------

async def battle_checker(app):

    logger.info("Battle checker started")

    async with httpx.AsyncClient() as client:

        while True:

            try:

                response = await client.get(
                    "https://api2.warera.io/trpc/battle.getBattles",
                    params={"input": '{"isActive": true}'}
                )

                data = response.json()

                battles = data["result"]["data"]["json"]

                battle_ids = [
                    b.get("battleId") for b in battles if b.get("battleId")
                ]

                logger.info(f"Active battles: {battle_ids}")

            except Exception as e:
                logger.error(f"Battle checker error: {e}")

            await asyncio.sleep(30)


# -----------------------
# Background tasks
# -----------------------

async def start_background_tasks(app):

    app["battle_checker"] = asyncio.create_task(
        battle_checker(app)
    )


async def cleanup_background_tasks(app):

    app["battle_checker"].cancel()
    await app["battle_checker"]


# -----------------------
# Telegram bot startup
# -----------------------

async def start_bot(app):

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))

    await application.initialize()

    # limpiar webhook por si quedó configurado
    await application.bot.delete_webhook()

    await application.start()

    await application.updater.start_polling()

    app["telegram_app"] = application


async def stop_bot(app):

    await app["telegram_app"].stop()


# -----------------------
# App factory
# -----------------------

async def init_app():

    await init_db()

    app = web.Application()

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    app.on_startup.append(start_bot)
    app.on_startup.append(start_background_tasks)

    app.on_cleanup.append(cleanup_background_tasks)
    app.on_cleanup.append(stop_bot)

    return app


# -----------------------
# Run app (Render)
# -----------------------

app = init_app()
