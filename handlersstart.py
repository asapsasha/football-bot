# handlers/start.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database import get_player
from keyboards import main_menu_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if player:
        await message.answer("С возвращением! Используй меню для игры.", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Привет! Я бот-симулятор футбольной карьеры. Создай своего игрока с помощью команды /create.")