import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ------------------------------
# CONFIGURACIÓN
# ------------------------------

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Debes definir la variable de entorno TELEGRAM_BOT_TOKEN")

# ------------------------------
# VARIABLES
# ------------------------------

threshold = 0.5  # Valor mínimo por defecto

# ------------------------------
# LOGS
# ------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# COMANDOS
# ------------------------------

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🤖 Bot iniciado.\n\n"
        "Comandos disponibles:\n"
        "/hunt MIN MAX — Buscar bounties en rango\n"
        "/threshold X — Ajustar mínimo automático\n"
        "/status — Ver mínimo actual"
    )

def ping(update: Update, context: CallbackContext):
    update.message.reply_text("🏓 Pong! Bot activo.")

def hunt(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        update.message.reply_text(
            "Uso correcto:\n/hunt MIN MAX\nEjemplo: /hunt 0.5 1.5"
        )
        return

    try:
        min_bounty = float(context.args[0])
        max_bounty = float(context.args[1])
    except ValueError:
        update.message.reply_text("Valores inválidos.")
        return

    # Aquí normalmente harías la lógica para tus bounties
    # Como dijiste que no necesitas ver otros jugadores, solo devolvemos un ejemplo
    update.message.reply_text(f"Bounties entre {min_bounty} y {max_bounty}:")

def set_threshold(update: Update, context: CallbackContext):
    global threshold
    if len(context.args) != 1:
        update.message.reply_text("Uso:\n/threshold 0.5")
        return

    try:
        threshold = float(context.args[0])
        update.message.reply_text(f"Nuevo mínimo automático: {threshold}")
    except ValueError:
        update.message.reply_text("Valor inválido.")

def status(update: Update, context: CallbackContext):
    update.message.reply_text(f"Mínimo automático actual: {threshold}")

# ------------------------------
# MAIN
# ------------------------------

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ping", ping))
    dp.add_handler(CommandHandler("hunt", hunt))
    dp.add_handler(CommandHandler("threshold", set_threshold))
    dp.add_handler(CommandHandler("status", status))

    # Iniciar bot
    updater.start_polling()
    logger.info("Bot iniciado correctamente")
    updater.idle()


if __name__ == "__main__":
    main()
