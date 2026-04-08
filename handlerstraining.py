# handlers/training.py

from aiogram import Router, F
from aiogram.types import Message
from database import get_player, save_player
from game_engine import apply_training
from keyboards import main_menu_keyboard

router = Router()

@router.message(F.text == "🏋️ Лёгкая (500)")
async def light_training(message: Message):
    await process_training(message, "light")

@router.message(F.text == "💪 Средняя (1000)")
async def medium_training(message: Message):
    await process_training(message, "medium")

@router.message(F.text == "🔥 Тяжёлая (2000)")
async def heavy_training(message: Message):
    await process_training(message, "heavy")

@router.message(F.text == "🛌 Восстановление (800)")
async def recovery(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        await message.answer("Создай персонажа /create")
        return
    
    cost = 800
    if player['money'] < cost:
        await message.answer("Недостаточно денег для восстановления!")
        return
    
    player['money'] -= cost
    player['fatigue'] = max(0, player['fatigue'] - 20)
    save_player(player)
    await message.answer(f"🛌 Ты восстановился! Усталость снижена на 20. Потрачено {cost}.", reply_markup=main_menu_keyboard())

@router.message(F.text == "🔙 Назад")
async def back_to_menu(message: Message):
    await message.answer("Возврат в главное меню.", reply_markup=main_menu_keyboard())

async def process_training(message: Message, intensity):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        await message.answer("Создай персонажа /create")
        return
    
    report, updated_player = apply_training(player, intensity)
    save_player(updated_player)
    await message.answer(report, reply_markup=main_menu_keyboard())