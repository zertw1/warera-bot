import os
import asyncpg

pool = None


async def init_db():
    global pool

    DATABASE_URL = os.environ.get("DATABASE_URL")

    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            platform TEXT DEFAULT 'telegram',
            threshold FLOAT DEFAULT 0,
            min_pool FLOAT DEFAULT 0
        )
        """)


def get_db_pool():
    return pool
