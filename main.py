import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, webhook

# ------------------------------
# CONFIG
# ------------------------------
TOKEN = os.environ["TELEGRAM_TOKEN"]  # variable de entorno en Render
PORT = int(os.environ.get("PORT", 10000))
APP_URL = os.environ.get("APP_URL", "https://TU_APP.onrender.com")  # la URL de tu web service

# ------------------------------
# HANDLERS
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activado!")

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Cazando!")

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Threshold ajustado.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Estado del bot: OK")

# ------------------------------
# MAIN
# ------------------------------
def main():
    app = Application.builder().token(TOKEN).build()

    # registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", threshold))
    app.add_handler(CommandHandler("status", status))

    # iniciar webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{APP_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
