import logging
import asyncpg
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram.exceptions import TelegramBadRequest

from app.db import queries

async def check_unsubscribes(bot: Bot, pool: asyncpg.Pool):
    logging.info("Scheduler: Running check_unsubscribes job.")
    executions = await queries.get_pending_hold_executions(pool)
    for execution in executions:
        try:
            member = await bot.get_chat_member(
                chat_id=execution['target_url'],
                user_id=execution['worker_user_id']
            )
            if member.status in ['left', 'kicked']:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await queries.fail_execution(conn, execution['execution_id'])
                        await queries.update_user_balance(conn, execution['worker_user_id'], -execution['cost_per_execution'], is_hold=True)
                        await queries.increment_task_budget(conn, execution['task_id'], execution['cost_per_execution'])
                logging.info(f"Execution {execution['execution_id']} for user {execution['worker_user_id']} failed (unsubscribed). Funds returned.")
        except TelegramBadRequest:
            # Канал мог быть удален или бот кикнут. Считаем это как отписку.
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await queries.fail_execution(conn, execution['execution_id'])
                    await queries.update_user_balance(conn, execution['worker_user_id'], -execution['cost_per_execution'], is_hold=True)
                    await queries.increment_task_budget(conn, execution['task_id'], execution['cost_per_execution'])
            logging.warning(f"Execution {execution['execution_id']} failed due to TelegramBadRequest. Assuming unsubscribe.")
        except Exception as e:
            logging.error(f"Unexpected error in check_unsubscribes for execution {execution['execution_id']}: {e}")

async def process_payouts(bot: Bot, pool: asyncpg.Pool):
    logging.info("Scheduler: Running process_payouts job.")
    executions = await queries.get_ready_for_payout_executions(pool)
    for execution in executions:
        try:
            member = await bot.get_chat_member(
                chat_id=execution['target_url'],
                user_id=execution['worker_user_id']
            )
            if member.status not in ['left', 'kicked']:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await queries.complete_execution(
                            conn,
                            execution['execution_id'],
                            execution['worker_user_id'],
                            execution['task_id'],
                            execution['cost_per_execution']
                        )
                logging.info(f"Execution {execution['execution_id']} paid out to user {execution['worker_user_id']}.")
                # TODO: Логика рефералки
            else:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await queries.fail_execution(conn, execution['execution_id'])
                        await queries.update_user_balance(conn, execution['worker_user_id'], -execution['cost_per_execution'], is_hold=True)
                        await queries.increment_task_budget(conn, execution['task_id'], execution['cost_per_execution'])
                logging.info(f"Execution {execution['execution_id']} for user {execution['worker_user_id']} failed (unsubscribed before payout).")
        except Exception as e:
            logging.error(f"Unexpected error in process_payouts for execution {execution['execution_id']}: {e}")


def setup_scheduler(bot: Bot, pool: asyncpg.Pool):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(check_unsubscribes, IntervalTrigger(minutes=15), args=(bot, pool))
    scheduler.add_job(process_payouts, IntervalTrigger(minutes=5), args=(bot, pool))
    return scheduler
