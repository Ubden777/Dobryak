from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_subscribe_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру с кнопкой для подписки на канал и кнопкой для проверки.
    """
    buttons = [
        [InlineKeyboardButton(text="➡️ Подписаться", url=channel_url)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру главного меню.
    """
    buttons = [
        [
            InlineKeyboardButton(text="💪 Приступить к заданиям", callback_data="execute_tasks"),
            InlineKeyboardButton(text="📢 Мои задания", callback_data="tasks")
        ],
        [InlineKeyboardButton(text="⭐️ Звезды", callback_data="stars")],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
