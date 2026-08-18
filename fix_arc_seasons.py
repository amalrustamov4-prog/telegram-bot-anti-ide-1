"""
Скрипт для исправления season_id для аниме с арками (Ванпис).
Объединяет все серии одной арки под одним season_id.
"""
import sqlite3

DB_PATH = 'users.db'

def fix_arc_season_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем все аниме ключи у которых есть arc_name
    cursor.execute("""
        SELECT DISTINCT anime_key 
        FROM anime_catalog 
        WHERE arc_name IS NOT NULL AND arc_name != ''
    """)
    anime_keys = [r[0] for r in cursor.fetchall()]
    print(f"Найдено аниме с арками: {anime_keys}")
    
    for anime_key in anime_keys:
        # Получаем все уникальные (dubbing, arc_name) для этого аниме
        cursor.execute("""
            SELECT DISTINCT dubbing, arc_name 
            FROM anime_catalog 
            WHERE anime_key = ? AND arc_name IS NOT NULL AND arc_name != ''
            ORDER BY dubbing, arc_name
        """, (anime_key,))
        dub_arcs = cursor.fetchall()
        print(f"\n=== {anime_key} ===")
        
        # Назначаем каждой (dubbing, arc_name) уникальный season_id начиная с 1
        # Нужно выяснить максимальный статический season_id для этого аниме
        # Для op_elbaf нет статических, начинаем с 1
        arc_to_season = {}  # (dubbing, arc_name) -> season_id
        next_season = 1
        
        for dubbing, arc_name in dub_arcs:
            key = (dubbing.lower(), arc_name)
            if key not in arc_to_season:
                arc_to_season[key] = next_season
                next_season += 1
            print(f"  {dubbing} | {arc_name!r} -> season_id={arc_to_season[key]}")
        
        # Обновляем season_id в БД для каждой записи
        for (dubbing, arc_name), season_id in arc_to_season.items():
            cursor.execute("""
                UPDATE anime_catalog 
                SET season_id = ?
                WHERE anime_key = ? AND LOWER(dubbing) = ? AND arc_name = ?
            """, (season_id, anime_key, dubbing, arc_name))
            print(f"  Updated: {anime_key} | {dubbing} | {arc_name!r} -> season_id={season_id}, rows={cursor.rowcount}")
    
    conn.commit()
    
    # Проверяем результат
    print("\n=== Результат для op_elbaf ===")
    cursor.execute("""
        SELECT anime_key, season_id, arc_name, dubbing, COUNT(*) 
        FROM anime_catalog 
        WHERE anime_key='op_elbaf' 
        GROUP BY season_id, arc_name, dubbing
        ORDER BY season_id
    """)
    for r in cursor.fetchall():
        print(r)
    
    conn.close()
    print("\nГотово!")

if __name__ == "__main__":
    fix_arc_season_ids()
