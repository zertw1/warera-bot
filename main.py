import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ------------------------------
# CONFIGURACIÓN
# ------------------------------

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # Se toma desde el environment

# ------------------------------
# VARIABLES
# ------------------------------

threshold = 0.5

# ------------------------------
# LOGS
# ------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------------------
# COMANDOS
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot iniciado.\n\n"
        "Comandos disponibles:\n"
        "/hunt MIN MAX — calcula tus valores\n"
        "/threshold X — establece el mínimo de referencia\n"
        "/status — muestra estado y threshold actual"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot activo.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot activo.\nThreshold actual: {threshold}")

# ------------------------------
# HUNT POR RANGO
# ------------------------------

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Uso correcto:\n/hunt MIN MAX\nEjemplo: /hunt 0.5 2.0"
        )
        return

    try:
        min_val = float(context.args[0])
        max_val = float(context.args[1])
    except:
        await update.message.reply_text("Valores inválidos.")
        return

    resultados = []
    for val in [min_val, max_val]:
        if val >= threshold:
            resultados.append(val)

    if resultados:
        await update.message.reply_text(f"Valores sobre el threshold: {resultados}")
    else:
        await update.message.reply_text("Ningún valor supera el threshold.")

# ------------------------------
# CAMBIAR THRESHOLD
# ------------------------------

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global threshold
    if len(context.args) != 1:
        await update.message.reply_text("Uso: /threshold 0.5")
        return
    try:
        threshold = float(context.args[0])
        await update.message.reply_text(f"✅ Nuevo threshold: {threshold}")
    except:
        await update.message.reply_text("Valor inválido.")

# ------------------------------
# MAIN
# ------------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("threshold", set_threshold))

    # iniciar bot
    print("Bot iniciado correctamente")
    app.run_polling()

# ------------------------------

if __name__ == "__main__":
    main()
