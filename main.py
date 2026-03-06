import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ----------------------------
# CONFIG
# ----------------------------

API_URL = "https://api.war-era.com/leaderboard"
PRO_THRESHOLD = 500000
DEFAULT_MIN = 0
DEFAULT_MAX = 10000000000

# ----------------------------
# BOUNTY DETECTION
# ----------------------------

def calculate_bounty(player):
    bounty = player.get("bounty", 0)

    # fallback por bug común del API
    if bounty == 0:
        kills = player.get("kills", 0)
        deaths = player.get("deaths", 1)
        bounty = kills * 10000 - deaths * 5000

    if bounty < 0:
        bounty = 0

    return bounty

# ----------------------------
# FETCH DATA
# ----------------------------

def get_players():

    try:
        r = requests.get(API_URL, timeout=10)
        data = r.json()
        return data.get("players", [])
    except:
        return []

# ----------------------------
# COMMANDS
# ----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bounty Hunter Bot PRO\n\n"
        "/hunt min max\n"
        "ejemplo:\n"
        "/hunt 500000 2000000"
    )

# ----------------------------

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    players = get_players()

    if not players:
        await update.message.reply_text("⚠️ No se pudo obtener la data")
        return

    # rango por defecto
    min_bounty = DEFAULT_MIN
    max_bounty = DEFAULT_MAX

    if len(context.args) == 2:
        try:
            min_bounty = int(float(context.args[0]) * 1000000)
            max_bounty = int(float(context.args[1]) * 1000000)
        except:
            pass

    targets = []

    for p in players:

        bounty = calculate_bounty(p)

        if min_bounty <= bounty <= max_bounty:

            targets.append({
                "name": p.get("name","Unknown"),
                "bounty": bounty,
                "server": p.get("server","?")
            })

    if not targets:
        await update.message.reply_text("❌ No hay objetivos en ese rango")
        return

    targets.sort(key=lambda x: x["bounty"], reverse=True)

    msg = "🎯 Targets encontrados\n\n"

    for t in targets[:10]:

        bounty_m = round(t["bounty"]/1000000,2)

        msg += f"{t['name']} — {bounty_m}M — {t['server']}\n"

    await update.message.reply_text(msg)

# ----------------------------
# PRO SCANNER
# ----------------------------

async def pro_scan(context: ContextTypes.DEFAULT_TYPE):

    players = get_players()

    if not players:
        return

    targets = []

    for p in players:

        bounty = calculate_bounty(p)

        if bounty >= PRO_THRESHOLD:

            targets.append({
                "name": p.get("name","Unknown"),
                "bounty": bounty,
                "server": p.get("server","?")
            })

    if not targets:
        return

    targets.sort(key=lambda x: x["bounty"], reverse=True)

    msg = "🚨 PRO BOUNTY DETECTED\n\n"

    for t in targets[:5]:

        bounty_m = round(t["bounty"]/1000000,2)

        msg += f"{t['name']} — {bounty_m}M — {t['server']}\n"

    for chat_id in context.bot_data.get("subscribers", []):
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except:
            pass

# ----------------------------
# SUBSCRIBE
# ----------------------------

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if "subscribers" not in context.bot_data:
        context.bot_data["subscribers"] = []

    if chat_id not in context.bot_data["subscribers"]:
        context.bot_data["subscribers"].append(chat_id)

    await update.message.reply_text("✅ Activado PRO scanner")

# ----------------------------
# MAIN
# ----------------------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("subscribe", subscribe))

    job_queue = app.job_queue
    job_queue.run_repeating(pro_scan, interval=60, first=10)

    print("BOT RUNNING")

    app.run_polling()

# ----------------------------

if __name__ == "__main__":
    main()

