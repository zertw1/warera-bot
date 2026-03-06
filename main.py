import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from shared_logic import get_active_battles, get_live_battle_data_batched, check_battles_for_users

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# TOKEN del bot (debe estar en Render como variable de entorno)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Simulación de usuarios registrados para recibir notificaciones
USERS = [
    {
        "user_id": 123456789,  # Reemplazar con tu Telegram user_id real
        "platform": "PC",
        "threshold": 1000,
        "min_pool": 5000
    }
]

# Estado de batallas previamente notificadas
battle_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado! Recibirás notificaciones de WarEra.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Usuarios registrados: {len(USERS)}")

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando batallas activas...")
    import httpx

    async with httpx.AsyncClient() as client:
        active_battles = await get_active_battles(client)
        battle_ids = [b.get("battleId") for b in active_battles]
        live_data_list = await get_live_battle_data_batched(client, battle_ids)
        all_live_data = list(zip(battle_ids, live_data_list))
        notifications = check_battles_for_users(USERS, all_live_data, battle_states)
        
        for note in notifications:
            try:
                await context.bot.send_message(
                    chat_id=note["user_id"],
                    text=note["message"],
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                # Guardamos el estado notificado
                battle_states[(note["user_id"], note["platform"], note["battle_id"], note["side_name"])] = {
                    "money_per_1k": note["ratio"],
                    "money_pool": note["pool"]
                }
            except Exception as e:
                logger.error(f"Error enviando notificación a {note['user_id']}: {e}")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("hunt", hunt))
    
    # Ejecutar el bot de forma async
    await app.run_polling()

if __name__ == "__main__":
    # Evitar conflictos con event loop ya corriendo
    try:
        asyncio.run(main())
    except RuntimeError as e:
        logger.warning(f"Event loop already running: {e}")
        loop = asyncio.get_event_loop()
        loop.create_task(main())
