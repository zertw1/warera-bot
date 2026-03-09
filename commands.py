from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_pool


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = get_db_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
        )

    await update.message.reply_text(
        "✅ You are registered!\n\n"
        "Commands:\n"
        "/set_threshold <value>\n"
        "/set_min_pool <value>\n"
        "/help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/set_threshold <value> — minimum profit ratio\n"
        "/set_min_pool <value> — minimum bounty pool\n"
    )


async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /set_threshold <value>")
        return

    value = float(context.args[0])
    pool = get_db_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET threshold=$1 WHERE user_id=$2",
            value,
            user_id,
        )

    await update.message.reply_text(f"Threshold set to {value}")


async def set_min_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /set_min_pool <value>")
        return

    value = float(context.args[0])
    pool = get_db_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET min_pool=$1 WHERE user_id=$2",
            value,
            user_id,
        )

    await update.message.reply_text(f"Min pool set to {value}")
