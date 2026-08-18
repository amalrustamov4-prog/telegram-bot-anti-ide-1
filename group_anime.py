import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# 1. Группируем все "Магическая битва" в один ключ "jjk" с чистым названием
jjk_keys = ['anime_magicheskaya', 'magicheskaya_bitva_3', 'magicheskaya_bitva_j', 'magicheskaya_bitva_2']

cursor.execute(f"UPDATE anime_catalog SET anime_key = 'jjk', title = 'Магическая битва' WHERE anime_key IN ({','.join(['?']*len(jjk_keys))})", jjk_keys)
updated_jjk = cursor.rowcount

# Также обновим те, которые уже 'jjk', чтобы у всех было одинаковое название
cursor.execute("UPDATE anime_catalog SET title = 'Магическая битва' WHERE anime_key = 'jjk'")

# 2. Адский рай
cursor.execute("UPDATE anime_catalog SET anime_key = 'hellas', title = 'Адский рай' WHERE title LIKE '%Адский рай%'")
updated_hells = cursor.rowcount

# 3. Убираем эмодзи из всех названий (чтобы в меню всё было красиво и группировалось)
cursor.execute("SELECT message_id, title FROM anime_catalog")
rows = cursor.fetchall()
cleaned = 0
for msg_id, title in rows:
    new_title = title.replace("🌸 Аниме: ", "").replace("🎬", "").replace("🔥", "").strip()
    if new_title != title:
        cursor.execute("UPDATE anime_catalog SET title = ? WHERE message_id = ?", (new_title, msg_id))
        cleaned += 1

conn.commit()
conn.close()

logging.info(f"✅ Успешно сгруппировано {updated_jjk} серий 'Магической битвы' в один каталог!")
logging.info(f"✅ Успешно сгруппировано {updated_hells} серий 'Адский рай'.")
logging.info(f"🧹 Очищено от лишних символов (эмодзи) {cleaned} названий аниме.")
logging.info("\nТеперь в каталоге бота они будут отображаться под одной кнопкой с выбором сезонов и озвучек!")
