import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Смотрим что сейчас есть
print("--- Текущее состояние ---")
c.execute("SELECT DISTINCT title, anime_key, season_id, dubbing FROM anime_catalog WHERE title LIKE '%Ангел%'")
for r in c.fetchall():
    print(r)

# Восстанавливаем: Dream Cast -> это другое аниме "Ангел по соседству"
# AniLiberty -> "Ангел по соседству меня ужасно балует"
c.execute("""
    UPDATE anime_catalog 
    SET title = 'Ангел по соседству', 
        anime_key = 'anime_angel_po_sose'
    WHERE title LIKE '%Ангел по соседству%' AND dubbing = 'Dream Cast'
""")
print(f"\nВосстановлено Dream Cast: {c.rowcount} серий -> 'Ангел по соседству'")

# AniLiberty оставляем как есть - "Ангел по соседству меня ужасно балует"
c.execute("""
    UPDATE anime_catalog 
    SET title = 'Ангел по соседству меня ужасно балует', 
        anime_key = 'angel_po_sosedstvu_m'
    WHERE title LIKE '%Ангел по соседству%' AND dubbing != 'Dream Cast'
""")
print(f"Оставлено AniLiberty: {c.rowcount} серий -> 'Ангел по соседству меня ужасно балует'")

conn.commit()

print("\n--- Результат ---")
c.execute("SELECT DISTINCT title, anime_key, season_id, dubbing FROM anime_catalog WHERE title LIKE '%Ангел%'")
for r in c.fetchall():
    print(r)

conn.close()
