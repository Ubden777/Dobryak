import asyncpg
from typing import Optional, List
from decimal import Decimal

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

# --- Task Management ---

async def add_task(pool: asyncpg.Pool, owner_user_id: int, target_url: str, cost_per_execution: Decimal, executions_needed: int, task_budget_stars: Decimal, hold_days: int = 7) -> int:
    """
    Добавляет новое задание в базу данных и возвращает его ID.
    """
    sql = """
        INSERT INTO tasks (owner_user_id, target_url, cost_per_execution, executions_needed, task_budget_stars, hold_days)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING task_id;
    """
    async with pool.acquire() as connection:
        task_id = await connection.fetchval(sql, owner_user_id, target_url, cost_per_execution, executions_needed, task_budget_stars, hold_days)
        return task_id

async def get_user_tasks(pool: asyncpg.Pool, user_id: int) -> List[asyncpg.Record]:
    """
    Получает список заданий, созданных пользователем.
    """
    sql = "SELECT task_id, target_url, status, executions_done, executions_needed FROM tasks WHERE owner_user_id = $1 ORDER BY created_at DESC;"
    async with pool.acquire() as connection:
        return await connection.fetch(sql, user_id)

# --- Balance and Transaction Management ---

async def update_user_balance(pool: asyncpg.Pool, user_id: int, amount_stars: Decimal, is_hold: bool = False):
    """
    Обновляет баланс пользователя.
    :param amount_stars: Сумма для прибавления (может быть отрицательной для списания).
    :param is_hold: Если True, обновляет hold_stars, иначе balance_stars.
    """
    field = "hold_stars" if is_hold else "balance_stars"
    sql = f"UPDATE users SET {field} = {field} + $1 WHERE user_id = $2;"
    async with pool.acquire() as connection:
        await connection.execute(sql, amount_stars, user_id)

async def add_transaction(
    pool: asyncpg.Pool,
    user_id: int,
    type: str,
    status: str,
    amount_stars: Optional[Decimal] = None,
    amount_ton: Optional[Decimal] = None,
    tx_hash: Optional[str] = None,
    telegram_charge_id: Optional[str] = None
):
    """
    Логирует транзакцию.
    """
    sql = """
        INSERT INTO transactions (user_id, type, status, amount_stars, amount_ton, tx_hash, telegram_charge_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7);
    """
    async with pool.acquire() as connection:
        await connection.execute(sql, user_id, type, status, amount_stars, amount_ton, tx_hash, telegram_charge_id)
