import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

ONE_PIECE_ARCS = [
    {"name": "На заре приключений", "range": (1, 3), "is_filler": False},
    {"name": "Оранж-Таун", "range": (4, 8), "is_filler": False},
    {"name": "Деревня Сиропа", "range": (9, 18), "is_filler": False},
    {"name": "Ресторан Барати", "range": (19, 30), "is_filler": False},
    {"name": "Арлонг-Парк", "range": (31, 45), "is_filler": False},
    {"name": "История Багги", "range": (46, 47), "is_filler": False},
    {"name": "Логтаун", "range": (48, 53), "is_filler": False},
    {"name": "Апис", "range": (54, 61), "is_filler": True},
    {"name": "Реверс-Маунтин", "range": (62, 63), "is_filler": False},
    {"name": "Виски-Пик", "range": (64, 67), "is_filler": False},
    {"name": "История Коби и Хельмеппо", "range": (68, 69), "is_filler": False},
    {"name": "Литл-Гарден", "range": (70, 77), "is_filler": False},
    {"name": "Остров Драм", "range": (78, 91), "is_filler": False},
    {"name": "Алабаста", "range": (92, 130), "is_filler": False},
    {"name": "После Алабасты", "range": (131, 135), "is_filler": True},
    {"name": "Козий остров", "range": (136, 138), "is_filler": True},
    {"name": "Остров Рулука", "range": (139, 143), "is_filler": True},
    {"name": "Джая", "range": (144, 152), "is_filler": False},
    {"name": "Скайпия", "range": (153, 195), "is_filler": False},
    {"name": "G-8", "range": (196, 206), "is_filler": True},
    {"name": "Длинно-круглая земля", "range": (207, 219), "is_filler": False},
    {"name": "Океанский Сон", "range": (220, 224), "is_filler": True},
    {"name": "Возвращение Фокси", "range": (225, 228), "is_filler": False},
    {"name": "Water 7", "range": (229, 263), "is_filler": False},
    {"name": "Эниес-Лобби", "range": (264, 312), "is_filler": False},
    {"name": "После Эниес-Лобби", "range": (313, 325), "is_filler": False},
    {"name": "Ледяной Охотник", "range": (326, 336), "is_filler": True},
    {"name": "Триллер-Барк", "range": (337, 381), "is_filler": False},
    {"name": "Остров — спа", "range": (382, 384), "is_filler": True},
    {"name": "Архипелаг Сабаоди", "range": (385, 407), "is_filler": False},
    {"name": "Амазония Лили", "range": (408, 421), "is_filler": False},
    {"name": "Импел-Даун ч.1", "range": (422, 425), "is_filler": False},
    {"name": "Литл Ист Блю", "range": (426, 429), "is_filler": True},
    {"name": "Импел-Даун ч.2", "range": (430, 456), "is_filler": False},
    {"name": "Маринфорд", "range": (457, 489), "is_filler": False},
    {"name": "После Войны", "range": (490, 516), "is_filler": False},
    {"name": "Возвращение на Сабаоди", "range": (517, 526), "is_filler": False},
    {"name": "Остров Рыболюдей", "range": (527, 574), "is_filler": False},
    {"name": "Амбиции Z", "range": (575, 578), "is_filler": True},
    {"name": "Панк Хазард", "range": (579, 625), "is_filler": False},
    {"name": "Возвращение Цезаря", "range": (626, 628), "is_filler": True},
    {"name": "Дресс Роза", "range": (629, 746), "is_filler": False},
    {"name": "Серебряный рудник", "range": (747, 750), "is_filler": True},
    {"name": "Зоя", "range": (751, 779), "is_filler": False},
    {"name": "Дозорные-сверхновые", "range": (780, 782), "is_filler": True},
    {"name": "Пирожный Остров", "range": (783, 877), "is_filler": False},
    {"name": "Совет Королей", "range": (878, 889), "is_filler": False},
    {"name": "Страна Вано", "range": (890, 1085), "is_filler": False},
    {"name": "Яичная Голова", "range": (1086, 1155), "is_filler": False},
    {"name": "Эльбаф", "range": (1156, 999999), "is_filler": False},
]

def get_one_piece_arc(ep_num: int):
    """Возвращает (arc_id, arc_name, is_filler) по номеру серии"""
    for arc_idx, arc in enumerate(ONE_PIECE_ARCS, start=1):
        a_min, a_max = arc["range"]
        if a_min <= ep_num <= a_max:
            return arc_idx, arc["name"], arc["is_filler"]
            
    return len(ONE_PIECE_ARCS), ONE_PIECE_ARCS[-1]["name"], False

def normalize_dubbing(dub_raw: str, quality_raw: str):
    if not dub_raw:
        return "Shachiburi"
    d_lower = dub_raw.lower()
    
    if "макс летов" in d_lower or "макса летова" in d_lower:
        return "Субтитры (Макс Летов)"
    elif "субтитры" in d_lower or "sub" in d_lower:
        return "Субтитры"
    else:
        return "Shachiburi"

def clean_and_fix_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Удаляем невалидные серии One Piece (номера <= 0 или > 1500)
    cursor.execute("""
        DELETE FROM anime_catalog
        WHERE anime_key = 'op_elbaf' AND (episode_num <= 0 OR episode_num > 1500)
    """)
    deleted_invalid = cursor.rowcount
    print(f"🗑 Удалено невалидных записей: {deleted_invalid}")

    # 2. Обновляем все серии Ван-Пис в базе данных
    cursor.execute("""
        SELECT message_id, anime_key, title, season_id, episode_num, quality, dubbing
        FROM anime_catalog
        WHERE anime_key = 'op_elbaf' 
           OR title LIKE '%Ван%' 
           OR title LIKE '%One Piece%' 
           OR title LIKE '%Вегапанк%'
           OR anime_key LIKE '%one_piece%'
           OR anime_key = 'unknown_anime'
    """)
    rows = cursor.fetchall()
    print(f"Обработка {len(rows)} записей Ван-Пис...")

    updated_count = 0
    for message_id, anime_key, title, season_id, episode_num, quality, dubbing in rows:
        if episode_num is None or episode_num <= 0 or episode_num > 1500:
            cursor.execute("DELETE FROM anime_catalog WHERE message_id = ?", (message_id,))
            continue

        arc_id, arc_name, is_filler = get_one_piece_arc(episode_num)
        norm_dub = normalize_dubbing(dubbing, quality)
        
        norm_quality = quality or "720p"
        if "4к" in (dubbing or "").lower() or "4k" in (dubbing or "").lower() or "4к" in (quality or "").lower() or "4k" in (quality or "").lower():
            norm_quality = "4K"
        elif "1080" in (dubbing or "").lower() or "1080" in (quality or "").lower():
            norm_quality = "1080p"
        elif "480" in (dubbing or "").lower() or "480" in (quality or "").lower():
            norm_quality = "480p"

        cursor.execute("""
            UPDATE anime_catalog
            SET anime_key = 'op_elbaf',
                title = '🏴‍☠️ Ван-Пис',
                season_id = ?,
                arc_name = ?,
                dubbing = ?,
                quality = ?,
                is_filler = ?
            WHERE message_id = ?
        """, (arc_id, arc_name, norm_dub, norm_quality, 1 if is_filler else 0, message_id))
        updated_count += 1

    conn.commit()
    print(f"✅ Успешно обновлено записей Ван-Пис: {updated_count}")

    # Проверка распределения по аркам
    cursor.execute("""
        SELECT season_id, arc_name, COUNT(*), MIN(episode_num), MAX(episode_num)
        FROM anime_catalog
        WHERE anime_key = 'op_elbaf'
        GROUP BY season_id, arc_name
        ORDER BY season_id
    """)
    summary = cursor.fetchall()
    print("\n--- Итоговое распределение Ван-Пис по Аркам [1..50] ---")
    for s_id, arc, cnt, min_ep, max_ep in summary:
        print(f"[{s_id}] {arc}: {min_ep}–{max_ep} серии -> {cnt} записей в БД")

    conn.close()

if __name__ == "__main__":
    clean_and_fix_database()
