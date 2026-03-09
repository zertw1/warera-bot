# main.py
import os
import asyncio
from aiohttp import web
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application

# -----------------------
# Configuración
# -----------------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = "https://merc-tool-bot-up4g.onrender.com/"  # tu dominio

# -----------------------
# Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Bot corriendo correctamente.")

# -----------------------
# Funciones de servicios
# -----------------------
async def battle_checker():
    while True:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                # Aquí va tu lógica de battle_checker
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("Error battle_checker:", e)
            await asyncio.sleep(5)

# -----------------------
# Aiohttp app principal
# -----------------------
app = web.Application()
app["telegram_app"] = None  # para guardar la app de telegram

# Endpoint que recibe actualizaciones de Telegram
async def telegram_webhook(request):
    telegram_app: Application = request.app["telegram_app"]
    if not telegram_app:
        return web.Response(status=503)
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return web.Response(status=200)

app.router.add_post("/", telegram_webhook)

# -----------------------
# Startup y cleanup
# -----------------------
async def on_startup(app: web.Application):
    # Crear aplicación de Telegram
    telegram_app: Application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )
    telegram_app.add_handler(CommandHandler("start", start))
    # Iniciar battle_checker en background
    telegram_app.job_queue.create_task(battle_checker())
    # Configurar webhook
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    app["telegram_app"] = telegram_app
    print("Bot iniciado y webhook configurado.")

async def on_cleanup(app: web.Application):
    telegram_app: Application = app.get("telegram_app")
    if telegram_app:
        await telegram_app.stop()
        print("Bot detenido correctamente.")

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

# -----------------------
# Para correr local (opcional)
# -----------------------
if __name__ == "__main__":
    web.run_app(app, port=int(os.environ.get("PORT", 8080)))
