import asyncio
import logging
import os
import httpx
from aiohttp import web
from telegram.ext import Application, CommandHandler

from db import init_db, get_db_pool
from commands import start, help_command, set_threshold, set_min_pool
from shared_logic import get_active_battles, get_live_battle_data_batched, check_battles_for_users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

battle_states = {}

async def battle_checker(app):
    logger.info("Battle checker started")

    pool = get_db_pool()

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                battles = await get_active_battles(client)

                if not battles:
                    await asyncio.sleep(30)
                    continue

                battle_ids = [b["id"] for b in battles]

                live_data = await get_live_battle_data_batched(client, battle_ids)

                battle_data = list(zip(battle_ids, live_data))

                async with pool.acquire() as conn:
                    users = await conn.fetch(
                        "SELECT user_id, platform, threshold, min_pool FROM users"
                    )

                users = [dict(u) for u in users]

                notifications = check_battles_for_users(
                    users,
                    battle_data,
                    battle_states
                )

                for notif in notifications:

                    await app["bot"].bot.send_message(
                        chat_id=notif["user_id"],
                        text=notif["message"],
                        parse_mode="Markdown"
                    )

                    state_key = (
                        notif["user_id"],
                        notif["platform"],
                        notif["battle_id"],
                        notif["side_name"]
                    )

                    battle_states[state_key] = {
                        "money_per_1k": notif["ratio"],
                        "money_pool": notif["pool"]
                    }

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Battle checker error: {e}")
                await asyncio.sleep(30)

async def start_background_tasks(app):
    app["battle_checker"] = asyncio.create_task(battle_checker(app))

async def cleanup_background_tasks(app):
    app["battle_checker"].cancel()
    await app["battle_checker"]

async def health(request):
    return web.Response(text="OK")

async def init_app():

    await init_db()

    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("set_threshold", set_threshold))
    telegram_app.add_handler(CommandHandler("set_min_pool", set_min_pool))

    await telegram_app.initialize()
    await telegram_app.start()

    app = web.Application()

    app["bot"] = telegram_app

    app.router.add_get("/health", health)

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app
