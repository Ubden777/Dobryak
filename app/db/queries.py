import asyncpg
from typing import Optional, List, Union
from decimal import Decimal
from datetime import datetime

# Тип для обозначения либо пула, либо уже установленного соединения
Executor = Union[asyncpg.Pool, asyncpg.Connection]

async def _execute_sql(executor: Executor, sql: str, *args):
    if isinstance(executor, asyncpg.pool.Pool):
        async with executor.acquire() as connection:
            return await connection.execute(sql, *args)
    else:
        return await executor.execute(sql, *args)

async def _fetchrow_sql(executor: Executor, sql: str, *args) -> Optional[asyncpg.Record]:
    if isinstance(executor, asyncpg.pool.Pool):
        async with executor.acquire() as connection:
            return await connection.fetchrow(sql, *args)
    else:
        return await executor.fetchrow(sql, *args)

async def _fetch_sql(executor: Executor, sql: str, *args) -> List[asyncpg.Record]:
    if isinstance(executor, asyncpg.pool.Pool):
        async with executor.acquire() as connection:
            return await connection.fetch(sql, *args)
    else:
        return await executor.fetch(sql, *args)

async def _fetchval_sql(executor: Executor, sql: str, *args):
    if isinstance(executor, asyncpg.pool.Pool):
        async with executor.acquire() as connection:
            return await connection.fetchval(sql, *args)
    else:
        return await executor.fetchval(sql, *args)

# --- User Management ---
async def add_user(executor: Executor, user_id: int, username: str, referred_by_id: Optional[int] = None):
    sql = "INSERT INTO users (user_id, username, referred_by_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING;"
    await _execute_sql(executor, sql, user_id, username, referred_by_id)

async def get_user(executor: Executor, user_id: int) -> Optional[asyncpg.Record]:
    sql = "SELECT * FROM users WHERE user_id = $1;"
    return await _fetchrow_sql(executor, sql, user_id)

# --- Sponsor Channel Management ---
async def add_sponsor_channel(executor: Executor, channel_id: int, channel_url: str):
    sql = "INSERT INTO sponsor_channels (channel_id, channel_url) VALUES ($1, $2) ON CONFLICT (channel_id) DO UPDATE SET channel_url = $2;"
    await _execute_sql(executor, sql, channel_id, channel_url)

async def get_active_sponsor_channel(executor: Executor) -> Optional[asyncpg.Record]:
    sql = "SELECT channel_id, channel_url FROM sponsor_channels LIMIT 1;"
    return await _fetchrow_sql(executor, sql)

# --- Task Management ---
async def add_task(executor: Executor, owner_user_id: int, target_url: str, cost_per_execution: Decimal, executions_needed: int, task_budget_stars: Decimal, hold_days: int = 7) -> int:
    sql = "INSERT INTO tasks (owner_user_id, target_url, cost_per_execution, executions_needed, task_budget_stars, hold_days) VALUES ($1, $2, $3, $4, $5, $6) RETURNING task_id;"
    return await _fetchval_sql(executor, sql, owner_user_id, target_url, cost_per_execution, executions_needed, task_budget_stars, hold_days)

async def get_user_tasks(executor: Executor, user_id: int) -> List[asyncpg.Record]:
    sql = "SELECT task_id, target_url, status, executions_done, executions_needed FROM tasks WHERE owner_user_id = $1 ORDER BY created_at DESC;"
    return await _fetch_sql(executor, sql, user_id)

async def increment_task_budget(executor: Executor, task_id: int, amount: Decimal):
    sql = "UPDATE tasks SET task_budget_stars = task_budget_stars + $1 WHERE task_id = $2;"
    await _execute_sql(executor, sql, amount, task_id)

# --- Execution Management ---
async def find_available_task(executor: Executor, user_id: int) -> Optional[asyncpg.Record]:
    sql = """
        SELECT task_id, target_url, cost_per_execution, hold_days
        FROM tasks
        WHERE status = 'active'
          AND owner_user_id != $1
          AND executions_done < executions_needed
          AND task_id NOT IN (
            SELECT task_id FROM executions WHERE worker_user_id = $1
          )
        ORDER BY cost_per_execution DESC
        LIMIT 1;
    """
    return await _fetchrow_sql(executor, sql, user_id)

async def create_execution(executor: Executor, task_id: int, worker_user_id: int, payout_at: datetime):
    sql = "INSERT INTO executions (task_id, worker_user_id, status, payout_at) VALUES ($1, $2, 'pending_hold', $3);"
    await _execute_sql(executor, sql, task_id, worker_user_id, payout_at)

async def get_pending_hold_executions(executor: Executor) -> List[asyncpg.Record]:
    sql = """
        SELECT e.execution_id, e.worker_user_id, t.target_url, t.cost_per_execution, t.task_id
        FROM executions e
        JOIN tasks t ON e.task_id = t.task_id
        WHERE e.status = 'pending_hold';
    """
    return await _fetch_sql(executor, sql)

async def fail_execution(executor: Executor, execution_id: int):
    sql = "UPDATE executions SET status = 'failed_unsubscribed' WHERE execution_id = $1;"
    await _execute_sql(executor, sql, execution_id)

async def get_ready_for_payout_executions(executor: Executor) -> List[asyncpg.Record]:
    sql = """
        SELECT e.execution_id, e.worker_user_id, e.task_id, t.cost_per_execution, t.target_url, u.referred_by_id, u.ref_bonus_paid
        FROM executions e
        JOIN tasks t ON e.task_id = t.task_id
        JOIN users u ON e.worker_user_id = u.user_id
        WHERE e.status = 'pending_hold' AND e.payout_at <= NOW();
    """
    return await _fetch_sql(executor, sql)

async def complete_execution(executor: Executor, execution_id: int, worker_user_id: int, task_id: int, cost: Decimal):
    await _execute_sql(executor, "UPDATE executions SET status = 'paid' WHERE execution_id = $1;", execution_id)
    await _execute_sql(executor, "UPDATE tasks SET executions_done = executions_done + 1 WHERE task_id = $1;", task_id)
    await update_user_balance(executor, worker_user_id, cost, is_hold=False)
    await update_user_balance(executor, worker_user_id, -cost, is_hold=True)

# --- Balance and Transaction Management ---
async def update_user_balance(executor: Executor, user_id: int, amount_stars: Decimal, is_hold: bool = False):
    field = "hold_stars" if is_hold else "balance_stars"
    sql = f"UPDATE users SET {field} = {field} + $1 WHERE user_id = $2;"
    await _execute_sql(executor, sql, amount_stars, user_id)

async def add_transaction(
    executor: Executor,
    user_id: int,
    type: str,
    status: str,
    amount_stars: Optional[Decimal] = None,
    amount_ton: Optional[Decimal] = None,
    tx_hash: Optional[str] = None,
    telegram_charge_id: Optional[str] = None
):
    sql = "INSERT INTO transactions (user_id, type, status, amount_stars, amount_ton, tx_hash, telegram_charge_id) VALUES ($1, $2, $3, $4, $5, $6, $7);"
    await _execute_sql(executor, sql, user_id, type, status, amount_stars, amount_ton, tx_hash, telegram_charge_id)
