import os
import asyncio
import logging
import httpx
import asyncpg

from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

pool = None
battle_bounties = {}

POLL_INTERVAL = 3

# -------------------------
# DATABASE
# -------------------------

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            threshold FLOAT DEFAULT 1,
            min_pool FLOAT DEFAULT 0
        )
        """)

# -------------------------
# COMMANDS
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id)
                VALUES ($1::BIGINT)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id
            )

        await update.message.reply_text(
            "🤖 Bot activado\n\n"
            "Comandos:\n"
            "/threshold <valor>\n"
            "/min_pool <valor>\n"
            "/status\n"
            "/stop"
        )
    except Exception as e:
        logger.error(f"Error en /start: {e}")
        await update.message.reply_text("⚠ Ocurrió un error al registrarte.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM users WHERE user_id=$1::BIGINT",
                user_id
            )

        await update.message.reply_text("⛔ Alertas desactivadas")
    except Exception as e:
        logger.error(f"Error en /stop: {e}")
        await update.message.reply_text("⚠ Ocurrió un error al desactivar alertas.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT threshold, min_pool
                FROM users
                WHERE user_id=$1::BIGINT
                """,
                user_id
            )

        if not row:
            await update.message.reply_text("No estás registrado. Usa /start")
            return

        await update.message.reply_text(
            f"📊 Estado del Bot\n\n"
            f"Threshold: {row['threshold']}\n"
            f"Min Pool: {row['min_pool']}"
        )
    except Exception as e:
        logger.error(f"Error en /status: {e}")
        await update.message.reply_text("⚠ Ocurrió un error al obtener tu estado.")


async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /threshold 1")
        return

    try:
        value = float(context.args[0])
        user_id = update.effective_user.id

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET threshold=$1 WHERE user_id=$2::BIGINT",
                value,
                user_id
            )

        await update.message.reply_text(f"Threshold actualizado a {value}")
    except Exception as e:
        logger.error(f"Error en /threshold: {e}")
        await update.message.reply_text("⚠ Ocurrió un error al actualizar el threshold.")


async def min_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /min_pool 0")
        return

    try:
        value = float(context.args[0])
        user_id = update.effective_user.id

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET min_pool=$1 WHERE user_id=$2::BIGINT",
                value,
                user_id
            )

        await update.message.reply_text(f"Min pool actualizado a {value}")
    except Exception as e:
        logger.error(f"Error en /min_pool: {e}")
        await update.message.reply_text("⚠ Ocurrió un error al actualizar min pool.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n\n"
        "/start\n"
        "/stop\n"
        "/status\n"
        "/threshold 1\n"
        "/min_pool 0"
    )

# -------------------------
# HEALTHCHECK
# -------------------------

async def health(request):
    return web.Response(text="OK")

# -------------------------
# BATTLE PARSER
# -------------------------

def extract_battles(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            result = extract_battles(value)
            if result:
                return result
    return []

# -------------------------
# BATTLE CHECKER
# -------------------------

async def battle_checker(application):
    logger.info("Battle watcher started")

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
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                async with pool.acquire() as conn:
                    users = await conn.fetch(
                        "SELECT user_id, threshold, min_pool FROM users"
                    )

                for battle in battles:
                    battle_id = battle.get("battleId") or battle.get("id")
                    if not battle_id:
                        continue

                    bounty = float(battle.get("bounty", 0))
                    pool_size = float(battle.get("pool", 0))
                    previous_bounty = battle_bounties.get(battle_id, 0)
                    battle_bounties[battle_id] = bounty

                    if bounty <= previous_bounty:
                        continue

                    for user in users:
                        if bounty < user["threshold"]:
                            continue
                        if pool_size < user["min_pool"]:
                            continue
                        if previous_bounty >= user["threshold"]:
                            continue
                        try:
                            await application.bot.send_message(
                                chat_id=int(user["user_id"]),
                                text=(
                                    f"🎯 High Bounty Detectado\n\n"
                                    f"Battle: {battle_id}\n"
                                    f"Bounty: {bounty}\n"
                                    f"Pool: {pool_size}"
                                )
                            )
                        except Exception as e:
                            logger.error(f"Telegram error: {e}")
            except Exception as e:
                logger.error(f"Battle checker error: {e}")

            await asyncio.sleep(POLL_INTERVAL)

# -------------------------
# START SERVICES
# -------------------------

async def start_services(app):
    await init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("threshold", threshold))
    application.add_handler(CommandHandler("min_pool", min_pool))
    application.add_handler(CommandHandler("help", help_cmd))

    await application.initialize()
    await application.start()
    await application.bot.delete_webhook()

    # Start polling and battle checker concurrently
    asyncio.create_task(application.start_polling())
    asyncio.create_task(battle_checker(application))

    app["bot"] = application

async def stop_services(app):
    if "bot" in app:
        await app["bot"].stop()
        await app["bot"].shutdown()

# -------------------------
# APP FACTORY
# -------------------------

async def init_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.on_startup.append(start_services)
    app.on_cleanup.append(stop_services)
    return app

app = asyncio.run(init_app())
