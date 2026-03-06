import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Tu token tal como lo definiste en Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ------------------------------
# Handlers de comandos
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado!")

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hunt ejecutado!")

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Threshold actualizado!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Estado del bot OK!")

# ------------------------------
# Función principal
# ------------------------------
def main():
    # Crear aplicación del bot
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Agregar handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", threshold))
    app.add_handler(CommandHandler("status", status))

    # Ejecutar el bot usando polling (no webhook, evita conflictos en Render)
    app.run_polling()

if __name__ == "__main__":
    main()
