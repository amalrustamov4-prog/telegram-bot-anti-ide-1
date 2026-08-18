import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Объединяем все "Ангел по соседству..." под одним ключом и правильным названием
c.execute("""
    UPDATE anime_catalog 
    SET title = 'Ангел по соседству меня ужасно балует', 
        anime_key = 'angel_po_sosedstvu_m'
    WHERE title LIKE '%Ангел по соседству%'
""")
print(f"Обновлено: {c.rowcount} серий")
conn.commit()

# Проверяем результат
c.execute("SELECT DISTINCT title, anime_key, season_id, dubbing FROM anime_catalog WHERE title LIKE '%Ангел%'")
for r in c.fetchall():
    print(r)
conn.close()
