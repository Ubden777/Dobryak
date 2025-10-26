import asyncpg
from typing import Optional

# --- User Management ---

async def add_user(pool: asyncpg.Pool, user_id: int, username: str, referred_by_id: Optional[int] = None):
    """
    Добавляет нового пользователя в базу данных.
    Если пользователь уже существует, ничего не делает.
    """
    sql = """
        INSERT INTO users (user_id, username, referred_by_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO NOTHING;
    """
    async with pool.acquire() as connection:
        await connection.execute(sql, user_id, username, referred_by_id)

async def get_user(pool: asyncpg.Pool, user_id: int) -> Optional[asyncpg.Record]:
    """
    Получает информацию о пользователе по его ID.
    """
    sql = "SELECT * FROM users WHERE user_id = $1;"
    async with pool.acquire() as connection:
        return await connection.fetchrow(sql, user_id)

# --- Sponsor Channel Management ---

async def add_sponsor_channel(pool: asyncpg.Pool, channel_id: int, channel_url: str):
    """
    Добавляет новый спонсорский канал.
    """
    sql = """
        INSERT INTO sponsor_channels (channel_id, channel_url)
        VALUES ($1, $2)
        ON CONFLICT (channel_id) DO UPDATE SET channel_url = $2;
    """
    async with pool.acquire() as connection:
        await connection.execute(sql, channel_id, channel_url)

async def get_active_sponsor_channel(pool: asyncpg.Pool) -> Optional[asyncpg.Record]:
    """
    Получает один (первый) активный спонсорский канал.
    В MVP предполагаем, что он только один.
    """
    sql = "SELECT channel_id, channel_url FROM sponsor_channels LIMIT 1;"
    async with pool.acquire() as connection:
        return await connection.fetchrow(sql)
