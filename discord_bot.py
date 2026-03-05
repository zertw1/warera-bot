import discord
from discord.ext import tasks, commands
import shared_logic as shared
import logging
import asyncio

logger = logging.getLogger(__name__)

# ------------------------------
# CONFIGURACIÓN
# ------------------------------

TOKEN = "5a0f6f21c7c60a457a5080bdf33c89991dd0d2fd2215a786e3612328138141a4"  # Reemplaza esto con la variable de entorno si quieres
CHANNEL_ID = 1479194534410981436  # Pega aquí el ID de tu canal

CHECK_INTERVAL = 60  # segundos entre chequeos de bounties

# ------------------------------
# BOT
# ------------------------------

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot conectado como {bot.user.name}')
    check_bounties.start()  # inicia la tarea de bounties periódica

# ------------------------------
# TAREA PERIÓDICA DE BOUNTIES
# ------------------------------

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_bounties():
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            logger.error(f"No se encontró el canal con ID {CHANNEL_ID}")
            return

        # Obtener bounties activos usando tu lógica compartida
        battles = await shared.get_active_battles()  # Ajusta si tu función requiere algún cliente
        if not battles:
            return

        # Aquí creamos mensajes simples de cada battle
        for battle in battles:
            message = f"💥 Battle disponible: {battle.get('name')} - Pool: {battle.get('pool')}"
            await channel.send(message)

    except Exception as e:
        logger.error(f"Error revisando bounties: {e}")

# ------------------------------
# COMANDOS SIMPLES
# ------------------------------

@bot.command(name="status")
async def status(ctx):
    await ctx.send("✅ Bot activo y revisando bounties.")

# ------------------------------
# INICIAR BOT
# ------------------------------

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


