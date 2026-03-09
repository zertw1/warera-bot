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
WEBHOOK_URL = "https://merc-tool-bot-up4g.onrender.com/"  # tu dominio en Render

# -----------------------
# Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Bot corriendo correctamente.")

# -----------------------
# Funciones de servicios
# -----------------------
async def battle_checker():
    # Ejemplo de loop periódico
    while True:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                # Aquí tu lógica de battle_checker
                # await client.get("https://alguna_api.com")
                await asyncio.sleep(60)  # cada 1 minuto
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("Error battle_checker:", e)
            await asyncio.sleep(5)

# -----------------------
# Inicialización de aplicación
# -----------------------
async def init_bot():
    application: Application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    # Registrar handlers
    application.add_handler(CommandHandler("start", start))

    # Iniciar battle_checker en segundo plano
    application.job_queue.create_task(battle_checker())

    # Configurar webhook
    await application.bot.set_webhook(WEBHOOK_URL)

    return application

# -----------------------
# Aiohttp app
# -----------------------
app = web.Application()

# Guardamos la aplicación de Telegram en el app de aiohttp
app["telegram_app"] = None

async def on_startup(app: web.Application):
    app["telegram_app"] = await init_bot()
    print("Bot iniciado y webhook configurado.")

async def on_cleanup(app: web.Application):
    if app.get("telegram_app"):
        await app["telegram_app"].stop()
        print("Bot detenido correctamente.")

# Conectar los eventos
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

# Endpoint que recibe actualizaciones de Telegram
async def telegram_webhook(request):
    telegram_app: Application = request.app["telegram_app"]
    if not telegram_app:
        return web.Response(status=503)

    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return web.Response(status=200)

# Ruta principal del webhook
app.router.add_post("/", telegram_webhook)

# -----------------------
# Para correr localmente (opcional)
# -----------------------
if __name__ == "__main__":
    web.run_app(app, port=int(os.environ.get("PORT", 8080)))
