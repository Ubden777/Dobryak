from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

STAR_PACKAGES = {
    100: "⭐️ 100 звезд",
    500: "⭐️ 500 звезд",
    1000: "⭐️ 1000 звезд",
}

def get_deposit_packages_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру с пакетами звезд для пополнения.
    """
    buttons = []
    for stars, text in STAR_PACKAGES.items():
        # callback_data будет вида "deposit_100"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"deposit_{stars}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
