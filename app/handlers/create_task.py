import asyncpg
import re
import logging
from decimal import Decimal
from aiogram import Router, F, Bot, types
from aiogram.types import CallbackQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.states.create_task import CreateTaskState
from app.keyboards.create_task import get_my_tasks_keyboard, get_task_type_keyboard, get_check_admin_keyboard, get_cancel_keyboard
from app.keyboards.onboarding import get_main_menu_keyboard # Для возврата в меню
from app.db.queries import get_user_tasks, get_user, update_user_balance, add_transaction, add_task

create_task_router = Router()

# ... (Код до Шага 6 без изменений) ...

# --- UTILS ---
async def cancel_and_clear_state(message: Message, state: FSMContext):
    await state.clear()
    # Нужна ReplyKeyboardRemove для удаления кнопки "Отмена"
    from aiogram.types import ReplyKeyboardRemove
    await message.answer("Создание задания отменено.", reply_markup=ReplyKeyboardRemove())
    # Показываем главное меню
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

# --- NAVIGATIONAL HANDLERS ---
@create_task_router.callback_query(F.data == "tasks")
async def tasks_menu(callback: CallbackQuery, pool: asyncpg.Pool):
    user_tasks = await get_user_tasks(pool, callback.from_user.id)

    if not user_tasks:
        text = "У вас пока нет созданных заданий. Хотите создать первое?"
    else:
        text = "<b>Мои задания:</b>\n\n"
        for task in user_tasks:
            status_emoji = {"active": "🟢", "paused": "🟡", "completed": "✅"}.get(task['status'], "❓")
            text += f"{status_emoji} {task['target_url']} ({task['executions_done']}/{task['executions_needed']})\n"

    await callback.message.edit_text(text, reply_markup=get_my_tasks_keyboard())

@create_task_router.callback_query(F.data == "create_task")
async def start_task_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateTaskState.choosing_task_type)
    await callback.message.edit_text(
        "<b>Шаг 1: Тип задания</b>\n\nВыберите, какой тип задания вы хотите создать.",
        reply_markup=get_task_type_keyboard()
    )

# --- FSM HANDLERS ---

# Отмена на любом шаге
@create_task_router.message(F.text == "❌ Отмена")
async def cancel_creation_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await cancel_and_clear_state(message, state)

@create_task_router.callback_query(F.data == "cancel_task_creation")
async def cancel_creation_callback_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание задания отменено.")
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())


# Шаг 1: Выбор типа задания
@create_task_router.callback_query(F.data == "task_type_subscribe", CreateTaskState.choosing_task_type)
async def get_task_url(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateTaskState.getting_url)
    await callback.message.edit_text(
        "<b>Шаг 2: URL Канала</b>\n\nОтправьте юзернейм канала (например, `@durov`) или ссылку на него (`t.me/durov`).",
        reply_markup=None # Убираем клавиатуру
    )
    # Отправляем отдельное сообщение с кнопкой отмены, чтобы она появилась внизу
    await callback.message.answer("Вы можете отменить создание на любом шаге.", reply_markup=get_cancel_keyboard())


# Шаг 2: Получение URL
@create_task_router.message(CreateTaskState.getting_url)
async def process_url(message: Message, state: FSMContext, bot: Bot):
    url = message.text
    # Простая валидация
    match = re.match(r"(?:@|t\.me/|https://t\.me/)([a-zA-Z0-9_]{5,})", url)
    if not match:
        await message.answer("Неверный формат. Пожалуйста, отправьте юзернейм (`@channel`) или ссылку (`t.me/channel`).")
        return

    channel_username = f"@{match.group(1)}"

    # Проверяем, что канал существует, запросив его
    try:
        chat = await bot.get_chat(channel_username)
        await state.update_data(target_url=channel_username, target_id=chat.id)
    except TelegramBadRequest:
        await message.answer("Не удалось найти такой канал. Убедитесь, что ссылка верна и канал публичный.")
        return

    await state.set_state(CreateTaskState.checking_admin)
    await message.answer(
        f"<b>Шаг 3: Права Администратора</b>\n\nОтлично! Теперь добавьте @{bot.my_name} в администраторы вашего канала `{channel_username}` с правом 'Добавлять участников'.\n\nКак будете готовы, нажмите 'Проверить'.",
        reply_markup=get_check_admin_keyboard()
    )


# Шаг 3: Проверка прав администратора
@create_task_router.callback_query(F.data == "check_admin_rights", CreateTaskState.checking_admin)
async def process_admin_check(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_id = data.get("target_id")

    try:
        member = await bot.get_chat_member(chat_id=target_id, user_id=bot.id)
        if not isinstance(member, types.ChatMemberAdministrator) or not member.can_invite_users:
            await callback.answer("Бот не является администратором или у него нет права 'Добавлять участников'.", show_alert=True)
            return
    except TelegramBadRequest:
        await callback.answer("Не удалось проверить права. Возможно, канал стал приватным или бот был заблокирован.", show_alert=True)
        return

    await state.set_state(CreateTaskState.getting_cost)
    await callback.message.edit_text(
        "<b>Шаг 4: Цена за подписку</b>\n\nСколько звезд вы готовы платить за каждого нового подписчика? (Минимум: 1)"
    )


# Шаг 4: Получение цены
@create_task_router.message(CreateTaskState.getting_cost)
async def process_cost(message: Message, state: FSMContext):
    try:
        cost = Decimal(message.text)
        if cost < 1:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите числовое значение, не меньше 1.")
        return

    await state.update_data(cost_per_execution=cost)
    await state.set_state(CreateTaskState.getting_amount)
    await message.answer("<b>Шаг 5: Количество подписок</b>\n\nСколько всего подписчиков вы хотите привлечь?")

# Шаг 5: Получение количества
@create_task_router.message(CreateTaskState.getting_amount)
async def process_amount(message: Message, state: FSMContext, pool: asyncpg.Pool):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Пожалуйста, введите целое положительное число.")
        return

    await state.update_data(executions_needed=amount)

    data = await state.get_data()
    user = await get_user(pool, message.from_user.id)

    cost_total = data['cost_per_execution'] * amount
    commission = cost_total * Decimal('0.20')
    final_payment = cost_total + commission

    await state.update_data(final_payment=final_payment, task_budget=cost_total)

    await state.set_state(CreateTaskState.confirming)

    text = (
        f"<b>Подтверждение задания:</b>\n\n"
        f"<b>Канал:</b> {data['target_url']}\n"
        f"<b>Цена за подписку:</b> {data['cost_per_execution']} ⭐️\n"
        f"<b>Количество подписок:</b> {amount}\n\n"
        f"<b>Исполнителям:</b> {cost_total} ⭐️\n"
        f"<b>Комиссия (20%):</b> {commission} ⭐️\n"
        f"<b>Итого к списанию:</b> {final_payment} ⭐️\n\n"
        f"<b>Ваш баланс:</b> {user['balance_stars']} ⭐️"
    )

    # C2B-Flow
    if user['balance_stars'] >= final_payment:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить с баланса", callback_data="pay_from_balance")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_creation")]
        ])
        await message.answer(text, reply_markup=keyboard)
    else:
        needed = final_payment - user['balance_stars']
        text += f"\n\nНедостаточно средств. Вам не хватает {needed} ⭐️."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
             [InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="buy_stars")],
             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_creation")]
        ])
        await message.answer(text, reply_markup=keyboard)

# Шаг 6: Оплата и создание
@create_task_router.callback_query(F.data == "pay_from_balance", CreateTaskState.confirming)
async def process_payment_and_create_task(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    user_id = callback.from_user.id

    async with pool.acquire() as conn:
        # Начинаем транзакцию
        async with conn.transaction():
            try:
                # Блокируем строку пользователя для предотвращения гонок
                user = await conn.fetchrow("SELECT balance_stars FROM users WHERE user_id = $1 FOR UPDATE;", user_id)

                if user['balance_stars'] < data['final_payment']:
                    await callback.answer("На вашем балансе недостаточно средств. Возможно, вы совершили другую операцию.", show_alert=True)
                    return # Транзакция автоматически откатится

                # Все операции внутри транзакции
                await update_user_balance(conn, user_id, -data['final_payment'])
                await add_transaction(conn, user_id, 'commission', 'completed', amount_stars=data['final_payment'] - data['task_budget'])
                await add_task(
                    pool=conn,
                    owner_user_id=user_id,
                    target_url=data['target_url'],
                    cost_per_execution=data['cost_per_execution'],
                    executions_needed=data['executions_needed'],
                    task_budget_stars=data['task_budget']
                )

            except Exception as e:
                logging.error(f"Failed to create task for user {user_id} due to: {e}")
                await callback.answer("Произошла ошибка при создании задания. Попробуйте снова.", show_alert=True)
                # Транзакция автоматически откатится
                return

    await state.clear()
    await callback.message.edit_text("✅ <b>Задание успешно создано и оплачено!</b>")
    await tasks_menu(callback, pool)
