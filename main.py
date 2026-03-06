import os
import logging
import asyncio
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIGURACIÓN
# ------------------------------

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # Ahora se toma desde la variable de entorno

API_URL = "https://api-warera.vercel.app/players"
CHECK_INTERVAL = 120  # segundos

# ------------------------------
# VARIABLES
# ------------------------------

threshold = 0.5
seen_players = set()

# ------------------------------
# LOGS
# ------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------------------
# FUNCIONES
# ------------------------------

def get_players():
    try:
        r = requests.get(API_URL, timeout=10)
        if r.status_code != 200:
            print("API error:", r.status_code)
            return []

        data = r.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("players", [])
        return []
    except Exception as e:
        print("Error consultando API:", e)
        return []

def parse_bounty(player):
    bounty = player.get("bounty", 0)
    try:
        bounty = float(bounty)
    except:
        bounty = 0
    return bounty

# ------------------------------
# ESCÁNER AUTOMÁTICO
# ------------------------------

async def scanner(context: ContextTypes.DEFAULT_TYPE):
    global threshold
    players = get_players()

    for player in players:
        name = player.get("name", "Unknown")
        bounty = parse_bounty(player)

        if bounty >= threshold:
            key = f"{name}-{bounty}"
            if key not in seen_players:
                seen_players.add(key)
                message = (
                    f"🎯 Bounty detectado\n\n"
                    f"Jugador: {name}\n"
                    f"Bounty: {bounty}"
                )
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=message
                )

# ------------------------------
# COMANDOS
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot de bounties iniciado.\n\n"
        "Comandos:\n"
        "/hunt MIN MAX\n"
        "/threshold X\n"
        "/ping"
    )
    context.job_queue.run_repeating(
        scanner,
        interval=CHECK_INTERVAL,
        first=10,
        chat_id=update.effective_chat.id
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot activo.")

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Uso correcto:\n"
            "/hunt MIN MAX\n\n"
            "Ejemplo:\n"
            "/hunt 0.5 1.5"
        )
        return
    try:
        min_bounty = float(context.args[0])
        max_bounty = float(context.args[1])
    except:
        await update.message.reply_text("Valores inválidos.")
        return

    players = get_players()
    encontrados = []

    for player in players:
        name = player.get("name", "Unknown")
        bounty = parse_bounty(player)
        if min_bounty <= bounty <= max_bounty:
            encontrados.append(f"{name} — {bounty}")

    if not encontrados:
        await update.message.reply_text("No hay bounties en ese rango.")
        return

    msg = "🎯 Bounties encontrados:\n\n"
    for p in encontrados[:30]:
        msg += p + "\n"

    await update.message.reply_text(msg)

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global threshold
    if len(context.args) != 1:
        await update.message.reply_text("Uso:\n/threshold 0.5")
        return
    try:
        threshold = float(context.args[0])
        await update.message.reply_text(f"Nuevo mínimo automático: {threshold}")
    except:
        await update.message.reply_text("Valor inválido.")

# ------------------------------
# MAIN
# ------------------------------

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", set_threshold))

    # Borra webhook previo si existe
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print("No se pudo eliminar webhook:", e)

    print("Bot iniciado correctamente")
    await app.run_polling()

# ------------------------------

if __name__ == "__main__":
    # Evita error de loop corriendo en algunos entornos
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())




