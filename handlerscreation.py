# handlers/creation.py

import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
import config
from database import create_player, get_player, generate_league_schedule
from keyboards import main_menu_keyboard

router = Router()

class CreationForm(StatesGroup):
    first_name = State()
    last_name = State()
    position = State()
    country = State()
    league_country = State()

POSITIONS = ['Нападающий', 'Полузащитник', 'Защитник', 'Вратарь']
COUNTRIES = ['Россия', 'Бразилия', 'Германия', 'Испания', 'Англия', 'Италия', 'Франция']


@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if get_player(user_id):
        await message.answer("У тебя уже есть персонаж. Используй /start для возврата.")
        return
    await message.answer("Давай создадим твоего игрока! Введи имя:")
    await state.set_state(CreationForm.first_name)


@router.message(CreationForm.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Теперь фамилию:")
    await state.set_state(CreationForm.last_name)


@router.message(CreationForm.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    kb = ReplyKeyboardMarkup(keyboard=[[p] for p in POSITIONS], resize_keyboard=True)
    await message.answer("Выбери позицию:", reply_markup=kb)
    await state.set_state(CreationForm.position)


@router.message(CreationForm.position, F.text.in_(POSITIONS))
async def process_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    kb = ReplyKeyboardMarkup(keyboard=[[c] for c in COUNTRIES], resize_keyboard=True)
    await message.answer("Выбери страну игрока:", reply_markup=kb)
    await state.set_state(CreationForm.country)


@router.message(CreationForm.country, F.text.in_(COUNTRIES))
async def process_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    leagues = list(config.TEAMS_BY_LEAGUE.keys())
    kb = ReplyKeyboardMarkup(keyboard=[[l] for l in leagues], resize_keyboard=True)
    await message.answer("Выбери страну лиги, в которой хочешь начать:", reply_markup=kb)
    await state.set_state(CreationForm.league_country)


@router.message(CreationForm.league_country, F.text.in_(config.TEAMS_BY_LEAGUE.keys()))
async def process_league(message: Message, state: FSMContext):
    league_country = message.text
    await state.update_data(league_country=league_country)
    data = await state.get_data()

    # Рулетка клуба
    club = random.choice(config.TEAMS_BY_LEAGUE[league_country])
    data['club'] = club
    data['league_country'] = league_country

    # Генерируем расписание для лиги на первый сезон
    generate_league_schedule(league_country, 1)

    # Сохраняем игрока в БД
    user_id = message.from_user.id
    create_player(user_id, data)

    await message.answer(
        f"🎉 Твой игрок {data['first_name']} {data['last_name']}, позиция {data['position']}.\n"
        f"Страна: {data['country']}. Ты начинаешь в клубе {club} ({league_country}).\n"
        f"Стартовый скилл: {config.START_OVERALL}. Удачи!",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()