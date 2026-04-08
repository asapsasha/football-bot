# database.py

import sqlite3
import config
from collections import deque

DB_PATH = "football.db"

def init_db():
    """Инициализация базы данных и создание всех необходимых таблиц."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Таблица игроков
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            country TEXT,
            club TEXT,
            league_country TEXT,
            age INTEGER,
            season INTEGER,
            overall INTEGER,
            physical_form INTEGER,
            fatigue INTEGER,
            zeal INTEGER,
            salary INTEGER,
            money INTEGER,
            goals INTEGER,
            assists INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            man_of_match INTEGER,
            injury_days INTEGER,
            last_week_updated INTEGER DEFAULT 0,
            league_points INTEGER DEFAULT 0,
            league_goals_for INTEGER DEFAULT 0,
            league_goals_against INTEGER DEFAULT 0
        )
    ''')

    # Таблица истории сезонов (опционально)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS seasons_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            season_number INTEGER,
            club TEXT,
            final_place INTEGER,
            goals INTEGER,
            assists INTEGER,
            avg_rating REAL,
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        )
    ''')

    # Таблица расписания лиги
    cur.execute('''
        CREATE TABLE IF NOT EXISTS league_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_country TEXT,
            season INTEGER,
            week INTEGER,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            is_played BOOLEAN DEFAULT 0
        )
    ''')

    # Таблица турнирной таблицы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS league_standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_country TEXT,
            season INTEGER,
            team_name TEXT,
            played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            UNIQUE(league_country, season, team_name)
        )
    ''')

    conn.commit()
    conn.close()


def get_player(user_id):
    """Получить данные игрока по user_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_player(player_data):
    """Сохранить обновлённые данные игрока."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = '''
        UPDATE players SET
            first_name=?, last_name=?, position=?, country=?, club=?, league_country=?,
            age=?, season=?, overall=?, physical_form=?, fatigue=?, zeal=?,
            salary=?, money=?, goals=?, assists=?, yellow_cards=?, red_cards=?,
            man_of_match=?, injury_days=?, last_week_updated=?, league_points=?,
            league_goals_for=?, league_goals_against=?
        WHERE user_id=?
    '''
    cur.execute(query, (
        player_data['first_name'], player_data['last_name'], player_data['position'],
        player_data['country'], player_data['club'], player_data['league_country'],
        player_data['age'], player_data['season'], player_data['overall'],
        player_data['physical_form'], player_data['fatigue'], player_data['zeal'],
        player_data['salary'], player_data['money'], player_data['goals'],
        player_data['assists'], player_data['yellow_cards'], player_data['red_cards'],
        player_data['man_of_match'], player_data['injury_days'], player_data['last_week_updated'],
        player_data['league_points'], player_data['league_goals_for'],
        player_data['league_goals_against'], player_data['user_id']
    ))
    conn.commit()
    conn.close()


def create_player(user_id, data):
    """Создать нового игрока."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO players (
            user_id, first_name, last_name, position, country, club, league_country,
            age, season, overall, physical_form, fatigue, zeal, salary, money,
            goals, assists, yellow_cards, red_cards, man_of_match, injury_days, last_week_updated,
            league_points, league_goals_for, league_goals_against
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, data['first_name'], data['last_name'], data['position'],
        data['country'], data['club'], data['league_country'],
        config.START_AGE, 1, config.START_OVERALL, config.START_FORM,
        config.START_FATIGUE, config.START_ZEAL, config.START_SALARY, config.START_MONEY,
        0, 0, 0, 0, 0, 0, 0, 0, 0
    ))
    conn.commit()
    conn.close()


# ----- Функции для работы с лигой и расписанием -----

def generate_league_schedule(league_country, season):
    """Генерирует расписание для лиги на сезон по алгоритму 'змейка'."""
    teams = config.TEAMS_BY_LEAGUE[league_country].copy()
    num_teams = len(teams)
    schedule = []

    if num_teams % 2 != 0:
        teams.append(None)  # фиктивная команда для нечётного числа

    # Первый круг
    ring = deque(teams[1:])
    for _ in range(1, num_teams):
        round_matches = []
        for i in range(num_teams // 2):
            home = teams[i]
            away = ring[-(i+1)]
            if home is not None and away is not None:
                round_matches.append((home, away))
        schedule.append(round_matches)
        ring.rotate(1)

    # Второй круг (меняем местами)
    second_leg = []
    for round_matches in schedule:
        second_leg_round = [(away, home) for home, away in round_matches]
        second_leg.append(second_leg_round)

    full_schedule = schedule + second_leg

    # Сохраняем в БД
    conn = sqlite3.connect(DB_PATH)
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
    """Вернуть отсортированную турнирную таблицу."""
    conn = sqlite3.connect(DB_PATH)
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
    """Обновить турнирную таблицу после матча."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    def update_team(team, gf, ga, is_winner, is_draw):
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
              gf, ga, 3 if is_winner else (1 if is_draw else 0),
              1 if is_winner else 0, 1 if is_draw else 0, 1 if not is_winner and not is_draw else 0,
              gf, ga, 3 if is_winner else (1 if is_draw else 0)))

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


def get_next_match_for_team(league_country, season, current_week, team_name):
    """Вернуть следующий матч команды на указанной неделе (если есть)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM league_schedule
        WHERE league_country = ? AND season = ? AND week = ? AND (home_team = ? OR away_team = ?) AND is_played = 0
    ''', (league_country, season, current_week, team_name, team_name))
    match = cur.fetchone()
    conn.close()
    return dict(match) if match else None


def mark_match_played(match_id, home_score, away_score):
    """Отметить матч как сыгранный и записать счёт."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        UPDATE league_schedule
        SET home_score = ?, away_score = ?, is_played = 1
        WHERE id = ?
    ''', (home_score, away_score, match_id))
    conn.commit()
    conn.close()