import asyncpg
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, SuccessfulPayment, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.states.deposit import DepositState
from app.keyboards.deposit import get_deposit_packages_keyboard
from app.db.queries import get_user, update_user_balance, add_transaction

deposit_router = Router()

# Этот обработчик будет ловить нажатие на "⭐️ Звезды" в главном меню
@deposit_router.callback_query(F.data == "stars")
async def stars_menu(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, callback.from_user.id)
    balance = user['balance_stars'] if user else 0
    hold = user['hold_stars'] if user else 0

    text = (
        f"<b>⭐️ Звездный баланс</b>\n\n"
        f"<b>Доступно:</b> {balance} ⭐️\n"
        f"<b>В холде:</b> {hold} ⭐️\n\n"
        f"Звезды можно потратить на создание заданий или вывести в TON."
    )
    # Здесь нужна клавиатура с кнопками "Купить" и "Вывести"
    # Пока что сделаем заглушку
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="➖ Вывести в TON", callback_data="withdraw_ton")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)


@deposit_router.callback_query(F.data == "buy_stars")
async def buy_stars(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.choosing_package)
    await callback.message.edit_text(
        "Выберите пакет для пополнения:",
        reply_markup=get_deposit_packages_keyboard()
    )

from app.config.config import Config

# ... (other imports)

@deposit_router.callback_query(F.data.startswith("deposit_"), DepositState.choosing_package)
async def create_deposit_invoice(callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config):
    await callback.message.delete()
    star_amount = int(callback.data.split("_")[1])

    if not config.tg_bot.payment_provider_token:
        await callback.answer("Платежный провайдер не настроен. Пожалуйста, сообщите администратору.", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Покупка {star_amount} звезд",
        description=f"Пополнение баланса в \"Добряк Бот\" на {star_amount} ⭐️",
        payload=f"deposit_{star_amount}",
        provider_token=config.tg_bot.payment_provider_token,
        currency="XTR",
        prices=[LabeledPrice(label=f"{star_amount} ⭐️", amount=star_amount)],
        start_parameter="dobryak-bot-deposit"
    )

@deposit_router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@deposit_router.message(F.successful_payment)
async def successful_payment(message: Message, pool: asyncpg.Pool):
    star_amount = message.successful_payment.total_amount

    await update_user_balance(pool, message.from_user.id, star_amount)
    await add_transaction(pool, message.from_user.id, 'deposit_stars', 'completed', amount_stars=star_amount)

    await message.answer(f"✅ Успешно! Ваш баланс пополнен на {star_amount} ⭐️.")
