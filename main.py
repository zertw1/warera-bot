import logging
import requests
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# -----------------------------
# CONFIG
# -----------------------------

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BATTLES_API = "https://api2.warera.io/trpc/battle.getBattles?input=%7B%22isActive%22%3Atrue%7D"
LIVE_API = "https://api2.warera.io/trpc/battle.getLiveBattleData"

SCAN_INTERVAL = 120

threshold = 0.5
seen_players = set()

# -----------------------------
# LOGS
# -----------------------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------------
# API
# -----------------------------

def get_battles():

    try:

        r = requests.get(BATTLES_API, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        battles = data["result"]["data"]["json"]

        return battles

    except Exception as e:

        print("API error:", e)
        return []

# -----------------------------
# PARSE BOUNTY
# -----------------------------

def parse_bounty(player):

    try:

        bounty = float(player.get("bounty", 0))

    except:

        bounty = 0

    return bounty

# -----------------------------
# SCANNER
# -----------------------------

async def scanner(context: ContextTypes.DEFAULT_TYPE):

    global threshold

    battles = get_battles()

    for battle in battles:

        players = battle.get("players", [])

        for p in players:

            name = p.get("name", "Unknown")
            bounty = parse_bounty(p)

            if bounty >= threshold:

                key = f"{name}-{bounty}"

                if key not in seen_players:

                    seen_players.add(key)

                    msg = (
                        "🎯 Bounty detectado\n\n"
                        f"Jugador: {name}\n"
                        f"Bounty: {bounty}"
                    )

                    await context.bot.send_message(
                        chat_id=context.job.chat_id,
                        text=msg
                    )

# -----------------------------
# START
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 WarEra Bounty Bot PRO\n\n"
        "Comandos:\n"
        "/hunt MIN MAX\n"
        "/threshold X\n"
        "/top\n"
        "/live\n"
        "/ping"
    )

    context.job_queue.run_repeating(
        scanner,
        interval=SCAN_INTERVAL,
        first=10,
        chat_id=update.effective_chat.id
    )

# -----------------------------
# PING
# -----------------------------

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🏓 Pong")

# -----------------------------
# HUNT
# -----------------------------

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2:

        await update.message.reply_text(
            "Uso:\n/hunt MIN MAX\n\nEjemplo:\n/hunt 0.5 2"
        )
        return

    try:

        min_b = float(context.args[0])
        max_b = float(context.args[1])

    except:

        await update.message.reply_text("Valores inválidos")
        return

    battles = get_battles()

    results = []

    for battle in battles:

        players = battle.get("players", [])

        for p in players:

            name = p.get("name")
            bounty = parse_bounty(p)

            if min_b <= bounty <= max_b:

                results.append(f"{name} — {bounty}")

    if not results:

        await update.message.reply_text("No hay bounties en ese rango")
        return

    msg = "🎯 Bounties encontrados\n\n"

    for r in results[:30]:
        msg += r + "\n"

    await update.message.reply_text(msg)

# -----------------------------
# THRESHOLD
# -----------------------------

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global threshold

    if len(context.args) != 1:

        await update.message.reply_text(
            "Uso:\n/threshold 0.5"
        )
        return

    try:

        threshold = float(context.args[0])

        await update.message.reply_text(
            f"Nuevo mínimo automático: {threshold}"
        )

    except:

        await update.message.reply_text("Valor inválido")

# -----------------------------
# TOP BOUNTIES
# -----------------------------

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    battles = get_battles()

    players = []

    for battle in battles:

        for p in battle.get("players", []):

            name = p.get("name")
            bounty = parse_bounty(p)

            players.append((name, bounty))

    players.sort(key=lambda x: x[1], reverse=True)

    msg = "🏆 Top Bounties\n\n"

    for name, bounty in players[:10]:

        msg += f"{name} — {bounty}\n"

    await update.message.reply_text(msg)

# -----------------------------
# LIVE PLAYERS
# -----------------------------

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):

    battles = get_battles()

    msg = "⚔️ Jugadores peleando ahora\n\n"

    count = 0

    for battle in battles:

        players = battle.get("players", [])

        for p in players:

            name = p.get("name")
            bounty = parse_bounty(p)

            msg += f"{name} — {bounty}\n"
            count += 1

            if count > 20:
                break

    if count == 0:

        await update.message.reply_text("No hay batallas activas")
        return

    await update.message.reply_text(msg)

# -----------------------------
# MAIN
# -----------------------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", set_threshold))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("live", live))

    print("Bot iniciado")

    app.run_polling()

# -----------------------------

if __name__ == "__main__":

    main()



