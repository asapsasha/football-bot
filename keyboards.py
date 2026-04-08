# keyboards.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    """Главное меню игры."""
    buttons = [
        [KeyboardButton(text="⏩ Следующая неделя")],
        [KeyboardButton(text="💪 Тренировка")],
        [KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="🏆 Турнирная таблица")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def training_keyboard():
    """Меню выбора тренировки."""
    buttons = [
        [KeyboardButton(text="🏋️ Лёгкая (500)"), KeyboardButton(text="💪 Средняя (1000)")],
        [KeyboardButton(text="🔥 Тяжёлая (2000)"), KeyboardButton(text="🛌 Восстановление (800)")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def event_choice_keyboard(options):
    """Инлайн-клавиатура для выбора действия в событии (пенальти и т.д.)."""
    kb = []
    for i, opt in enumerate(options):
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"event_{i}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)