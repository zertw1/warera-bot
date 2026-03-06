import json
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import database as db
import shared_logic as shared
import discord_bot
import httpx
from aiohttp import web
import telegram

# ---------------- Logging ----------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Config Loader ----------------
def load_config():
    config = {}
    config["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
    config["discord_bot_token"] = os.getenv("DISCORD_BOT_TOKEN")
    if not config["telegram_bot_token"]:
        try:
            with open("config.json", "r") as f:
                json_config = json.load(f)
                config["telegram_bot_token"] = json_config.get("telegram_bot_token")
                config["discord_bot_token"] = json_config.get("discord_bot_token")
        except Exception:
            logger.error("Set TELEGRAM_BOT_TOKEN and DISCORD_BOT_TOKEN environment variables or use config.json")
            return None
    return config

# ---------------- Telegram Handlers ----------------
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
            await run_tg_immediate_check(chat_id, context)
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
            await run_tg_immediate_check(chat_id, context)
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

async def run_tg_immediate_check(chat_id, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data["db_pool"]
    user = await db.get_user(pool, chat_id, 'telegram')
    if not user or not user['active']: return
    
    async with httpx.AsyncClient() as client:
        battles = await shared.get_active_battles(client)
        if not battles: return
        
        battle_ids = [b.get("_id") for b in battles if b.get("_id")]
        states = await db.get_battle_states(pool, battle_ids)

        batch_results = await shared.get_live_battle_data_batched(client, battle_ids[:10])
        all_live_data = list(zip(battle_ids[:10], batch_results))
        user_list = [{"user_id": chat_id, "platform": 'telegram', "threshold": user['threshold'], "min_pool": user['min_pool']}]
        
        notifications = shared.check_battles_for_users(user_list, all_live_data, states)
        for n in notifications:
            await context.bot.send_message(chat_id=n['user_id'], text=n['message'], parse_mode="Markdown")
            await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])

# ---------------- Broadcast Notifications ----------------
async def broadcast_notifications(app, notifications):
    pool = app['db_pool']
    for n in notifications:
        try:
            if n['platform'] == 'telegram':
                await app['tg_app'].bot.send_message(chat_id=n['user_id'], text=n['message'], parse_mode="Markdown")
            elif n['platform'] == 'discord' and app.get('discord_bot_client'):
                discord_user = await app['discord_bot_client'].fetch_user(int(n['user_id']))
                if discord_user:
                    await discord_user.send(n['message'].replace("*", "**"))
            await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])
        except Exception as e:
            logger.error(f"Failed to send {n['platform']} message to {n['user_id']}: {e}")

# ---------------- Battle Checker Job ----------------
async def battle_checker_job(app):
    async with httpx.AsyncClient() as client:
        app['httpx_client'] = client
        pool = app['db_pool']
        discord_bot_client = app.get('discord_bot_client')
        if discord_bot_client:
            discord_bot_client.httpx_client = client

        while True:
            try:
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
                        await broadcast_notifications(app, notifications)
            except Exception as e:
                logger.error(f"Error in battle checker job: {e}")
            await asyncio.sleep(20)

# ---------------- Health Check ----------------
async def health(request):
    return web.Response(text="OK")

# ---------------- Root for browser ----------------
async def root(request):
    return web.Response(text="Bot running! ✅")

# ---------------- Telegram Webhook ----------------
async def tg_webhook(request):
    data = await request.json()
    update = telegram.Update.de_json(data, request.app['tg_app'].bot)
    await request.app['tg_app'].update_queue.put(update)
    return web.Response(text="OK")

# ---------------- Startup ----------------
async def start_background_tasks(app):
    config = load_config()
    if not config:
        return

    pool = await db.get_pool()
    app['db_pool'] = pool
    await db.init_db(pool)

    tg_token = config.get("telegram_bot_token")
    if tg_token:
        tg_application = ApplicationBuilder().token(tg_token).build()
        tg_application.bot_data["db_pool"] = pool
        tg_application.add_handler(CommandHandler("start", tg_start))
        tg_application.add_handler(CommandHandler("threshold", tg_set_threshold))
        tg_application.add_handler(CommandHandler("minpool", tg_set_minpool))
        tg_application.add_handler(CommandHandler("status", tg_status))
        tg_application.add_handler(CommandHandler("stop", tg_stop))
        WEBHOOK_URL = f"https://merc-tool-bot-up4g.onrender.com/tg_webhook"
        await tg_application.bot.set_webhook(WEBHOOK_URL)
        app['tg_app'] = tg_application

    discord_token = config.get("discord_bot_token")
    if discord_token:
        discord_bot_client = discord_bot.get_bot()
        discord_bot_client.db_pool = pool
        app['discord_bot_client'] = discord_bot_client
        app['discord_task'] = asyncio.create_task(discord_bot.start_discord_bot(discord_token))

    app['battle_checker'] = asyncio.create_task(battle_checker_job(app))

# ---------------- Cleanup ----------------
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

# ---------------- Init App ----------------
def init_app():
    app = web.Application()
    app.router.add_get("/", root)  # <-- raíz para navegador
    app.router.add_get("/health", health)
    app.router.add_post("/tg_webhook", tg_webhook)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app

# ---------------- Entrypoint para Python 3.14 ----------------
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = init_app()
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
