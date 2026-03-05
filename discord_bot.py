import discord
from discord import app_commands
from discord.ext import commands
import database as db
import shared_logic as shared
import logging
import asyncio

logger = logging.getLogger(__name__)

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

def get_bot():
    return bot

async def run_immediate_check(user_id):
    # accessing pool from bot instance
    pool = bot.db_pool
    if not pool:
        logger.error("DB Pool not initialized in Discord Bot")
        return

    user = await db.get_user(pool, user_id, 'discord')
    if not user or not user['active'] or not bot.httpx_client:
        return

    battles = await shared.get_active_battles(bot.httpx_client)
    if not battles:
        return

    battle_ids = [b.get("_id") for b in battles if b.get("_id")]
    states = await db.get_battle_states(pool, battle_ids)

    batch_results = await shared.get_live_battle_data_batched(bot.httpx_client, battle_ids[:10])
    all_live_data = list(zip(battle_ids[:10], batch_results))

    user_list = [{"user_id": user_id, "platform": 'discord', "threshold": user['threshold'], "min_pool": user['min_pool']}]
    notifications = shared.check_battles_for_users(user_list, all_live_data, states)
    
    try:
        discord_user = await bot.fetch_user(int(user_id))
        if discord_user:
            for n in notifications:
                await discord_user.send(n['message'].replace("*", "**"))
                await db.update_battle_state(pool, n['user_id'], n['platform'], n['battle_id'], n['side_name'], n['ratio'], n['pool'])
    except Exception as e:
        logger.error(f"Error in immediate check for {user_id}: {e}")

@bot.event
async def on_ready():
    logger.info(f'Discord bot logged in as {bot.user.name}')

@bot.tree.command(name="start", description="Register and start receiving battle notifications")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool = interaction.client.db_pool
    await db.update_user(pool, user_id, 'discord', active=1)
    user = await db.get_user(pool, user_id, 'discord')
    
    welcome_text = (
        "👋 Welcome to the WarEra Battle Checker Bot!\\n\\n"
        "I will notify you when profitable battles are found based on your settings.\\n\\n"
        f"Current Settings:\\n"
        f"💰 Threshold: {user['threshold']} money/1k damage\\n"
        f"🏦 Min Pool: {user['min_pool']} money\\n\\n"
        "Commands:\\n"
        "/threshold - Set your bounty threshold\\n"
        "/minpool - Set minimum money pool\\n"
        "/status - View your current settings\\n"
        "/stop - Stop receiving notifications"
    )
    await interaction.response.send_message(welcome_text, ephemeral=True)

@bot.tree.command(name="threshold", description="Set your bounty threshold (money per 1k damage)")
@app_commands.describe(value="Value between 0 and 2 (e.g. 0.8)")
async def set_threshold(interaction: discord.Interaction, value: float):
    user_id = str(interaction.user.id)
    pool = interaction.client.db_pool
    if 0 < value <= 2:
        await db.update_user(pool, user_id, 'discord', threshold=value)
        await interaction.response.send_message(f"✅ Threshold updated to {value}. Checking for battles...", ephemeral=True)
        asyncio.create_task(run_immediate_check(user_id))
    else:
        await interaction.response.send_message("❌ Value must be between 0 and 2.", ephemeral=True)

@bot.tree.command(name="minpool", description="Set minimum money pool")
@app_commands.describe(value="Value between 10 and 200")
async def set_minpool(interaction: discord.Interaction, value: float):
    user_id = str(interaction.user.id)
    pool = interaction.client.db_pool
    if 10 <= value <= 200:
        await db.update_user(pool, user_id, 'discord', min_pool=value)
        await interaction.response.send_message(f"✅ Minimum pool updated to {value}. Checking for battles...", ephemeral=True)
        asyncio.create_task(run_immediate_check(user_id))
    else:
        await interaction.response.send_message("❌ Value must be between 10 and 200.", ephemeral=True)

@bot.tree.command(name="status", description="View your current settings")
async def status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool = interaction.client.db_pool
    user = await db.get_user(pool, user_id, 'discord')
    if user:
        status_text = (
            "📊 Your Settings:\\n"
            f"💰 Threshold: {user['threshold']}\\n"
            f"🏦 Min Pool: {user['min_pool']}\\n"
            f"🔔 Notifications: {'Enabled' if user['active'] else 'Disabled'}"
        )
        await interaction.response.send_message(status_text, ephemeral=True)
    else:
        await interaction.response.send_message("You are not registered. Use /start to begin.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop receiving notifications")
async def stop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool = interaction.client.db_pool
    await db.update_user(pool, user_id, 'discord', active=0)
    await interaction.response.send_message("🚫 Notifications stopped. Use /start to resume.", ephemeral=True)

async def start_discord_bot(token):
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Failed to start Discord bot: {e}")
