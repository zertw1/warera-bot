import discord
from discord import app_commands
from discord.ext import commands
import shared_logic as shared
import logging
import asyncio
import os
import asyncpg  # si usas PostgreSQL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.httpx_client = None
        self.db_pool = None

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Slash commands synced globally.")

bot = DiscordBot()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # si quieres usar mismo env var

# -----------------------------
# Función para check inmediato
# -----------------------------
async def run_immediate_check(user_id):
    pool = bot.db_pool
    client = bot.httpx_client
    if not pool or not client:
        logger.error("DB Pool o HTTP client no inicializado")
        return

    # obtener usuario
    query = "SELECT * FROM users WHERE user_id=$1 AND platform='discord'"
    user = await pool.fetchrow(query, int(user_id))
    if not user or not user['active']:
        return

    battles = await shared.get_active_battles(client)
    if not battles: return

    battle_ids = [b.get("_id") for b in battles if b.get("_id")]
    states = {}  # aqui puedes traer estados de la DB si los guardas

    batch_results = await shared.get_live_battle_data_batched(client, battle_ids[:10])
    all_live_data = list(zip(battle_ids[:10], batch_results))
    user_list = [{"user_id": user_id, "platform": 'discord', "threshold": user['threshold'], "min_pool": user['min_pool']}]
    notifications = shared.check_battles_for_users(user_list, all_live_data, states)

    try:
        discord_user = await bot.fetch_user(int(user_id))
        if discord_user:
            for n in notifications:
                await discord_user.send(n['message'].replace("*", "**"))
                # guardar estado en DB si lo deseas
    except Exception as e:
        logger.error(f"Error enviando mensaje a {user_id}: {e}")

# -----------------------------
# Eventos y comandos
# -----------------------------
@bot.event
async def on_ready():
    logger.info(f"Discord bot logged in as {bot.user.name}")

@bot.tree.command(name="start", description="Register and start receiving battle notifications")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool = bot.db_pool
    await pool.execute(
        "INSERT INTO users(user_id, platform, active, threshold, min_pool) "
        "VALUES($1,'discord',1,0.5,50) "
        "ON CONFLICT(user_id, platform) DO UPDATE SET active=1", int(user_id)
    )
    await interaction.response.send_message("✅ Registered! You will now receive notifications.", ephemeral=True)

@bot.tree.command(name="status", description="View your current settings")
async def status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool = bot.db_pool
    user = await pool.fetchrow("SELECT * FROM users WHERE user_id=$1 AND platform='discord'", int(user_id))
    if user:
        await interaction.response.send_message(
            f"💰 Threshold: {user['threshold']}\n🏦 Min Pool: {user['min_pool']}\n🔔 Active: {user['active']}", ephemeral=True
        )
    else:
        await interaction.response.send_message("You are not registered. Use /start.", ephemeral=True)

# -----------------------------
# Inicialización
# -----------------------------
async def start_discord_bot(token):
    bot.httpx_client = httpx.AsyncClient()
    bot.db_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(start_discord_bot(os.getenv("DISCORD_BOT_TOKEN")))
