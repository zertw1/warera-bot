import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIGURACIÓN
# ------------------------------
TOKEN = os.environ["TELEGRAM_TOKEN"]  # asegurate de poner tu token en Render como variable de entorno
PORT = int(os.environ.get("PORT", 10000))  # Render asigna un puerto automáticamente

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
# APLICACIÓN
# ------------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", threshold))
    app.add_handler(CommandHandler("status", status))

    # Ejecutar con webhook en Render
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://TU_APP.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
