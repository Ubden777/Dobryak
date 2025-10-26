from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_my_tasks_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для раздела "Мои задания".
    """
    buttons = [
        [InlineKeyboardButton(text="➕ Создать новое задание", callback_data="create_task")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора типа задания. В MVP только один тип.
    """
    buttons = [
        [InlineKeyboardButton(text="📢 Подписка на канал/группу", callback_data="task_type_subscribe")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_creation")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_check_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для шага проверки прав администратора у бота.
    """
    buttons = [
        [InlineKeyboardButton(text="✅ Проверить", callback_data="check_admin_rights")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task_creation")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура для отмены на любом шаге ввода данных.
    """
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
