import os
import json
import asyncio
import logging
from aiohttp import web
import httpx

# Telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Tu código
import database as db
import shared_logic as shared
import discord_bot

# Config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Cargar configuración ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")


# ---------- Telegram Handlers ----------
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    pool = context.bot_data["db_pool"]
    await db.update_user(pool, chat_id, 'telegram', active=1)
    user = await db.get_user(pool, chat_id, 'telegram')
    await update.message.reply_text(f"👋 Bot funcionando! Threshold={user['threshold']}, Min Pool={user['min_pool']}")


# ---------- Función para recibir webhook ----------
async def tg_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, request.app['tg_app'].bot)
        await request.app['tg_app'].update_queue.put(update)
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
    return web.Response(text="OK")


# ---------- Health check y root ----------
async def root(request):
    return web.Response(text="Bot running! ✅")

async def health(request):
    return web.Response(text="OK")


# ---------- Inicialización ----------
async def start_background_tasks(app):
    # DB
    pool = await db.get_pool()
    app['db_pool'] = pool
    await db.init_db(pool)

    # Telegram
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    tg_app.bot_data["db_pool"] = pool
    tg_app.add_handler(CommandHandler("start", tg_start))
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    app['tg_app'] = tg_app

    # Configurar webhook
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/tg_webhook"
    await tg_app.bot.set_webhook(webhook_url)
    logger.info(f"Telegram webhook set: {webhook_url}")

    # Discord
    if DISCORD_TOKEN:
        discord_client = discord_bot.get_bot()
        discord_client.db_pool = pool
        app['discord_client'] = discord_client
        app['discord_task'] = asyncio.create_task(discord_bot.start_discord_bot(DISCORD_TOKEN))

    # Battle checker
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
        await app['tg_app'].updater.stop()
        await app['tg_app'].stop()
    if 'db_pool' in app:
        await app['db_pool'].close()


# ---------- Battle checker job ----------
async def battle_checker_job(app):
    pool = app['db_pool']
    async with httpx.AsyncClient() as client:
        app['httpx_client'] = client
        discord_client = app.get('discord_client')
        if discord_client:
            discord_client.httpx_client = client
        while True:
            try:
                battles = await shared.get_active_battles(client)
                if not battles:
                    await asyncio.sleep(20)
                    continue
                battle_ids = [b.get("_id") for b in battles if b.get("_id")]
                await db.clear_old_battles(pool, battle_ids)
                users = await db.get_all_active_users(pool)
                states = await db.get_battle_states(pool, battle_ids)

                # Check battles
                all_live_data = []
                batch_size = 10
                for i in range(0, len(battle_ids), batch_size):
                    batch_ids = battle_ids[i:i+batch_size]
                    batch_results = await shared.get_live_battle_data_batched(client, batch_ids)
                    all_live_data.extend(zip(batch_ids, batch_results))
                    await asyncio.sleep(0.2)

                notifications = shared.check_battles_for_users(users, all_live_data, states)

                # Broadcast notifications
                for n in notifications:
                    try:
                        if n['platform'] == 'telegram':
                            await app['tg_app'].bot.send_message(chat_id=n['user_id'], text=n['message'], parse_mode="Markdown")
                        elif n['platform'] == 'discord' and discord_client:
                            user = await discord_client.fetch_user(int(n['user_id']))
                            if user:
                                await user.send(n['message'].replace("*","**"))
                        await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])
                    except Exception as e:
                        logger.error(f"Error notificando {n['platform']} a {n['user_id']}: {e}")

            except Exception as e:
                logger.error(f"Error en battle checker: {e}")
            await asyncio.sleep(20)


# ---------- Crear app ----------
def init_app():
    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    app.router.add_post("/tg_webhook", tg_webhook)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app


# ---------- Run ----------
if __name__ == "__main__":
    import sys
    port = int(os.environ.get("PORT", 10000))
    web.run_app(init_app(), host="0.0.0.0", port=port)
