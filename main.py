# main.py
import asyncio
import logging
import os
import discord
from discord.ext import commands
import database as db  # tu módulo DB
import shared_logic as shared  # tu lógica de batallas

# ------------------------------
# Configuración básica
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID del bot (solo para logs)
DISCORD_BOT_ID = 1479229834340339712

# Token seguro desde variable de entorno
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    logger.error("ERROR: la variable de entorno DISCORD_BOT_TOKEN no está definida")
    exit(1)

# ------------------------------
# Inicializar bot
# ------------------------------
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# Eventos
# ------------------------------
@bot.event
async def on_ready():
    logger.info(f"Bot conectado como {bot.user} (ID configurada: {DISCORD_BOT_ID})")

# ------------------------------
# Comandos básicos
# ------------------------------
@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

@bot.command()
async def status(ctx):
    await ctx.send(f"Bot activo ✅ (ID: {DISCORD_BOT_ID})")

# ------------------------------
# Tarea de notificaciones
# ------------------------------
async def battle_checker():
    """Chequea batallas y envía notificaciones a usuarios de Discord."""
    await bot.wait_until_ready()
    pool = await db.get_pool()  # tu función DB
    while not bot.is_closed():
        try:
            async with shared.httpx_client() as client:  # si tu lógica usa httpx
                battles = await shared.get_active_battles(client)
                if battles:
                    battle_ids = [b["_id"] for b in battles if "_id" in b]
                    states = await db.get_battle_states(pool, battle_ids)
                    users = await db.get_all_active_users(pool)
                    
                    notifications = shared.check_battles_for_users(
                        users, 
                        [(bid, await shared.get_live_battle_data_batched(client, [bid])) for bid in battle_ids],
                        states
                    )
                    
                    for n in notifications:
                        if n["platform"] == "discord":
                            try:
                                user = await bot.fetch_user(int(n["user_id"]))
                                if user:
                                    await user.send(n["message"].replace("*", "**"))
                                    await db.update_battle_state(
                                        pool, n['user_id'], n['platform'], n['battle_id'], 
                                        n['side_name'], n['ratio'], n['pool']
                                    )
                            except Exception as e:
                                logger.error(f"No se pudo notificar a {n['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Error en battle_checker: {e}")
        await asyncio.sleep(20)

# ------------------------------
# Arranque
# ------------------------------
async def main():
    asyncio.create_task(battle_checker())
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
