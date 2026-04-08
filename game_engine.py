# game_engine.py

import random
import config
from database import mark_match_played, update_standings_after_match

# ------------------- Ежедневное обновление -------------------
def daily_update(player):
    """
    Обновляет состояние игрока за одну неделю (7 дней).
    Уменьшает усталость, случайно меняет форму, уменьшает дни травмы.
    """
    # Отдых: усталость снижается на 5 в день, но не ниже 0
    player['fatigue'] = max(0, player['fatigue'] - config.DAILY_FATIGUE_DEC * config.DAYS_IN_WEEK)
    # Случайное колебание формы
    change = random.randint(-2, 2)
    player['physical_form'] = max(1, min(config.MAX_FORM, player['physical_form'] + change))
    # Лечение травмы
    if player['injury_days'] > 0:
        player['injury_days'] -= config.DAYS_IN_WEEK
        if player['injury_days'] < 0:
            player['injury_days'] = 0
    return player


# ------------------- Тренировки -------------------
def apply_training(player, intensity):
    """
    Применяет эффект тренировки заданной интенсивности.
    intensity: 'light', 'medium', 'heavy'
    Возвращает (текст_отчёта, обновлённый_игрок)
    """
    # Цена и эффекты
    if intensity == 'light':
        cost = 500
        form_inc = 2
        fatigue_inc = 5
        injury_risk = 0.0
    elif intensity == 'medium':
        cost = 1000
        form_inc = 5
        fatigue_inc = 10
        injury_risk = 0.02
    else:  # heavy
        cost = 2000
        form_inc = 10
        fatigue_inc = 20
        injury_risk = 0.08

    if player['money'] < cost:
        return "Недостаточно денег!", player

    player['money'] -= cost
    player['physical_form'] = min(config.MAX_FORM, player['physical_form'] + form_inc)
    player['fatigue'] = min(config.MAX_FATIGUE, player['fatigue'] + fatigue_inc)

    text = f"💪 Тренировка ({intensity}): форма +{form_inc}, усталость +{fatigue_inc}. Потрачено {cost}."

    # Риск травмы
    if random.random() < injury_risk:
        injury_days = random.randint(5, 15)
        player['injury_days'] = injury_days
        text += f" ⚠️ Ты получил травму! Пропустишь {injury_days} дней."

    return text, player


# ------------------- Расчёт успеха в событиях -------------------
def calculate_event_success(player, event_type, choice_difficulty):
    """
    Возвращает вероятность успеха (0..1) для ролевого события (пенальти, штрафной и т.д.)
    event_type – не используется напрямую, но можно добавить модификаторы в будущем.
    choice_difficulty – множитель сложности выбора (1.2 – легко, 1.0 – средне, 0.8 – сложно)
    """
    base_chance = 0.5
    skill_factor = player['overall'] / 100.0
    form_factor = player['physical_form'] / 100.0
    fatigue_penalty = 1 - player['fatigue'] / 200.0
    zeal_factor = 1 + (player['zeal'] - 50) / 100.0

    # Ограничиваем экстремальные значения
    fatigue_penalty = max(0.3, min(1.0, fatigue_penalty))
    zeal_factor = max(0.4, min(1.6, zeal_factor))

    chance = base_chance * skill_factor * form_factor * fatigue_penalty * zeal_factor * choice_difficulty
    return min(0.95, max(0.05, chance))


# ------------------- Симуляция матча между командами -------------------
def simulate_team_match(team1, team2):
    """
    Симулирует результат матча между двумя командами на основе их рейтинга.
    Возвращает (голы_команды1, голы_команды2)
    """
    # Рейтинг команд (можно расширить или брать из БД)
    team_ratings = {
        "Реал Мадрид": 90, "Барселона": 89, "Бавария": 88, "ПСЖ": 87, "Ман Сити": 86,
        "Ливерпуль": 85, "Челси": 84, "Ювентус": 83, "Милан": 82, "Интер": 81,
        "Арсенал": 80, "Тоттенхэм": 79, "Ман Юнайтед": 78, "Атлетико Мадрид": 77,
        "Севилья": 76, "Наполи": 75, "Рома": 74, "Боруссия Дортмунд": 73,
        "РБ Лейпциг": 72, "Марсель": 71, "Лион": 70, "Монако": 69,
        "Ньюкасл": 68, "Астон Вилла": 67, "Вильярреал": 66, "Реал Сосьедад": 65,
        "Аталанта": 64, "Байер 04": 63,
    }
    rating1 = team_ratings.get(team1, 70)
    rating2 = team_ratings.get(team2, 70)

    total = rating1 + rating2
    prob_win1 = rating1 / total
    prob_win2 = rating2 / total
    prob_draw = 0.2  # базовая вероятность ничьей

    # Нормализуем вероятности
    prob_win1 = prob_win1 * (1 - prob_draw)
    prob_win2 = prob_win2 * (1 - prob_draw)

    r = random.random()
    if r < prob_win1:
        goals1 = random.randint(1, 3)
        goals2 = random.randint(0, goals1 - 1)
    elif r < prob_win1 + prob_win2:
        goals2 = random.randint(1, 3)
        goals1 = random.randint(0, goals2 - 1)
    else:
        goals1 = random.randint(0, 2)
        goals2 = goals1
    return goals1, goals2


# ------------------- Матч с участием игрока -------------------
def play_match_for_player(player, match_info):
    """
    Симулирует матч, в котором участвует игрок.
    match_info – словарь из таблицы league_schedule (id, home_team, away_team и т.д.)
    Возвращает (текст_отчёта, обновлённый_игрок)
    """
    # Если игрок травмирован – он пропускает матч
    if player['injury_days'] > 0:
        opponent = match_info['away_team'] if match_info['home_team'] == player['club'] else match_info['home_team']
        return f"❌ Ты травмирован и пропускаешь матч против {opponent}. Осталось дней травмы: {player['injury_days']}.", player

    # Определяем, дома или в гостях играет команда игрока
    is_home = (match_info['home_team'] == player['club'])
    opponent = match_info['away_team'] if is_home else match_info['home_team']

    # Симуляция матча между командами
    home_score, away_score = simulate_team_match(match_info['home_team'], match_info['away_team'])

    # Сохраняем результат в расписание
    mark_match_played(match_info['id'], home_score, away_score)
    # Обновляем турнирную таблицу
    update_standings_after_match(
        player['league_country'], player['season'],
        match_info['home_team'], match_info['away_team'],
        home_score, away_score
    )

    # Личная статистика игрока в матче
    player_goals = 0
    player_assists = 0
    team_score = home_score if is_home else away_score
    opponent_score = away_score if is_home else home_score

    # Шанс забить гол или отдать голевую передачу (только для полевых игроков)
    if player['position'] in ['Нападающий', 'Полузащитник']:
        # Базовый шанс зависит от формы, усталости, рвения и общего скилла
        goal_chance = (player['overall'] / 100) * (player['physical_form'] / 100) * (1 - player['fatigue'] / 200) * (player['zeal'] / 100)
        # Вероятность забить ~30% от базового шанса
        if random.random() < goal_chance * 0.3:
            player_goals = random.randint(1, 2)
        # Вероятность отдать голевую ~40% от базового шанса
        if random.random() < goal_chance * 0.4:
            player_assists = random.randint(1, 2)

    # Обновление параметров игрока после матча
    player['fatigue'] = min(config.MAX_FATIGUE, player['fatigue'] + config.MATCH_FATIGUE_INC)
    form_change = random.randint(-2, 2) + (player_goals * 2)
    player['physical_form'] = max(1, min(config.MAX_FORM, player['physical_form'] + form_change))

    if team_score > opponent_score:
        player['zeal'] = min(config.MAX_ZEAL, player['zeal'] + 8)
        zeal_text = "🔥 Победа! Рвение +8"
    elif team_score < opponent_score:
        player['zeal'] = max(0, player['zeal'] - 8)
        zeal_text = "😞 Поражение... Рвение -8"
    else:
        player['zeal'] = max(0, min(config.MAX_ZEAL, player['zeal'] + random.randint(-2, 2)))
        zeal_text = "🤝 Ничья"

    # Обновляем сезонную статистику
    player['goals'] += player_goals
    player['assists'] += player_assists
    # Для турнирной таблицы (командные очки, забитые/пропущенные – обновляются в update_standings_after_match)
    # Но для истории игрока можно добавить и командные показатели:
    player['league_points'] += 3 if team_score > opponent_score else (1 if team_score == opponent_score else 0)
    player['league_goals_for'] += team_score
    player['league_goals_against'] += opponent_score

    # Риск травмы из-за переутомления
    injury_text = ""
    if player['fatigue'] > 95 and random.random() < 0.25:
        injury_days = random.randint(7, 30)
        player['injury_days'] = injury_days
        injury_text = f"\n⚠️ Ты получил травму! Пропустишь {injury_days} дней."

    # Формируем отчёт
    report = (f"🏆 {match_info['home_team']} {home_score}:{away_score} {match_info['away_team']}\n"
              f"📊 Твоя статистика: ⚽ Голы: {player_goals}, 🎯 Ассисты: {player_assists}\n"
              f"💪 Форма: {form_change:+d} | 🥱 Усталость +{config.MATCH_FATIGUE_INC}\n"
              f"{zeal_text}{injury_text}")

    return report, player