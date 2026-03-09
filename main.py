import os
import asyncio
import logging
import httpx

from aiohttp import web
from telegram.ext import Application, CommandHandler

from database import init_db, get_db_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")


# -----------------------
# Telegram commands
# -----------------------

async def start(update, context):

    user_id = update.effective_user.id
    pool = get_db_pool()

    async with pool.acquire() as conn:

        await conn.execute(
            """
            INSERT INTO users (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id
        )

    await update.message.reply_text(
        "✅ You are registered!\n\n"
        "Commands:\n"
        "/threshold <value>\n"
        "/min_pool <value>\n"
        "/help"
    )


async def help_cmd(update, context):

    await update.message.reply_text(
        "Commands:\n"
        "/threshold <value>\n"
        "/min_pool <value>\n"
    )


async def threshold(update, context):

    if not context.args:
        await update.message.reply_text("Usage: /threshold <value>")
        return

    value = float(context.args[0])

    user_id = update.effective_user.id
    pool = get_db_pool()

    async with pool.acquire() as conn:

        await conn.execute(
            """
            UPDATE users
            SET threshold=$1
            WHERE user_id=$2
            """,
            value,
            user_id
        )

    await update.message.reply_text(f"✅ Threshold set to {value}")


async def min_pool(update, context):

    if not context.args:
        await update.message.reply_text("Usage: /min_pool <value>")
        return

    value = float(context.args[0])

    user_id = update.effective_user.id
    pool = get_db_pool()

    async with pool.acquire() as conn:

        await conn.execute(
            """
            UPDATE users
            SET min_pool=$1
            WHERE user_id=$2
            """,
            value,
            user_id
        )

    await update.message.reply_text(f"✅ Min pool set to {value}")


# -----------------------
# Health endpoint
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

                logger.info(f"WarEra response: {data}")

                battles = []

                if "result" in data:
                    result = data["result"]

                    if "data" in result and "json" in result["data"]:
                        battles = result["data"]["json"]

                    elif "data" in result:
                        battles = result["data"]

                battle_ids = []

                for b in battles:
                    if isinstance(b, dict):
                        if "battleId" in b:
                            battle_ids.append(b["battleId"])
                        elif "id" in b:
                            battle_ids.append(b["id"])

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
    application.add_handler(CommandHandler("threshold", threshold))
    application.add_handler(CommandHandler("min_pool", min_pool))

    await application.initialize()

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
# Run app
# -----------------------

app = init_app()
