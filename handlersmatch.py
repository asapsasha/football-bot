# handlers/match.py

import random
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from database import get_player, save_player
from game_engine import calculate_event_success
from keyboards import event_choice_keyboard, main_menu_keyboard

router = Router()

class MatchState(StatesGroup):
    waiting_choice = State()

# Временные данные для матча (можно хранить в FSM)
user_match_data = {}

@router.message(F.text == "⏩ Следующая неделя")
async def next_week_with_events(message: Message, state: FSMContext):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        await message.answer("Сначала создай персонажа /create")
        return
    
    # ... (здесь должна быть логика получения следующего матча, аналогично main_menu)
    # Для примера создадим тестовое событие
    event = {
        'minute': 23,
        'type': 'penalty',
        'options': ['левый угол', 'правый угол', 'по центру', 'в девятку'],
        'difficulties': [1.0, 1.0, 1.2, 0.8]
    }
    
    await state.update_data(user_id=user_id, event=event, report=[])
    await state.set_state(MatchState.waiting_choice)
    await message.answer(
        f"🕒 {event['minute']}′. Событие: {event['type'].upper()}\nТвой выбор?",
        reply_markup=event_choice_keyboard(event['options'])
    )

@router.callback_query(MatchState.waiting_choice, F.data.startswith("event_"))
async def handle_event_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    event = data['event']
    choice_idx = int(callback.data.split("_")[1])
    
    player = get_player(user_id)
    if not player:
        await callback.message.edit_text("Ошибка: данные игрока не найдены.")
        await state.clear()
        return
    
    chosen_option = event['options'][choice_idx]
    difficulty = event['difficulties'][choice_idx]
    success_chance = calculate_event_success(player, event['type'], difficulty)
    success = random.random() < success_chance
    
    # Обработка результата (упрощенная)
    if success:
        result_text = f"✅ Успех! Ты выбрал {chosen_option} и добился успеха!"
        player['goals'] += 1
    else:
        result_text = f"❌ Неудача! Твой выбор {chosen_option} не принес результата."
    
    save_player(player)
    report = data.get('report', []) + [result_text]
    
    await callback.message.edit_text(result_text)
    await callback.message.answer("Матч окончен.\n" + "\n".join(report), reply_markup=main_menu_keyboard())
    await state.clear()
    await callback.answer()