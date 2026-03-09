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

seen_battles = set()

# ------------------------
# TELEGRAM COMMANDS
# ------------------------

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
        "Bot activo.\n\n"
        "Comandos:\n"
        "/threshold <valor>\n"
        "/min_pool <valor>\n"
        "/help"
    )


async def help_cmd(update, context):

    await update.message.reply_text(
        "Comandos disponibles:\n\n"
        "/threshold 1.5\n"
        "/min_pool 200\n"
    )


async def threshold(update, context):

    if not context.args:
        await update.message.reply_text("Uso: /threshold 1.5")
        return

    value = float(context.args[0])

    pool = get_db_pool()
    user_id = update.effective_user.id

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET threshold=$1 WHERE user_id=$2",
            value,
            user_id
        )

    await update.message.reply_text(f"Threshold actualizado a {value}")


async def min_pool(update, context):

    if not context.args:
        await update.message.reply_text("Uso: /min_pool 200")
        return

    value = float(context.args[0])

    pool = get_db_pool()
    user_id = update.effective_user.id

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET min_pool=$1 WHERE user_id=$2",
            value,
            user_id
        )

    await update.message.reply_text(f"Min pool actualizado a {value}")


# ------------------------
# HEALTHCHECK
# ------------------------

async def health(request):
    return web.Response(text="OK")


# ------------------------
# EXTRAER BATTLES
# ------------------------

def extract_battles(data):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for value in data.values():
            result = extract_battles(value)
            if result:
                return result

    return []


# ------------------------
# BATTLE CHECKER
# ------------------------

async def battle_checker(app):

    logger.info("Battle checker started")

    telegram_app = app["telegram_app"]

    async with httpx.AsyncClient(timeout=20) as client:

        while True:

            try:

                r = await client.get(
                    "https://api2.warera.io/trpc/battle.getBattles",
                    params={"input": '{"isActive": true}'}
                )

                data = r.json()

                battles = extract_battles(data)

                if not battles:
                    await asyncio.sleep(30)
                    continue

                pool = get_db_pool()

                async with pool.acquire() as conn:
                    users = await conn.fetch(
                        "SELECT user_id, threshold, min_pool FROM users"
                    )

                for battle in battles:

                    battle_id = (
                        battle.get("battleId")
                        or battle.get("id")
                    )

                    if not battle_id:
                        continue

                    if battle_id in seen_battles:
                        continue

                    seen_battles.add(battle_id)

                    pool_size = float(battle.get("pool", 0))
                    threshold_value = float(battle.get("multiplier", 0))

                    logger.info(
                        f"New battle {battle_id} pool={pool_size} threshold={threshold_value}"
                    )

                    for user in users:

                        if threshold_value < user["threshold"]:
                            continue

                        if pool_size < user["min_pool"]:
                            continue

                        try:

                            await telegram_app.bot.send_message(
                                chat_id=user["user_id"],
                                text=(
                                    f"⚔️ Nueva Battle detectada\n\n"
                                    f"ID: {battle_id}\n"
                                    f"Pool: {pool_size}\n"
                                    f"Multiplier: {threshold_value}"
                                )
                            )

                        except Exception as e:

                            logger.error(f"Telegram send error: {e}")

            except Exception as e:

                logger.error(f"Battle checker error: {e}")

            await asyncio.sleep(30)


# ------------------------
# BACKGROUND TASKS
# ------------------------

async def start_background_tasks(app):

    app["battle_checker"] = asyncio.create_task(
        battle_checker(app)
    )


async def cleanup_background_tasks(app):

    task = app["battle_checker"]
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


# ------------------------
# TELEGRAM START
# ------------------------

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


# ------------------------
# APP FACTORY
# ------------------------

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


app = init_app()
