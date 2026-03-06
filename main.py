import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# Configuración del Bot
# ------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("No se encontró la variable de entorno TELEGRAM_BOT_TOKEN")

# ------------------------------
# Variables de ejemplo para estado
# ------------------------------
bot_state = {
    "threshold": 50,
    "hunts_done": 0
}

# ------------------------------
# Handlers de comandos
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Bot iniciado!\n"
        "Usa /hunt para cazar, /threshold para ver/modificar el umbral, /status para ver el estado."
    )

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_state["hunts_done"] += 1
    await update.message.reply_text(f"Hunt realizada! Total de hunts: {bot_state['hunts_done']}")

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si el usuario envía un argumento, lo tomamos como nuevo threshold
    if context.args:
        try:
            new_value = int(context.args[0])
            bot_state["threshold"] = new_value
            await update.message.reply_text(f"Threshold actualizado a {new_value}")
        except ValueError:
            await update.message.reply_text("Debes enviar un número válido.")
    else:
        await update.message.reply_text(f"El threshold actual es {bot_state['threshold']}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hunts realizadas: {bot_state['hunts_done']}\n"
        f"Threshold actual: {bot_state['threshold']}"
    )

# ------------------------------
# Inicialización del Bot
# ------------------------------
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", threshold))
    app.add_handler(CommandHandler("status", status))

    print("Bot iniciado. Esperando comandos...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
