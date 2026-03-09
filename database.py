import os
import asyncpg
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ------------------------------
# CONNECTION POOL
# ------------------------------

async def get_pool():

    if DATABASE_URL is None:
        raise ValueError("DATABASE_URL environment variable is not set")

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10
    )

    logger.info("Database pool created")

    return pool


# ------------------------------
# INIT DB
# ------------------------------

async def init_db(pool):

    async with pool.acquire() as conn:

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT,
                platform TEXT,
                threshold REAL DEFAULT 0.5,
                min_pool REAL DEFAULT 10.0,
                active INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, platform)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS battle_state (
                user_id TEXT,
                platform TEXT,
                battle_id TEXT,
                side TEXT,
                last_money_per_1k REAL,
                last_money_pool REAL,
                PRIMARY KEY (user_id, platform, battle_id, side)
            )
        """)

        logger.info("Database initialized")


# ------------------------------
# USER FUNCTIONS
# ------------------------------

async def get_user(pool, user_id, platform):

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT threshold, min_pool, active
            FROM users
            WHERE user_id=$1 AND platform=$2
            """,
            str(user_id),
            platform
        )

        return dict(row) if row else None


async def update_user(pool, user_id, platform, threshold=None, min_pool=None, active=None):

    async with pool.acquire() as conn:

        # Ensure user exists
        await conn.execute(
            """
            INSERT INTO users (user_id, platform)
            VALUES ($1,$2)
            ON CONFLICT (user_id,platform) DO NOTHING
            """,
            str(user_id),
            platform
        )

        if threshold is not None:

            await conn.execute(
                """
                UPDATE users
                SET threshold=$1
                WHERE user_id=$2 AND platform=$3
                """,
                threshold,
                str(user_id),
                platform
            )

        if min_pool is not None:

            await conn.execute(
                """
                UPDATE users
                SET min_pool=$1
                WHERE user_id=$2 AND platform=$3
                """,
                min_pool,
                str(user_id),
                platform
            )

        if active is not None:

            await conn.execute(
                """
                UPDATE users
                SET active=$1
                WHERE user_id=$2 AND platform=$3
                """,
                active,
                str(user_id),
                platform
            )


async def get_all_active_users(pool):

    async with pool.acquire() as conn:

        rows = await conn.fetch(
            """
            SELECT user_id, platform, threshold, min_pool
            FROM users
            WHERE active=1
            """
        )

        return [dict(row) for row in rows]


# ------------------------------
# BATTLE STATE
# ------------------------------

async def get_battle_states(pool, battle_ids):

    if not battle_ids:
        return {}

    async with pool.acquire() as conn:

        rows = await conn.fetch(
            """
            SELECT user_id, platform, battle_id, side,
                   last_money_per_1k,
                   last_money_pool
            FROM battle_state
            WHERE battle_id = ANY($1::text[])
            """,
            battle_ids
        )

        states = {}

        for row in rows:

            key = (
                row["user_id"],
                row["platform"],
                row["battle_id"],
                row["side"]
            )

            states[key] = {
                "money_per_1k": row["last_money_per_1k"],
                "money_pool": row["last_money_pool"]
            }

        return states


async def update_battle_state(pool, user_id, platform, battle_id, side, money_per_1k, money_pool):

    async with pool.acquire() as conn:

        await conn.execute(
            """
            INSERT INTO battle_state (
                user_id,
                platform,
                battle_id,
                side,
                last_money_per_1k,
                last_money_pool
            )
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (user_id,platform,battle_id,side)
            DO UPDATE SET
                last_money_per_1k = EXCLUDED.last_money_per_1k,
                last_money_pool = EXCLUDED.last_money_pool
            """,
            str(user_id),
            platform,
            battle_id,
            side,
            money_per_1k,
            money_pool
        )


# ------------------------------
# CLEAN OLD BATTLES
# ------------------------------

async def clear_old_battles(pool, active_battle_ids):

    if not active_battle_ids:
        return

    async with pool.acquire() as conn:

        await conn.execute(
            """
            DELETE FROM battle_state
            WHERE NOT (battle_id = ANY($1::text[]))
            """,
            active_battle_ids
        )
