import asyncpg
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.states.onboarding import OnboardingState
from app.keyboards.onboarding import get_subscribe_keyboard, get_main_menu_keyboard
from app.db.queries import add_user, get_active_sponsor_channel

onboarding_router = Router()

@onboarding_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot, pool: asyncpg.Pool):
    """
    Обработчик команды /start. Начинает процесс онбординга.
    """
    # 1. Проверка наличия username
    if message.from_user.username is None:
        await message.answer("Пожалуйста, установите @username в настройках Telegram, чтобы пользоваться ботом.")
        return

    # 2. Обработка реферальной ссылки и создание пользователя
    ref_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].split("_")[1])
        except (ValueError, IndexError):
            pass

    await add_user(pool, message.from_user.id, message.from_user.username, ref_id)

    # 3. Проверка обязательной подписки
    sponsor = await get_active_sponsor_channel(pool)
    if not sponsor:
        # Если спонсоров нет, сразу показываем главное меню
        await message.answer("Добро пожаловать!", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    try:
        member = await bot.get_chat_member(chat_id=sponsor["channel_id"], user_id=message.from_user.id)
        if member.status not in ['left', 'kicked']:
            # Если уже подписан, показываем главное меню
            await message.answer("Добро пожаловать! Вы уже подписаны на наш канал.", reply_markup=get_main_menu_keyboard())
            await state.clear()
            return
    except TelegramBadRequest:
        # Если бот не админ в канале или канал не существует
        await message.answer("Произошла ошибка с каналом спонсора. Сообщите администратору.")
        return

    # Если не подписан, просим подписаться
    await message.answer(
        "Для доступа к боту, пожалуйста, подпишитесь на наш канал.",
        reply_markup=get_subscribe_keyboard(sponsor["channel_url"])
    )
    await state.set_state(OnboardingState.waiting_for_subscription)


@onboarding_router.callback_query(F.data == "check_subscription", OnboardingState.waiting_for_subscription)
async def check_subscription(callback: CallbackQuery, state: FSMContext, bot: Bot, pool: asyncpg.Pool):
    """
    Проверяет, подписался ли пользователь на канал.
    """
    sponsor = await get_active_sponsor_channel(pool)
    if not sponsor:
        await callback.answer("Ошибка: Спонсорский канал не найден.", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(chat_id=sponsor["channel_id"], user_id=callback.from_user.id)
        if member.status not in ['left', 'kicked']:
            await callback.message.edit_text("Спасибо за подписку! Добро пожаловать в \"Добряк Бот\"!")
            await callback.message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
            await state.clear()
        else:
            await callback.answer("Вы еще не подписались на канал.", show_alert=True)
    except TelegramBadRequest:
        await callback.answer("Произошла ошибка. Убедитесь, что бот является администратором в канале.", show_alert=True)
