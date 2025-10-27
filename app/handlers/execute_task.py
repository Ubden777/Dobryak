import asyncpg
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.states.execute_task import ExecuteTaskState
from app.keyboards.execute_task import get_execute_task_keyboard
from app.db.queries import find_available_task, create_execution, update_user_balance

execute_task_router = Router()

async def show_task_to_user(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Ищет и показывает пользователю доступное задание.
    """
    task = await find_available_task(pool, callback.from_user.id)

    if not task:
        await callback.message.edit_text("😢 Новых заданий пока нет. Загляните позже!")
        await state.clear()
        return

    await state.set_state(ExecuteTaskState.viewing_task)
    await state.update_data(
        task_id=task['task_id'],
        target_url=task['target_url'],
        cost=task['cost_per_execution'],
        hold_days=task['hold_days']
    )

    text = (
        f"<b>🔥 Новое задание!</b>\n\n"
        f"<b>Тип:</b> Подписка на канал\n"
        f"<b>Награда:</b> {task['cost_per_execution']} ⭐️\n"
        f"<b>Холд:</b> {task['hold_days']} дней\n\n"
        f"Нажмите 'Перейти к каналу', подпишитесь, а затем вернитесь и нажмите 'Проверить подписку'."
    )

    await callback.message.edit_text(text, reply_markup=get_execute_task_keyboard(task['target_url']))


@execute_task_router.callback_query(F.data == "execute_tasks") # Предполагается, что такая кнопка будет в главном меню
async def start_executing(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    await show_task_to_user(callback, state, pool)

@execute_task_router.callback_query(F.data == "skip_task", ExecuteTaskState.viewing_task)
async def skip_task(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    # Просто ищем следующее задание
    await show_task_to_user(callback, state, pool)

@execute_task_router.callback_query(F.data == "stop_executing", ExecuteTaskState.viewing_task)
async def stop_executing(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from app.keyboards.onboarding import get_main_menu_keyboard
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=get_main_menu_keyboard())


@execute_task_router.callback_query(F.data == "check_task_subscription", ExecuteTaskState.viewing_task)
async def check_task_subscription(callback: CallbackQuery, state: FSMContext, bot: Bot, pool: asyncpg.Pool):
    data = await state.get_data()
    target_url = data.get("target_url")

    try:
        member = await bot.get_chat_member(chat_id=target_url, user_id=callback.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            # Пользователь подписан, создаем выполнение и обновляем холд
            cost = data['cost']
            hold_days = data['hold_days']
            payout_at = datetime.utcnow() + timedelta(days=hold_days)

            async with pool.acquire() as conn:
                async with conn.transaction():
                    await create_execution(conn, data['task_id'], callback.from_user.id, payout_at)
                    await update_user_balance(conn, callback.from_user.id, cost, is_hold=True)

            await callback.answer(f"✅ Успех! {cost} ⭐️ зачислены на холд-баланс.", show_alert=True)
            # Ищем следующее задание
            await show_task_to_user(callback, state, pool)

        else:
            await callback.answer("Вы еще не подписаны на канал. Пожалуйста, подпишитесь и попробуйте снова.", show_alert=True)
    except TelegramBadRequest:
        await callback.answer("Произошла ошибка при проверке подписки. Возможно, канал не существует или бот в нем заблокирован.", show_alert=True)
