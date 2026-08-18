import sqlite3
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица пользователей с именами
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            requests_count INTEGER DEFAULT 0
        )
    """)

    # Проверка и добавление недостающих колонок если база уже существует
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "username" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "full_name" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "balance" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0")
    if "xp" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
    if "level" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
    if "last_daily" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_daily TEXT")
    if "referred_by" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    if "game_balance" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN game_balance INTEGER DEFAULT 0")
    if "history_interval" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN history_interval TEXT DEFAULT 'never'")

    # Таблица истории просмотров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS view_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            anime_id TEXT,
            episode_id INTEGER,
            viewed_at TEXT
        )
    """)

    # Таблица рассылок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at TEXT
        )
    """)

    # Таблица отправленных сообщений для удаления
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER,
            user_id INTEGER,
            message_id INTEGER,
            FOREIGN KEY (broadcast_id) REFERENCES broadcasts(broadcast_id)
        )
    """)

    # Таблица рейтингов аниме
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_anime_ratings (
            user_id INTEGER,
            anime_id TEXT,
            rating INTEGER,
            PRIMARY KEY (user_id, anime_id)
        )
    """)

    # Таблица каталога аниме (автоматическое добавление)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anime_catalog (
            message_id INTEGER PRIMARY KEY,
            anime_key TEXT,
            title TEXT,
            season_id INTEGER,
            episode_num INTEGER,
            quality TEXT,
            dubbing TEXT,
            added_at TEXT
        )
    """)

    # Таблица избранного (favorites)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            anime_key TEXT,
            added_at TEXT,
            PRIMARY KEY (user_id, anime_key)
        )
    """)

    # Таблица хэштегов аниме (для точного связывания)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anime_hashtags (
            hashtag TEXT PRIMARY KEY,
            anime_key TEXT NOT NULL,
            anime_title TEXT NOT NULL
        )
    """)

    # Миграция: Проверка и добавление колонок в anime_catalog
    cursor.execute("PRAGMA table_info(anime_catalog)")
    catalog_cols = [col[1] for col in cursor.fetchall()]
    if "is_filler" not in catalog_cols:
        cursor.execute("ALTER TABLE anime_catalog ADD COLUMN is_filler INTEGER DEFAULT 0")
    if "source_channel" not in catalog_cols:
        cursor.execute("ALTER TABLE anime_catalog ADD COLUMN source_channel TEXT")

    conn.commit()
    conn.close()


def add_user(user_id, username=None, full_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Используем INSERT OR REPLACE для обновления имен если пользователь уже есть
    cursor.execute("""
        INSERT INTO users (user_id, username, full_name, join_date) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            username = excluded.username,
            full_name = excluded.full_name
    """, (user_id, username, full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_all_users():
    """Получить список ID всех пользователей (для обратной совместимости)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]


def get_all_users_info():
    """Получить список всех пользователей с их именами"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name FROM users")
    users = cursor.fetchall()
    conn.close()
    # Возвращаем список словарей
    return [{"user_id": u[0], "username": u[1], "full_name": u[2]} for u in users]


def increment_request(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET requests_count = requests_count + 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def get_user_info(user_id):
    """Получить детальную информацию о конкретном пользователе"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, full_name, join_date, requests_count,
balance, xp, level, last_daily, referred_by, game_balance
        FROM users WHERE user_id = ?
    """, (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "user_id": res[0],
            "username": res[1],
            "full_name": res[2],
            "join_date": res[3],
            "requests_count": res[4],
            "balance": res[5],
            "xp": res[6],
            "level": res[7],
            "last_daily": res[8],
            "referred_by": res[9],
            "game_balance": res[10]
        }
    return None


def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_game_balance(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET game_balance = game_balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def add_xp(user_id, amount):
    """Добавить XP и повысить уровень при достижении порога"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False

    current_xp, current_level = res
    new_xp = current_xp + amount

    # Порог уровня: уровень * 500 XP
    threshold = current_level * 500
    level_up = False

    if new_xp >= threshold:
        new_xp -= threshold
        current_level += 1
        level_up = True

    cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, current_level, user_id))
    conn.commit()
    conn.close()
    return level_up


def check_daily(user_id):
    """Проверить, можно ли забрать бонус (раз в 24 часа)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()

    if not res or not res[0]:
        # Никогда не брал
        cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()
        return True

    last_time = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
    if (datetime.now() - last_time).total_seconds() >= 86400:
        cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def get_all_users_detailed():
    """Получить всех пользователей с балансом и уровнем для таблицы"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, level, balance FROM users ORDER BY level DESC, balance DESC")
    users = cursor.fetchall()
    conn.close()
    return users


def get_global_stats():
    """Получить глобальную статистику для админа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Всего пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Всего просмотров серий
    cursor.execute("SELECT SUM(requests_count) FROM users")
    total_views = cursor.fetchone()[0] or 0

    # Активные (хотя бы 1 просмотр)
    cursor.execute("SELECT COUNT(*) FROM users WHERE requests_count > 0")
    active_users = cursor.fetchone()[0]

    conn.close()
    return {
        "total_users": total_users,
        "total_views": total_views,
        "active_users": active_users
    }

def create_broadcast():
    """Создает запись о новой рассылке и возвращает её ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO broadcasts (sent_at) VALUES (?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    broadcast_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return broadcast_id


def save_sent_message(broadcast_id, user_id, message_id):
    """Сохраняет ID отправленного сообщения для конкретного пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sent_messages (broadcast_id, user_id, message_id) VALUES (?, ?, ?)",
        (broadcast_id, user_id, message_id)
    )
    conn.commit()
    conn.close()


def get_last_broadcast_messages():
    """Возвращает список сообщений последней рассылки для удаления"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Находим ID последней рассылки
    cursor.execute("SELECT broadcast_id FROM broadcasts ORDER BY broadcast_id DESC LIMIT 1")
    res = cursor.fetchone()
    if not res:
        conn.close()
        return []

    broadcast_id = res[0]
    cursor.execute("SELECT user_id, message_id FROM sent_messages WHERE broadcast_id = ?", (broadcast_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages


def set_anime_rating(user_id, anime_id, rating):
    """Добавляет или обновляет оценку аниме от пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_anime_ratings (user_id, anime_id, rating) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, anime_id) DO UPDATE SET rating = excluded.rating
    """, (user_id, anime_id, rating))
    conn.commit()
    conn.close()


def get_anime_rating_info(anime_id):
    """Получает среднюю оценку и количество голосов для аниме"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(rating), COUNT(rating) 
        FROM user_anime_ratings WHERE anime_id = ?
    """, (anime_id,))
    res = cursor.fetchone()
    conn.close()
    if res and res[1] > 0:
        return {"avg": round(res[0], 1), "count": res[1]}
    return {"avg": 0, "count": 0}


def get_top_anime(limit=10):
    """Возвращает топ аниме по среднему рейтингу"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Сортируем по среднему баллу, а при равенстве — по количеству голосов
    cursor.execute("""
        SELECT anime_id, AVG(rating) as avg_rating, COUNT(rating) as vote_count
        FROM user_anime_ratings
        GROUP BY anime_id
        ORDER BY avg_rating DESC, vote_count DESC
        LIMIT ?
    """, (limit,))
    res = cursor.fetchall()
    conn.close()
    return res


# --- НОВЫЕ ФУНКЦИИ ДЛЯ НАСТРОЕК И ИСТОРИИ ---

def update_user_setting(user_id, setting_name, value):
    """Универсальное обновление настроек пользователя с защитой от SQL-инъекций"""
    allowed_columns = {"username", "full_name", "history_interval", "balance", "xp", "level", "last_daily", "referred_by", "game_balance", "is_banned"}
    if setting_name not in allowed_columns:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {setting_name} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()
    return True


def add_view_history(user_id, anime_id, episode_id):
    """Добавить запись в историю просмотров"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO view_history (user_id, anime_id, episode_id, viewed_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, anime_id, episode_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def clear_expired_history():
    """Очистка старой истории на основе настроек пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем интервалы для каждого пользователя
    cursor.execute("SELECT user_id, history_interval FROM users WHERE history_interval != 'never'")
    users_settings = cursor.fetchall()
    
    for user_id, interval in users_settings:
        if interval == "1day":
            time_limit = "1 day"
        elif interval == "2weeks":
            time_limit = "14 days"
        else:
            continue
            
        cursor.execute(f"""
            DELETE FROM view_history 
            WHERE user_id = ? 
            AND viewed_at < datetime('now', '-{time_limit}', 'localtime')
        """, (user_id,))
    
    conn.commit()
    conn.close()


def get_user_history(user_id, limit=5):
    """Получить последние просмотры пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT anime_id, episode_id, viewed_at 
        FROM view_history WHERE user_id = ? 
        ORDER BY viewed_at DESC LIMIT ?
    """, (user_id, limit))
    res = cursor.fetchall()
    conn.close()
    return res


# --- ФУНКЦИИ ДЛЯ АВТОМАТИЧЕСКОГО КАТАЛОГА ---

def add_dynamic_episode(message_id, anime_key, title, season_id, episode_num, quality, dubbing, is_filler=0, arc_name=None, source_channel=None):
    """Добавить или обновить серию в динамическом каталоге"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Динамически добавляем колонки arc_name и source_channel, если их ещё нет в БД
    cursor.execute("PRAGMA table_info(anime_catalog)")
    cols = [col[1] for col in cursor.fetchall()]
    if "arc_name" not in cols:
        try:
            cursor.execute("ALTER TABLE anime_catalog ADD COLUMN arc_name TEXT")
            conn.commit()
        except Exception:
            pass
    if "source_channel" not in cols:
        try:
            cursor.execute("ALTER TABLE anime_catalog ADD COLUMN source_channel TEXT")
            conn.commit()
        except Exception:
            pass

    cursor.execute("""
        INSERT INTO anime_catalog (message_id, anime_key, title, season_id, episode_num, quality, dubbing, is_filler, arc_name, source_channel, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            anime_key = excluded.anime_key,
            title = excluded.title,
            season_id = excluded.season_id,
            episode_num = excluded.episode_num,
            quality = excluded.quality,
            dubbing = excluded.dubbing,
            is_filler = excluded.is_filler,
            arc_name = excluded.arc_name,
            source_channel = excluded.source_channel
    """, (message_id, anime_key, title, season_id, episode_num, quality, dubbing, is_filler, arc_name, source_channel, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_dynamic_episodes(anime_key, season_id, dubbing=None, arc_name=None, exclude_480p=True):
    """Получить список серий из БД для конкретного аниме, сезона, озвучки и арки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT message_id, episode_num, is_filler FROM anime_catalog WHERE anime_key = ? AND season_id = ?"
    params = [anime_key, season_id]
    
    if exclude_480p:
        query += " AND (quality IS NULL OR quality NOT LIKE '%480%')"
        
    if dubbing:
        query += " AND dubbing LIKE ? COLLATE NOCASE"
        params.append(f"%{dubbing}%")
        
    if arc_name:
        query += " AND arc_name = ?"
        params.append(arc_name)
        
    query += " ORDER BY episode_num ASC"
    
    cursor.execute(query, params)
    res = cursor.fetchall()
    conn.close()
    return res

def get_4k_episode(anime_key, episode_num):
    """Возвращает message_id 4K-версии серии, если она существует в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_id FROM anime_catalog
        WHERE anime_key = ? AND episode_num = ? AND (quality LIKE '%4K%' OR dubbing LIKE '%4K%' OR dubbing LIKE '%4к%')
        LIMIT 1
    """, (anime_key, episode_num))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_hd_episode(anime_key, episode_num, dubbing=None):
    """Возвращает message_id обычного HD/1080p/720p качества серии"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT message_id FROM anime_catalog WHERE anime_key = ? AND episode_num = ? AND (quality IS NULL OR quality NOT LIKE '%4K%')"
    params = [anime_key, episode_num]
    if dubbing:
        query += " AND dubbing LIKE ? COLLATE NOCASE"
        params.append(f"%{dubbing}%")
    query += " LIMIT 1"
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_season_title(anime_key, season_id, dub_name=None):
    """Возвращает title для первого найденного эпизода в сезоне (можно фильтровать по озвучке)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if dub_name:
        cursor.execute("""
            SELECT title FROM anime_catalog 
            WHERE anime_key = ? AND season_id = ? AND dubbing LIKE ? COLLATE NOCASE
            LIMIT 1
        """, (anime_key, season_id, f"%{dub_name}%"))
    else:
        cursor.execute("""
            SELECT title FROM anime_catalog 
            WHERE anime_key = ? AND season_id = ? 
            LIMIT 1
        """, (anime_key, season_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_or_create_season_id_for_arc(anime_key, arc_name, dubbing, max_static_season=1):
    """Находит существующий season_id для этой арки и этой озвучки, или создает новый (max + 1)"""
    if not arc_name:
        return 1
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ищем по полю arc_name (приоритет) — точный поиск по названию арки
    cursor.execute("PRAGMA table_info(anime_catalog)")
    cols = [col[1] for col in cursor.fetchall()]
    if "arc_name" in cols:
        cursor.execute("""
            SELECT season_id FROM anime_catalog 
            WHERE anime_key = ? AND dubbing LIKE ? COLLATE NOCASE AND arc_name = ? COLLATE NOCASE
            LIMIT 1
        """, (anime_key, f"%{dubbing}%", arc_name))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]

    # Fallback: ищем по title (старый формат)
    cursor.execute("""
        SELECT season_id FROM anime_catalog 
        WHERE anime_key = ? AND dubbing LIKE ? COLLATE NOCASE AND (title LIKE ? OR title LIKE ?)
        LIMIT 1
    """, (anime_key, f"%{dubbing}%", f"%— {arc_name}%", f"%арка: {arc_name}%"))
    
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]
        
    # Если для этой озвучки нет, берем максимальный season_id для этой озвучки у этого аниме в БД
    cursor.execute("""
        SELECT MAX(season_id) FROM anime_catalog 
        WHERE anime_key = ? AND dubbing LIKE ? COLLATE NOCASE
    """, (anime_key, f"%{dubbing}%"))
    max_row = cursor.fetchone()
    max_db_season = max_row[0] if max_row and max_row[0] is not None else 0
    
    conn.close()
    return max(max_db_season, max_static_season) + 1


def get_season_arc_name(anime_key, season_id, dub_name=None):
    """Возвращает название арки для сезона из поля arc_name (для аниме без сезонов, только с арками)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Проверяем наличие колонки arc_name
    cursor.execute("PRAGMA table_info(anime_catalog)")
    cols = [col[1] for col in cursor.fetchall()]
    if "arc_name" not in cols:
        conn.close()
        return None
    if dub_name:
        cursor.execute("""
            SELECT arc_name FROM anime_catalog 
            WHERE anime_key = ? AND season_id = ? AND dubbing LIKE ? COLLATE NOCASE
            AND arc_name IS NOT NULL AND arc_name != ''
            LIMIT 1
        """, (anime_key, season_id, f"%{dub_name}%"))
    else:
        cursor.execute("""
            SELECT arc_name FROM anime_catalog 
            WHERE anime_key = ? AND season_id = ?
            AND arc_name IS NOT NULL AND arc_name != ''
            LIMIT 1
        """, (anime_key, season_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_dynamic_seasons(anime_key, dubbing=None):
    """Получить список доступных сезонов для аниме из БД, отсортированный по первой серии"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if dubbing:
        cursor.execute("""
            SELECT season_id FROM anime_catalog 
            WHERE anime_key = ? AND dubbing LIKE ? COLLATE NOCASE
            GROUP BY season_id
            ORDER BY MIN(episode_num) ASC
        """, (anime_key, f"%{dubbing}%"))
    else:
        cursor.execute("""
            SELECT season_id FROM anime_catalog 
            WHERE anime_key = ?
            GROUP BY season_id
            ORDER BY MIN(episode_num) ASC
        """, (anime_key,))
    
    res = cursor.fetchall()
    conn.close()
    return [row[0] for row in res]

def get_season_min_episodes(anime_key):
    """Возвращает словарь {season_id: min_episode} для сортировки сезонов"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT season_id, MIN(episode_num) 
        FROM anime_catalog 
        WHERE anime_key = ?
        GROUP BY season_id
    """, (anime_key,))
    res = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in res}

def get_episode_metadata(message_id):
    """Получить информацию о серии по ID сообщения"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Проверяем наличие колонки source_channel
    cursor.execute("PRAGMA table_info(anime_catalog)")
    cols = [col[1] for col in cursor.fetchall()]
    if "source_channel" in cols:
        cursor.execute("SELECT anime_key, title, season_id, episode_num, quality, dubbing, source_channel FROM anime_catalog WHERE message_id = ?", (message_id,))
    else:
        cursor.execute("SELECT anime_key, title, season_id, episode_num, quality, dubbing FROM anime_catalog WHERE message_id = ?", (message_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        meta = {
            "anime_key": res[0],
            "title": res[1],
            "season_id": res[2],
            "episode_num": res[3],
            "quality": res[4],
            "dubbing": res[5]
        }
        if "source_channel" in cols and len(res) > 6:
            meta["source_channel"] = res[6]
        return meta
    return None

def get_all_dynamic_anime_keys():
    """Получить все уникальные аниме из динамического каталога (ключ + название)"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT anime_key, title FROM anime_catalog
            GROUP BY anime_key
            ORDER BY title ASC
        """)
        res = cursor.fetchall()
    except Exception:
        res = []
    conn.close()
    return res  # [(anime_key, title), ...]

def get_anime_with_dubs():
    """Возвращает все аниме с их озвучками одним запросом.
    Результат: {anime_key: {"title": str, "dubs": [dub1, dub2, ...]}}
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT anime_key, title, dubbing
            FROM anime_catalog
            GROUP BY anime_key, dubbing
            ORDER BY title ASC, dubbing ASC
        """)
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()

    result = {}
    for anime_key, title, dub in rows:
        if anime_key not in result:
            result[anime_key] = {"title": title, "dubs": []}
        if dub and dub not in result[anime_key]["dubs"]:
            result[anime_key]["dubs"].append(dub)
    return result

def get_dynamic_dubs(anime_key):
    """Получить список доступных озвучек для аниме из БД"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT dubbing FROM anime_catalog 
            WHERE anime_key = ?
            ORDER BY dubbing COLLATE NOCASE ASC
        """, (anime_key,))
        res = cursor.fetchall()
    except Exception:
        res = []
    conn.close()
    return [row[0] for row in res if row[0]]


# --- ФУНКЦИИ УДАЛЕНИЯ ИЗ КАТАЛОГА ---

def delete_episode(message_id: int) -> bool:
    """Удалить одну серию по message_id. Возвращает True если удалено."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM anime_catalog WHERE message_id = ?", (message_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def delete_anime(anime_key: str) -> int:
    """Удалить всё аниме (все серии всех озвучек всех сезонов) по ключу.
    Возвращает количество удалённых серий."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM anime_catalog WHERE anime_key = ?", (anime_key,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_dubbing(anime_key: str, dubbing: str) -> int:
    """Удалить все серии конкретной озвучки у аниме.
    Возвращает количество удалённых серий."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM anime_catalog WHERE anime_key = ? AND dubbing LIKE ? COLLATE NOCASE",
        (anime_key, f"%{dubbing}%")
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def clear_catalog() -> int:
    """Полностью очистить весь динамический каталог (таблицу anime_catalog).
    Возвращает количество удалённых записей."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM anime_catalog")
    count = cursor.fetchone()[0]
    cursor.execute("DELETE FROM anime_catalog")
    conn.commit()
    conn.close()
    return count


def get_catalog_stats() -> dict:
    """Получить статистику каталога: кол-во аниме, серий, озвучек."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT anime_key) FROM anime_catalog")
    anime_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM anime_catalog")
    ep_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT dubbing) FROM anime_catalog")
    dub_count = cursor.fetchone()[0]
    conn.close()
    return {"anime": anime_count, "episodes": ep_count, "dubs": dub_count}


# ==========================================
# ФУНКЦИИ ДЛЯ ИЗБРАННОГО (FAVORITES)
# ==========================================
def add_to_favorites(user_id: int, anime_key: str):
    """Добавить аниме в избранное"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO favorites (user_id, anime_key, added_at)
        VALUES (?, ?, ?)
    """, (user_id, anime_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def remove_from_favorites(user_id: int, anime_key: str):
    """Удалить аниме из избранного"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM favorites WHERE user_id = ? AND anime_key = ?
    """, (user_id, anime_key))
    conn.commit()
    conn.close()


def is_favorite(user_id: int, anime_key: str) -> bool:
    """Проверить, находится ли аниме в избранном"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM favorites WHERE user_id = ? AND anime_key = ? LIMIT 1
    """, (user_id, anime_key))
    res = cursor.fetchone()
    conn.close()
    return res is not None


def get_favorites(user_id: int) -> list:
    """Получить список всех избранных аниме пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT anime_key FROM favorites WHERE user_id = ? ORDER BY added_at DESC
    """, (user_id,))
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res


# ==========================================
# ФУНКЦИИ ДЛЯ ИСТОРИИ И ПРОДОЛЖЕНИЯ ПРОСМОТРА
# ==========================================
def add_to_history(user_id: int, anime_key: str, season_id: int, episode_num: int):
    """Добавить просмотр серии в историю. Если запись уже есть — обновляем время."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Так как у нас в view_history есть AUTOINCREMENT id, мы просто вставим новую запись
    cursor.execute("""
        INSERT INTO view_history (user_id, anime_id, episode_id, viewed_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, anime_key, f"{season_id}:{episode_num}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_last_watched(user_id: int) -> dict | None:
    """Возвращает последнее просмотренное аниме, его сезон и серию"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Достаем последнюю запись из view_history
    cursor.execute("""
        SELECT anime_id, episode_id FROM view_history
        WHERE user_id = ? AND anime_id IS NOT NULL AND episode_id IS NOT NULL
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        anime_key, ep_str = row
        try:    
            season_id, episode_num = map(int, ep_str.split(":"))
            return {
                "anime_key": anime_key,
                "season_id": season_id,
                "episode_num": episode_num
            }
        except ValueError:
            return None
    return None


# --- ФУНКЦИИ ДЛЯ ХЭШТЕГОВ АНИМЕ ---

def add_anime_hashtag(hashtag, anime_key, anime_title):
    """Добавить или обновить соответствие хэштега и ключа аниме"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO anime_hashtags (hashtag, anime_key, anime_title)
        VALUES (?, ?, ?)
        ON CONFLICT(hashtag) DO UPDATE SET
            anime_key = excluded.anime_key,
            anime_title = excluded.anime_title
    """, (hashtag.lower().strip(), anime_key.strip(), anime_title.strip()))
    conn.commit()
    conn.close()

def get_anime_key_by_hashtag(hashtag):
    """Получить anime_key и anime_title по хэштегу"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT anime_key, anime_title FROM anime_hashtags WHERE hashtag = ?
    """, (hashtag.lower().strip(),))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"anime_key": res[0], "anime_title": res[1]}
    return None

def delete_anime_hashtag(hashtag):
    """Удалить соответствие хэштега"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM anime_hashtags WHERE hashtag = ?
    """, (hashtag.lower().strip(),))
    rowcount = cursor.rowcount
    conn.commit()
    conn.close()
    return rowcount

def get_all_anime_hashtags():
    """Получить все зарегистрированные хэштеги"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT hashtag, anime_key, anime_title FROM anime_hashtags ORDER BY hashtag ASC")
    res = cursor.fetchall()
    conn.close()
    return res


def has_episodes_without_arc(anime_key, season_id, dubbing=None):
    """Проверяет, есть ли в этом сезоне серии без арки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if dubbing:
        cursor.execute("""
            SELECT 1 FROM anime_catalog
            WHERE anime_key = ? AND season_id = ? AND (arc_name IS NULL OR arc_name = '') AND dubbing LIKE ? COLLATE NOCASE
            LIMIT 1
        """, (anime_key, season_id, f"%{dubbing}%"))
    else:
        cursor.execute("""
            SELECT 1 FROM anime_catalog
            WHERE anime_key = ? AND season_id = ? AND (arc_name IS NULL OR arc_name = '')
            LIMIT 1
        """, (anime_key, season_id))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def get_dynamic_arcs(anime_key, season_id, dubbing=None):
    """Получить уникальные названия арок для конкретного аниме, сезона и озвучки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем, существует ли вообще колонка arc_name в БД
    cursor.execute("PRAGMA table_info(anime_catalog)")
    cols = [col[1] for col in cursor.fetchall()]
    if "arc_name" not in cols:
        conn.close()
        return []

    if dubbing:
        cursor.execute("""
            SELECT arc_name FROM anime_catalog
            WHERE anime_key = ? AND season_id = ? AND arc_name IS NOT NULL AND arc_name != '' AND dubbing LIKE ? COLLATE NOCASE
            GROUP BY arc_name
            ORDER BY min(episode_num) ASC
        """, (anime_key, season_id, f"%{dubbing}%"))
    else:
        cursor.execute("""
            SELECT arc_name FROM anime_catalog
            WHERE anime_key = ? AND season_id = ? AND arc_name IS NOT NULL AND arc_name != ''
            GROUP BY arc_name
            ORDER BY min(episode_num) ASC
        """, (anime_key, season_id))
    res = cursor.fetchall()
    conn.close()
    return [row[0] for row in res if row[0]]
