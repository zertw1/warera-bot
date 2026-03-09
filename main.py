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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Ej: https://<tu-dominio>/webhook/<bot_token>

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
# TELEGRAM COMMANDS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1::BIGINT) ON CONFLICT DO NOTHING",
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
        logger.error(f"/start error: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id=$1::BIGINT", user_id)
        await update.message.reply_text("⛔ Alertas desactivadas")
    except Exception as e:
        logger.error(f"/stop error: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT threshold, min_pool FROM users WHERE user_id=$1::BIGINT", user_id
            )
        if not row:
            await update.message.reply_text("No estás registrado. Usa /start")
            return
        await update.message.reply_text(
            f"📊 Estado del Bot\nThreshold: {row['threshold']}\nMin Pool: {row['min_pool']}"
        )
    except Exception as e:
        logger.error(f"/status error: {e}")

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /threshold <valor>")
        return
    try:
        value = float(context.args[0])
        user_id = update.effective_user.id
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET threshold=$1 WHERE user_id=$2::BIGINT", value, user_id
            )
        await update.message.reply_text(f"Threshold actualizado a {value}")
    except Exception as e:
        logger.error(f"/threshold error: {e}")

async def min_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /min_pool <valor>")
        return
    try:
        value = float(context.args[0])
        user_id = update.effective_user.id
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET min_pool=$1 WHERE user_id=$2::BIGINT", value, user_id
            )
        await update.message.reply_text(f"Min pool actualizado a {value}")
    except Exception as e:
        logger.error(f"/min_pool error: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos:\n/start\n/stop\n/status\n/threshold <valor>\n/min_pool <valor>"
    )

# -------------------------
# HEALTHCHECK
# -------------------------
async def health(request):
    return web.Response(text="OK")

# -------------------------
# WEBHOOK HANDLER
# -------------------------
async def telegram_webhook(request):
    data = await request.json()
    update = Update.de_json(data, request.app["bot"])
    await request.app["application"].update_queue.put(update)
    return web.Response(text="OK")

# -------------------------
# BATTLE CHECKER
# -------------------------
def extract_battles(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            result = extract_battles(v)
            if result:
                return result
    return []

async def battle_checker(application: Application):
    logger.info("Battle watcher started")
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            try:
                r = await client.get(
                    "https://api2.warera.io/trpc/battle.getBattles",
                    params={"input": '{"isActive": true}'}
                )
                battles = extract_battles(r.json())
                if not battles:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                async with pool.acquire() as conn:
                    users = await conn.fetch("SELECT user_id, threshold, min_pool FROM users")
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
                        if bounty < user["threshold"] or pool_size < user["min_pool"]:
                            continue
                        if previous_bounty >= user["threshold"]:
                            continue
                        try:
                            await application.bot.send_message(
                                chat_id=int(user["user_id"]),
                                text=f"🎯 High Bounty Detectado\nBattle: {battle_id}\nBounty: {bounty}\nPool: {pool_size}"
                            )
                        except Exception as e:
                            logger.error(f"Telegram error: {e}")
            except Exception as e:
                logger.error(f"Battle checker error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

# -------------------------
# START SERVICES
# -------------------------
async def start_services(app: web.Application):
    await init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("threshold", threshold))
    application.add_handler(CommandHandler("min_pool", min_pool))
    application.add_handler(CommandHandler("help", help_cmd))

    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}")
    app["bot"] = application
    app["application"] = application

    # Start battle checker
    asyncio.create_task(battle_checker(application))

async def stop_services(app: web.Application):
    if "bot" in app:
        await app["bot"].shutdown()
        await app["bot"].stop()

# -------------------------
# APP FACTORY
# -------------------------
async def init_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post(f"/webhook/{BOT_TOKEN}", telegram_webhook)
    app.on_startup.append(start_services)
    app.on_cleanup.append(stop_services)
    return app

app = init_app
