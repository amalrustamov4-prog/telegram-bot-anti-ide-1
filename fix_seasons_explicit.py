import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("SELECT message_id, anime_key, title, season_id FROM anime_catalog")
rows = cursor.fetchall()

fixed_count = 0
for msg_id, key, title, s_id in rows:
    # Ищем " 2 сезон" или " 4 сезон" в названии
    match = re.search(r'\s+(\d+)\s+сезон\s*$', title, re.IGNORECASE)
    
    if match:
        new_season = int(match.group(1))
        # Убираем "X сезон" из названия
        clean_title = re.sub(r'\s+\d+\s+сезон\s*$', '', title, flags=re.IGNORECASE).strip()
        
        # Обновляем сезон и очищаем название
        if s_id != new_season or title != clean_title:
            cursor.execute("""
                UPDATE anime_catalog 
                SET season_id = ?, title = ? 
                WHERE message_id = ?
            """, (new_season, clean_title, msg_id))
            fixed_count += 1

conn.commit()

# Сливаем ключи для тех аниме, у которых стало одинаковое название
cursor.execute("SELECT DISTINCT title, anime_key FROM anime_catalog")
title_keys = {}
for title, key in cursor.fetchall():
    if title not in title_keys:
        title_keys[title] = []
    title_keys[title].append(key)

merged_keys = 0
for title, keys in title_keys.items():
    if len(keys) > 1:
        base_key = min(keys, key=len)
        cursor.execute("UPDATE anime_catalog SET anime_key = ? WHERE title = ?", (base_key, title))
        merged_keys += 1

# --- Особые случаи (Ручная привязка сезонов для Клинка) ---
demon_slayer_mappings = {
    "Клинок, рассекающий демонов (Kimetsu no Yaiba)": (1, "Клинок, рассекающий демонов"),
    "Клинок, рассекающий демонов: Квартал красных фонарей (Kimetsu no Yaiba: Yuukaku-hen)": (2, "Клинок, рассекающий демонов"),
    "Клинок, рассекающий демонов: Деревня кузнецов (Kimetsu no Yaiba: Katanakaji no Sato-hen)": (3, "Клинок, рассекающий демонов"),
    "Клинок, рассекающий демонов: Тренировка столпов": (4, "Клинок, рассекающий демонов"),
    "Клинок, рассекающий демонов: Бесконечный замок": (5, "Клинок, рассекающий демонов"),
}

for old_title, (s_num, new_title) in demon_slayer_mappings.items():
    cursor.execute("""
        UPDATE anime_catalog 
        SET season_id = ?, title = ?, anime_key = 'anime_klinok_rassek'
        WHERE title = ?
    """, (s_num, new_title, old_title))
    if cursor.rowcount > 0:
        fixed_count += cursor.rowcount
        merged_keys += 1

# Реинкарнация безработного (убираем подзаголовок у 1 сезона)
cursor.execute("""
    UPDATE anime_catalog
    SET title = 'Реинкарнация безработного', anime_key = 'anime_reinkarnatsiy'
    WHERE title LIKE 'Реинкарнация безработного:%'
""")

conn.commit()
conn.close()

logging.info(f"\n✅ Исправлено сезонов (со словом 'сезон' и Клинком): {fixed_count} серий!")
logging.info(f"✅ Успешно сгруппировано дополнительных аниме: {merged_keys}!")
