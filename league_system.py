# league_system.py

import random
import sqlite3
import config
from collections import deque

def generate_league_schedule(league_country, season):
    """
    Генерирует расписание для лиги на сезон по алгоритму "змейка".
    """
    teams = config.TEAMS_BY_LEAGUE[league_country]
    num_teams = len(teams)
    schedule = []

    # --- Алгоритм "змейка" для генерации расписания (два круга) ---
    if num_teams % 2 != 0:
        teams.append(None)  # Добавляем фиктивную команду для нечетного числа
    
    # Первый круг
    ring = deque(teams[1:])
    for round_num in range(1, num_teams):
        round_matches = []
        for i in range(num_teams // 2):
            home = teams[i]
            away = ring[-(i+1)]
            if home is not None and away is not None:
                round_matches.append((home, away))
        schedule.append(round_matches)
        ring.rotate(1)
    
    # Второй круг (меняем местами домашнюю и выездную команды)
    second_leg = []
    for round_matches in schedule:
        second_leg_round = [(away, home) for home, away in round_matches]
        second_leg.append(second_leg_round)
    
    full_schedule = schedule + second_leg
    
    # Сохраняем расписание в базу данных
    conn = sqlite3.connect('football.db')
    cur = conn.cursor()
    week_num = 1
    for round_matches in full_schedule:
        for home, away in round_matches:
            cur.execute('''
                INSERT INTO league_schedule (league_country, season, week, home_team, away_team)
                VALUES (?, ?, ?, ?, ?)
            ''', (league_country, season, week_num, home, away))
        week_num += 1
    conn.commit()
    conn.close()

def get_league_standings(league_country, season):
    """Получить текущую турнирную таблицу лиги."""
    conn = sqlite3.connect('football.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM league_standings
        WHERE league_country = ? AND season = ?
        ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC
    ''', (league_country, season))
    standings = [dict(row) for row in cur.fetchall()]
    conn.close()
    return standings

def update_standings_after_match(league_country, season, home_team, away_team, home_score, away_score):
    """Обновляет турнирную таблицу после сыгранного матча."""
    conn = sqlite3.connect('football.db')
    cur = conn.cursor()
    
    # Функция для обновления статистики команды
    def update_team(team, goals_for, goals_against, is_winner, is_draw):
        cur.execute('''
            INSERT INTO league_standings (league_country, season, team_name, played, wins, draws, losses, goals_for, goals_against, points)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(league_country, season, team_name) DO UPDATE SET
                played = played + 1,
                wins = wins + ?,
                draws = draws + ?,
                losses = losses + ?,
                goals_for = goals_for + ?,
                goals_against = goals_against + ?,
                points = points + ?
        ''', (league_country, season, team,
              1 if is_winner else 0, 1 if is_draw else 0, 1 if not is_winner and not is_draw else 0,
              goals_for, goals_against, 3 if is_winner else (1 if is_draw else 0),
              1 if is_winner else 0, 1 if is_draw else 0, 1 if not is_winner and not is_draw else 0,
              goals_for, goals_against, 3 if is_winner else (1 if is_draw else 0)))
    
    if home_score > away_score:
        update_team(home_team, home_score, away_score, True, False)
        update_team(away_team, away_score, home_score, False, False)
    elif away_score > home_score:
        update_team(home_team, home_score, away_score, False, False)
        update_team(away_team, away_score, home_score, True, False)
    else:
        update_team(home_team, home_score, away_score, False, True)
        update_team(away_team, away_score, home_score, False, True)
    
    conn.commit()
    conn.close()

def simulate_team_match(team1, team2):
    """Симулирует результат матча между двумя командами на основе их силы."""
    # Базовая сила команды (можно вынести в конфиг)
    team_strength = {
        "Реал Мадрид": 90, "Барселона": 89, "Бавария": 88, "ПСЖ": 87, "Ман Сити": 86,
        "Ливерпуль": 85, "Челси": 84, "Ювентус": 83, "Милан": 82, "Интер": 81,
    }
    strength1 = team_strength.get(team1, 75)
    strength2 = team_strength.get(team2, 75)
    
    # Расчет вероятности победы
    total_strength = strength1 + strength2
    prob_win1 = strength1 / total_strength
    prob_win2 = strength2 / total_strength
    prob_draw = 0.2  # Базовая вероятность ничьей
    
    # Нормализация вероятностей
    prob_win1 = prob_win1 * (1 - prob_draw)
    prob_win2 = prob_win2 * (1 - prob_draw)
    
    rand = random.random()
    if rand < prob_win1:
        # Победа первой команды
        goals1 = random.randint(1, 3)
        goals2 = random.randint(0, goals1 - 1)
    elif rand < prob_win1 + prob_win2:
        # Победа второй команды
        goals2 = random.randint(1, 3)
        goals1 = random.randint(0, goals2 - 1)
    else:
        # Ничья
        goals1 = random.randint(0, 2)
        goals2 = goals1
    
    return goals1, goals2

def generate_european_cup(season, qualified_teams, cup_type="champions_league"):
    """
    Генерирует сетку плей-офф для еврокубка.
    qualified_teams: список команд, прошедших квалификацию.
    """
    random.shuffle(qualified_teams)
    matches = []
    for i in range(0, len(qualified_teams), 2):
        if i+1 < len(qualified_teams):
            matches.append((qualified_teams[i], qualified_teams[i+1]))
    
    table_name = "champions_league" if cup_type == "champions_league" else "europa_league"
    conn = sqlite3.connect('football.db')
    cur = conn.cursor()
    
    for team1, team2 in matches:
        cur.execute(f'''
            INSERT INTO {table_name} (season, round, team1, team2)
            VALUES (?, ?, ?, ?)
        ''', (season, "1/8 финала", team1, team2))
    
    conn.commit()
    conn.close()

def play_european_match(season, cup_type, match_id):
    """
    "Сыграть" матч еврокубка.
    """
    table_name = "champions_league" if cup_type == "champions_league" else "europa_league"
    conn = sqlite3.connect('football.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM {table_name} WHERE id = ? AND season = ?', (match_id, season))
    match = cur.fetchone()
    
    if not match or match['is_played']:
        return None
    
    team1 = match['team1']
    team2 = match['team2']
    score1, score2 = simulate_team_match(team1, team2)
    
    cur.execute(f'''
        UPDATE {table_name}
        SET score1 = ?, score2 = ?, is_played = 1
        WHERE id = ?
    ''', (score1, score2, match_id))
    conn.commit()
    conn.close()
    
    winner = team1 if score1 > score2 else (team2 if score2 > score1 else None)
    return {'team1': team1, 'team2': team2, 'score1': score1, 'score2': score2, 'winner': winner}