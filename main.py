import logging
import asyncio
import os
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIG
# ------------------------------

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

API_URL = "https://api-warera.vercel.app/players"

CHECK_INTERVAL = 120

# ------------------------------
# VARIABLES
# ------------------------------

threshold = 0.5
seen_players = set()

# ------------------------------
# LOGS
# ------------------------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------------------
# API
# ------------------------------

def get_players():

    try:

        r = requests.get(API_URL, timeout=10)

        if r.status_code != 200:
            logging.error(f"API error {r.status_code}")
            return []

        data = r.json()

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("players", [])

        return []

    except Exception as e:

        logging.error(f"API request failed: {e}")
        return []


def parse_bounty(player):

    bounty = player.get("bounty", 0)

    try:
        return float(bounty)
    except:
        return 0


# ------------------------------
# SCANNER
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

                try:

                    await context.bot.send_message(
                        chat_id=context.job.chat_id,
                        text=message
                    )

                except Exception as e:

                    logging.error(f"Telegram send error: {e}")


# ------------------------------
# COMANDOS
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot WarEra PRO iniciado\n\n"
        "Comandos:\n"
        "/hunt MIN MAX\n"
        "/threshold X\n"
        "/top\n"
        "/scan\n"
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


# ------------------------------
# SCAN MANUAL
# ------------------------------

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    players = get_players()

    total = len(players)

    await update.message.reply_text(
        f"🔎 Escaneo manual completado\n\n"
        f"Jugadores analizados: {total}"
    )


# ------------------------------
# HUNT
# ------------------------------

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2:

        await update.message.reply_text(
            "Uso:\n/hunt MIN MAX\n\n"
            "Ejemplo:\n"
            "/hunt 0.5 2"
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

            encontrados.append((name, bounty))

    if not encontrados:

        await update.message.reply_text("No hay bounties en ese rango.")
        return

    encontrados.sort(key=lambda x: x[1], reverse=True)

    msg = "🎯 Bounties encontrados:\n\n"

    for name, bounty in encontrados[:30]:

        msg += f"{name} — {bounty}\n"

    await update.message.reply_text(msg)


# ------------------------------
# TOP BOUNTIES
# ------------------------------

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    players = get_players()

    lista = []

    for player in players:

        name = player.get("name", "Unknown")
        bounty = parse_bounty(player)

        lista.append((name, bounty))

    lista.sort(key=lambda x: x[1], reverse=True)

    msg = "🏆 Top bounties:\n\n"

    for name, bounty in lista[:15]:

        msg += f"{name} — {bounty}\n"

    await update.message.reply_text(msg)


# ------------------------------
# THRESHOLD
# ------------------------------

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global threshold

    if len(context.args) != 1:

        await update.message.reply_text("Uso:\n/threshold 0.5")
        return

    try:

        threshold = float(context.args[0])

        await update.message.reply_text(
            f"Nuevo mínimo automático: {threshold}"
        )

    except:

        await update.message.reply_text("Valor inválido.")


# ------------------------------
# MAIN
# ------------------------------

async def main():

    if not TOKEN:

        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", set_threshold))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("scan", scan))

    await app.bot.delete_webhook(drop_pending_updates=True)

    print("Bot WarEra PRO iniciado")

    await app.run_polling()


# ------------------------------

if __name__ == "__main__":

    asyncio.run(main())

