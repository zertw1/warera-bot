import json
import asyncio
import logging
import os
from aiohttp import web
import httpx
import telegram

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import database as db
import shared_logic as shared
import discord_bot

# ---------------- LOGGING ----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------

def load_config():
    config = {}

    config["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
    config["discord_bot_token"] = os.getenv("DISCORD_BOT_TOKEN")

    if not config["telegram_bot_token"]:
        try:
            with open("config.json") as f:
                file_config = json.load(f)
                config["telegram_bot_token"] = file_config.get("telegram_bot_token")
                config["discord_bot_token"] = file_config.get("discord_bot_token")
        except:
            logger.error("No config found")

    return config


# ---------------- TELEGRAM COMMANDS ----------------

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    pool = context.bot_data["db_pool"]

    await db.update_user(pool, chat_id, "telegram", active=1)

    user = await db.get_user(pool, chat_id, "telegram")

    text = f"👋 Bot activo!\nThreshold: {user['threshold']}\nMin Pool: {user['min_pool']}"

    await update.message.reply_text(text)


async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    pool = context.bot_data["db_pool"]

    user = await db.get_user(pool, chat_id, "telegram")

    if user:
        text = f"📊 Settings\nThreshold: {user['threshold']}\nMin Pool: {user['min_pool']}\nActive: {user['active']}"
    else:
        text = "No estás registrado. Usa /start"

    await update.message.reply_text(text)


async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    pool = context.bot_data["db_pool"]

    await db.update_user(pool, chat_id, "telegram", active=0)

    await update.message.reply_text("🚫 Notificaciones desactivadas")


# ---------------- TELEGRAM WEBHOOK ----------------

async def tg_webhook(request):

    data = await request.json()

    update = telegram.Update.de_json(data, request.app["tg_app"].bot)

    await request.app["tg_app"].update_queue.put(update)

    return web.Response(text="OK")


# ---------------- HEALTH ----------------

async def health(request):
    return web.Response(text="OK")


# ---------------- ROOT ----------------

async def root(request):
    return web.Response(text="Bot running! ✅")


# ---------------- BATTLE CHECKER ----------------

async def battle_checker_job(app):

    pool = app["db_pool"]

    async with httpx.AsyncClient() as client:

        while True:

            try:

                battles = await shared.get_active_battles(client)

                if battles:

                    battle_ids = [b["_id"] for b in battles if "_id" in b]

                    users = await db.get_all_active_users(pool)

                    states = await db.get_battle_states(pool, battle_ids)

                    all_live_data = []

                    batch_size = 10

                    for i in range(0, len(battle_ids), batch_size):

                        ids = battle_ids[i:i+batch_size]

                        results = await shared.get_live_battle_data_batched(client, ids)

                        all_live_data.extend(zip(ids, results))

                        await asyncio.sleep(0.2)

                    notifications = shared.check_battles_for_users(users, all_live_data, states)

                    for n in notifications:

                        try:

                            if n["platform"] == "telegram":

                                await app["tg_app"].bot.send_message(
                                    chat_id=n["user_id"],
                                    text=n["message"],
                                    parse_mode="Markdown"
                                )

                            elif n["platform"] == "discord" and app.get("discord_bot_client"):

                                user = await app["discord_bot_client"].fetch_user(int(n["user_id"]))

                                await user.send(n["message"])

                            await db.update_battle_state(
                                pool,
                                n["user_id"],
                                n["platform"],
                                n["battle_id"],
                                n["side_name"],
                                n["ratio"],
                                n["pool"]
                            )

                        except Exception as e:
                            logger.error(e)

            except Exception as e:
                logger.error(f"Battle checker error: {e}")

            await asyncio.sleep(20)


# ---------------- STARTUP ----------------

async def start_background_tasks(app):

    config = load_config()

    pool = await db.get_pool()

    await db.init_db(pool)

    app["db_pool"] = pool

    # Telegram

    tg_token = config.get("telegram_bot_token")

    if tg_token:

        tg_app = ApplicationBuilder().token(tg_token).build()

        tg_app.bot_data["db_pool"] = pool

        tg_app.add_handler(CommandHandler("start", tg_start))
        tg_app.add_handler(CommandHandler("status", tg_status))
        tg_app.add_handler(CommandHandler("stop", tg_stop))

        webhook_url = "https://merc-tool-bot-up4g.onrender.com/tg_webhook"

        await tg_app.bot.set_webhook(webhook_url)

        app["tg_app"] = tg_app

    # Discord

    discord_token = config.get("discord_bot_token")

    if discord_token:

        client = discord_bot.get_bot()

        client.db_pool = pool

        app["discord_bot_client"] = client

        app["discord_task"] = asyncio.create_task(
            discord_bot.start_discord_bot(discord_token)
        )

    # Battle checker

    app["battle_checker"] = asyncio.create_task(
        battle_checker_job(app)
    )


# ---------------- CLEANUP ----------------

async def cleanup_background_tasks(app):

    if "battle_checker" in app:
        app["battle_checker"].cancel()

    if "discord_task" in app:
        app["discord_task"].cancel()

    if "db_pool" in app:
        await app["db_pool"].close()


# ---------------- INIT APP ----------------

def init_app():

    app = web.Application()

    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    app.router.add_post("/tg_webhook", tg_webhook)

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app


# ---------------- MAIN ----------------

if __name__ == "__main__":

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    app = init_app()

    port = int(os.environ.get("PORT", 10000))

    web.run_app(app, host="0.0.0.0", port=port)
