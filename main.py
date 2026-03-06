import os
import logging
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIG
# ------------------------------

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BATTLES_API = "https://api2.warera.io/trpc/battle.getBattles?input=%7B%22isActive%22%3Atrue%7D"

CHECK_INTERVAL = 60

threshold = 0.5
seen_players = set()

# ------------------------------
# LOGGING
# ------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------------------
# API
# ------------------------------

def get_active_battles():

    try:

        r = requests.get(BATTLES_API, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        if "result" in data:
            return data["result"]["data"]["json"]

        return []

    except Exception as e:
        print("API error:", e)
        return []

# ------------------------------
# SCANNER
# ------------------------------

async def scanner(context: ContextTypes.DEFAULT_TYPE):

    global threshold

    battles = get_active_battles()

    for battle in battles:

        players = battle.get("players", [])

        for player in players:

            name = player.get("username", "Unknown")
            bounty = float(player.get("bounty", 0))

            if bounty >= threshold:

                key = f"{name}-{bounty}"

                if key not in seen_players:

                    seen_players.add(key)

                    message = (
                        f"🎯 BOUNTY DETECTADO\n\n"
                        f"Jugador: {name}\n"
                        f"Bounty: {bounty}"
                    )

                    await context.bot.send_message(
                        chat_id=context.job.chat_id,
                        text=message
                    )

# ------------------------------
# COMMANDS
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 WarEra Bounty Bot PRO\n\n"
        "Comandos:\n"
        "/hunt min max\n"
        "/threshold x\n"
        "/ping"
    )

    context.job_queue.run_repeating(
        scanner,
        interval=CHECK_INTERVAL,
        first=10,
        chat_id=update.effective_chat.id
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🏓 Bot activo")


async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2:

        await update.message.reply_text(
            "Uso:\n/hunt 0.5 2"
        )
        return

    try:

        min_b = float(context.args[0])
        max_b = float(context.args[1])

    except:

        await update.message.reply_text("Valores inválidos")
        return

    battles = get_active_battles()

    encontrados = []

    for battle in battles:

        players = battle.get("players", [])

        for player in players:

            name = player.get("username", "Unknown")
            bounty = float(player.get("bounty", 0))

            if min_b <= bounty <= max_b:

                encontrados.append(f"{name} — {bounty}")

    if not encontrados:

        await update.message.reply_text("No hay bounties en ese rango")
        return

    msg = "🎯 Bounties encontrados\n\n"

    for p in encontrados[:30]:
        msg += p + "\n"

    await update.message.reply_text(msg)


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global threshold

    if len(context.args) != 1:

        await update.message.reply_text("/threshold 0.5")
        return

    try:

        threshold = float(context.args[0])

        await update.message.reply_text(
            f"Nuevo mínimo automático: {threshold}"
        )

    except:

        await update.message.reply_text("Valor inválido")

# ------------------------------
# MAIN
# ------------------------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", set_threshold))

    print("Bot iniciado")

    app.run_polling()


if __name__ == "__main__":

    main()


