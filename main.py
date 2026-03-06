# main.py
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")

# Eliminar webhook activo para evitar conflictos con polling
bot = Bot(TOKEN)
bot.delete_webhook()

# -----------------------------
# HANDLERS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola! Bot activado. Usa /hunt, /threshold o /status.")

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aquí va la lógica de tu "cazar"
    await update.message.reply_text("Hunting... 🏹")

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aquí va la lógica de tu "umbral"
    await update.message.reply_text("Threshold ajustado!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aquí va la lógica de tu "estado"
    await update.message.reply_text("Estado actual: todo en orden ✅")

# -----------------------------
# MAIN
# -----------------------------
def main():
    # Crear la app
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", threshold))
    app.add_handler(CommandHandler("status", status))

    # Iniciar polling
    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
