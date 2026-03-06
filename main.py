import json
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import database as db
import shared_logic as shared
import discord_bot
import httpx
import os
from aiohttp import web

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_config():
    """Loads the configuration from environment variables or config.json."""
    config = {}
    config["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
    config["discord_bot_token"] = os.getenv("DISCORD_BOT_TOKEN")

    if not config["telegram_bot_token"]:
        try:
            with open("config.json", "r") as f:
                json_config = json.load(f)
                config["telegram_bot_token"] = json_config.get("telegram_bot_token")
                config["discord_bot_token"] = json_config.get("discord_bot_token")
        except FileNotFoundError:
            logger.error("config.json not found. Set TELEGRAM_BOT_TOKEN and DISCORD_BOT_TOKEN environment variables.")
            return None
        except json.JSONDecodeError:
            logger.error("Could not decode config.json.")
            return None
    
    return config

# ----------------------------------
# TELEGRAM HANDLERS
# ----------------------------------
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    await db.update_user(pool, chat_id, 'telegram', active=1)
    user = await db.get_user(pool, chat_id, 'telegram')
    welcome_text = f"👋 Welcome! Your settings: Threshold={user['threshold']}, Min Pool={user['min_pool']}"
    await update.message.reply_text(welcome_text)

async def tg_set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    try:
        val = float(context.args[0])
        if 0 < val <= 2:
            await db.update_user(pool, chat_id, 'telegram', threshold=val)
            await update.message.reply_text(f"✅ Threshold updated to {val}. Checking for battles...")
        else:
            await update.message.reply_text("❌ Value must be between 0 and 2.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /threshold <value>")

async def tg_set_minpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    try:
        val = float(context.args[0])
        if 10 <= val <= 200:
            await db.update_user(pool, chat_id, 'telegram', min_pool=val)
            await update.message.reply_text(f"✅ Min Pool updated to {val}. Checking for battles...")
        else:
            await update.message.reply_text("❌ Value must be between 10 and 200.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /minpool <value>")

async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    user = await db.get_user(pool, chat_id, 'telegram')
    if user:
        status_text = f"📊 Settings: Threshold={user['threshold']}, Min Pool={user['min_pool']}, Active={user['active']}"
        await update.message.reply_text(status_text)
    else:
        await update.message.reply_text("You are not registered. /start to begin.")

async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    await db.update_user(pool, chat_id, 'telegram', active=0)
    await update.message.reply_text("🚫 Notifications stopped. /start to resume.")

# ----------------------------------
# AIOHTTP SERVER
# ----------------------------------
async def health(request):
    return web.Response(text="OK")

# ----------------------------------
# BACKGROUND TASKS
# ----------------------------------
async def battle_checker_job(app):
    async with httpx.AsyncClient() as client:
        pool = app['db_pool']
        discord_bot_client = app.get('discord_bot_client')

        while True:
            try:
                logger.info("Checking for profitable battles...")
                battles = await shared.get_active_battles(client)
                if battles:
                    battle_ids = [b.get("_id") for b in battles if b.get("_id")]
                    await db.clear_old_battles(pool, battle_ids)
                    users = await db.get_all_active_users(pool)
                    states = await db.get_battle_states(pool, battle_ids)

                    if users:
                        batch_size = 10
                        all_live_data = []
                        for i in range(0, len(battle_ids), batch_size):
                            current_batch_ids = battle_ids[i:i + batch_size]
                            batch_results = await shared.get_live_battle_data_batched(client, current_batch_ids)
                            all_live_data.extend(zip(current_batch_ids, batch_results))
                            await asyncio.sleep(0.2)

                        notifications = shared.check_battles_for_users(users, all_live_data, states)
                        for n in notifications:
                            try:
                                if n['platform'] == 'telegram':
                                    await app['tg_app'].bot.send_message(chat_id=n['user_id'], text=n['message'], parse_mode="Markdown")
                                elif n['platform'] == 'discord' and discord_bot_client:
                                    user = await discord_bot_client.fetch_user(int(n['user_id']))
                                    if user:
                                        await user.send(n['message'].replace("*", "**"))
                                await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])
                            except Exception as e:
                                logger.error(f"Failed to send {n['platform']} message: {e}")

            except Exception as e:
                logger.error(f"Error in battle checker job: {e}")
            await asyncio.sleep(20)

async def start_background_tasks(app):
    config = load_config()
    if not config:
        return

    # Init DB
    pool = await db.get_pool()
    await db.init_db(pool)
    app['db_pool'] = pool

    # Init Telegram
    tg_token = config["telegram_bot_token"]
    tg_app = ApplicationBuilder().token(tg_token).build()
    tg_app.bot_data["db_pool"] = pool
    tg_app.add_handler(CommandHandler("start", tg_start))
    tg_app.add_handler(CommandHandler("threshold", tg_set_threshold))
    tg_app.add_handler(CommandHandler("minpool", tg_set_minpool))
    tg_app.add_handler(CommandHandler("status", tg_status))
    tg_app.add_handler(CommandHandler("stop", tg_stop))
    app['tg_app'] = tg_app

    await tg_app.initialize()
    await tg_app.start()

    # Init Discord
    discord_token = config.get("discord_bot_token")
    if discord_token:
        discord_client = discord_bot.get_bot()
        discord_client.db_pool = pool
        app['discord_bot_client'] = discord_client
        app['discord_task'] = asyncio.create_task(discord_bot.start_discord_bot(discord_token))

    # Start battle checker
    app['battle_checker'] = asyncio.create_task(battle_checker_job(app))

async def cleanup_background_tasks(app):
    if 'battle_checker' in app:
        app['battle_checker'].cancel()
        try:
            await app['battle_checker']
        except asyncio.CancelledError:
            pass
    if 'discord_task' in app:
        app['discord_task'].cancel()
        try:
            await app['discord_task']
        except asyncio.CancelledError:
            pass
    if 'tg_app' in app:
        await app['tg_app'].stop()
    if 'db_pool' in app:
        await app['db_pool'].close()

# ----------------------------------
# INIT APP (para Render)
# ----------------------------------
def init_app():
    # Crear loop explícito para Python 3.14+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = web.Application()
    app.router.add_get("/health", health)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app

# ----------------------------------
# RUN LOCAL (opcional)
# ----------------------------------
if __name__ == "__main__":
    web.run_app(init_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

