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
    # Ищем цифру в конце названия (например "Магическая битва 3", "Семья шпиона 2")
    # Также учитываем "Часть 2", "Часть 3" и т.д.
    match = re.search(r'(?:\s+Часть\s+|\s+)(\d+)$', title)
    
    if match:
        new_season = int(match.group(1))
        # Убираем цифру и слово "Часть" из названия
        clean_title = re.sub(r'(?:\s+Часть\s+|\s+)\d+$', '', title).strip()
        
        # Если это какой-то странный случай (типа "Тацуки Фудзимото: с 17 до 26"), пропускаем
        if new_season > 20 or new_season < 2:
            continue
            
        # Обновляем сезон и очищаем название
        if s_id != new_season or title != clean_title:
            cursor.execute("""
                UPDATE anime_catalog 
                SET season_id = ?, title = ? 
                WHERE message_id = ?
            """, (new_season, clean_title, msg_id))
            fixed_count += 1
            # logging.info(f"[{title}] -> Сезон {new_season}, Название '{clean_title}'")

conn.commit()

# Теперь нужно объединить ключи для тех аниме, у которых стало одинаковое название
cursor.execute("SELECT DISTINCT title, anime_key FROM anime_catalog")
title_keys = {}
for title, key in cursor.fetchall():
    if title not in title_keys:
        title_keys[title] = []
    title_keys[title].append(key)

merged_keys = 0
for title, keys in title_keys.items():
    if len(keys) > 1:
        # Берем самый короткий ключ как основной (например, jjk вместо magicheskaya_bitva_3)
        base_key = min(keys, key=len)
        cursor.execute("UPDATE anime_catalog SET anime_key = ? WHERE title = ?", (base_key, title))
        merged_keys += 1
        logging.info(f"Объединено аниме '{title}' под ключом '{base_key}' (были ключи: {keys})")

conn.commit()
conn.close()

logging.info(f"\n✅ Исправлено сезонов у {fixed_count} серий!")
logging.info(f"✅ Успешно сгруппировано {merged_keys} разных аниме с одинаковыми названиями!")
