import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import shared_logic as shared
import database as db  # tu módulo de DB

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obtener token desde variable de entorno
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("La variable TELEGRAM_BOT_TOKEN no está definida")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pool = context.application.db_pool
    await db.update_user(pool, user_id, 'telegram', active=1)
    user = await db.get_user(pool, user_id, 'telegram')

    welcome_text = (
        "👋 Bienvenido al WarEra Battle Checker Bot!\n\n"
        "Te notificaré cuando haya batallas rentables según tus ajustes.\n\n"
        f"💰 Threshold: {user['threshold']} dinero/1k daño\n"
        f"🏦 Min Pool: {user['min_pool']} dinero\n\n"
        "Comandos:\n"
        "/threshold - Ajustar tu bounty threshold\n"
        "/minpool - Ajustar mínimo pool\n"
        "/status - Ver tus ajustes actuales\n"
        "/stop - Detener notificaciones"
    )
    await update.message.reply_text(welcome_text)


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pool = context.application.db_pool
    try:
        value = float(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usa: /threshold <valor entre 0 y 2>")
        return

    if 0 < value <= 2:
        await db.update_user(pool, user_id, 'telegram', threshold=value)
        await update.message.reply_text(f"✅ Threshold actualizado a {value}. Revisando batallas...")
        asyncio.create_task(run_immediate_check(user_id, context))
    else:
        await update.message.reply_text("❌ El valor debe estar entre 0 y 2.")


async def set_minpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pool = context.application.db_pool
    try:
        value = float(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usa: /minpool <valor entre 10 y 200>")
        return

    if 10 <= value <= 200:
        await db.update_user(pool, user_id, 'telegram', min_pool=value)
        await update.message.reply_text(f"✅ Min Pool actualizado a {value}. Revisando batallas...")
        asyncio.create_task(run_immediate_check(user_id, context))
    else:
        await update.message.reply_text("❌ El valor debe estar entre 10 y 200.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pool = context.application.db_pool
    user = await db.get_user(pool, user_id, 'telegram')
    if user:
        status_text = (
            f"📊 Tus ajustes:\n"
            f"💰 Threshold: {user['threshold']}\n"
            f"🏦 Min Pool: {user['min_pool']}\n"
            f"🔔 Notificaciones: {'Activadas' if user['active'] else 'Desactivadas'}"
        )
        await update.message.reply_text(status_text)
    else:
        await update.message.reply_text("No estás registrado. Usa /start para comenzar.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    pool = context.application.db_pool
    await db.update_user(pool, user_id, 'telegram', active=0)
    await update.message.reply_text("🚫 Notificaciones detenidas. Usa /start para reanudar.")


async def run_immediate_check(user_id, context):
    pool = context.application.db_pool
    user = await db.get_user(pool, user_id, 'telegram')
    if not user or not user['active']:
        return

    async with context.application.httpx_client as client:
        battles = await shared.get_active_battles(client)
        if not battles:
            return

        battle_ids = [b.get("_id") for b in battles if b.get("_id")]
        states = await db.get_battle_states(pool, battle_ids)

        batch_results = await shared.get_live_battle_data_batched(client, battle_ids[:10])
        all_live_data = list(zip(battle_ids[:10], batch_results))

        user_list = [{"user_id": user_id, "platform": 'telegram', "threshold": user['threshold'], "min_pool": user['min_pool']}]
        notifications = shared.check_battles_for_users(user_list, all_live_data, states)

        for n in notifications:
            try:
                await context.bot.send_message(chat_id=user_id, text=n['message'].replace("*", "**"))
                await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])
            except Exception as e:
                logger.error(f"Error notificando a {user_id}: {e}")


async def init_app():
    # Inicializa el bot y clientes compartidos
    application = ApplicationBuilder().token(TOKEN).build()

    # Guardamos DB y HTTPX en el objeto application
    application.db_pool = await db.init_pool()  # tu función de DB async
    import httpx
    application.httpx_client = httpx.AsyncClient()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("threshold", set_threshold))
    application.add_handler(CommandHandler("minpool", set_minpool))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stop", stop))

    return application


def main():
    loop = asyncio.get_event_loop()
    application = loop.run_until_complete(init_app())
    logger.info("Bot iniciado. Ejecutando polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
