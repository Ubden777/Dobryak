from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_execute_task_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для выполнения задания.
    """
    buttons = [
        [InlineKeyboardButton(text="➡️ Перейти к каналу", url=channel_url)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_task_subscription")],
        [InlineKeyboardButton(text="Пропустить ➡️", callback_data="skip_task")],
        [InlineKeyboardButton(text="❌ Прекратить", callback_data="stop_executing")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
