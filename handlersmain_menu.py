# handlers/main_menu.py

import random
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database import get_player, save_player, get_next_match_for_team, get_league_standings, generate_league_schedule
from game_engine import daily_update, apply_training, play_match_for_player
from keyboards import main_menu_keyboard, training_keyboard

router = Router()


@router.message(F.text == "⏩ Следующая неделя")
async def next_week(message: Message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        await message.answer("Сначала создай персонажа /create")
        return

    # Ежедневное обновление (7 дней)
    player = daily_update(player)
    save_player(player)

    if player['injury_days'] > 0:
        await message.answer(f"🩹 Ты травмирован. Осталось дней: {player['injury_days']}", reply_markup=main_menu_keyboard())
        return

    current_week = player['last_week_updated'] + 1
    match = get_next_match_for_team(player['league_country'], player['season'], current_week, player['club'])

    if match:
        report, updated_player = play_match_for_player(player, match)
        save_player(updated_player)
        await message.answer(report, reply_markup=main_menu_keyboard())
        # Увеличиваем счётчик недель
        updated_player['last_week_updated'] = current_week
        save_player(updated_player)
    else:
        # Сезон окончен
        # Обновляем возраст и скилл
        player['age'] += 1
        if player['age'] <= 22:
            player['overall'] = min(config.MAX_OVERALL, player['overall'] + random.randint(1, 3))
        elif player['age'] <= 30:
            player['overall'] = min(config.MAX_OVERALL, player['overall'] + random.randint(0, 2))
        else:
            player['overall'] = max(50, player['overall'] - random.randint(1, 2))

        # Сброс сезонной статистики
        player['goals'] = 0
        player['assists'] = 0
        player['yellow_cards'] = 0
        player['red_cards'] = 0
        player['league_points'] = 0
        player['league_goals_for'] = 0
        player['league_goals_against'] = 0
        player['season'] += 1
        player['last_week_updated'] = 0

        # Генерация нового расписания
        generate_league_schedule(player['league_country'], player['season'])

        # Изменение зарплаты
        player['salary'] = int(player['salary'] * (0.9 + random.random() * 0.2))

        save_player(player)
        await message.answer(
            f"🏁 Сезон завершён! Тебе {player['age']} лет. Скилл: {player['overall']}. Новая зарплата: {player['salary']}.\n"
            f"Новый сезон начался!",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "💪 Тренировка")
async def training_menu(message: Message):
    await message.answer("Выбери интенсивность тренировки:", reply_markup=training_keyboard())


@router.message(F.text == "📊 Мой профиль")
async def show_profile(message: Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("Создай персонажа /create")
        return

    text = (
        f"🧑‍⚽ {player['first_name']} {player['last_name']} ({player['age']} лет)\n"
        f"📌 Позиция: {player['position']}\n"
        f"🏆 Клуб: {player['club']} ({player['league_country']})\n"
        f"📊 Общий скилл: {player['overall']}\n"
        f"💪 Форма: {player['physical_form']}   🥱 Усталость: {player['fatigue']}   🔥 Рвение: {player['zeal']}\n"
        f"💰 Деньги: {player['money']}   💵 Зарплата: {player['salary']}\n"
        f"📈 Сезон: Голы {player['goals']}, Ассисты {player['assists']}, ЖК {player['yellow_cards']}, КК {player['red_cards']}\n"
        f"🩹 Травма: {player['injury_days']} дней"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(F.text == "🏆 Турнирная таблица")
async def show_standings(message: Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("Создай персонажа /create")
        return

    standings = get_league_standings(player['league_country'], player['season'])
    if not standings:
        await message.answer("Турнирная таблица пока не сформирована.")
        return

    text = "🏆 *Турнирная таблица:*\n\n"
    for i, team in enumerate(standings[:10], 1):
        text += f"{i}. {team['team_name']} — {team['points']} очков (И: {team['played']}, ГЗ: {team['goals_for']}, ГП: {team['goals_against']})\n"

    player_pos = next((i+1 for i, t in enumerate(standings) if t['team_name'] == player['club']), None)
    if player_pos:
        text += f"\n📍 Твоя команда (*{player['club']}*) на {player_pos} месте."

    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


# ----- Обработчики тренировок (можно вынести в отдельный файл, но для простоты оставим здесь) -----

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