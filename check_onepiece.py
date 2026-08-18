import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Найти все записи Ванпис/One Piece
c.execute("SELECT DISTINCT anime_key, title FROM anime_catalog WHERE title LIKE '%анпис%' OR title LIKE '%One Piece%' OR anime_key LIKE '%one_piece%' OR anime_key LIKE '%vanpis%'")
rows = c.fetchall()
print("--- Ванпис в базе ---")
for r in rows:
    print(r)

# Посчитать серий
for key, title in rows:
    c.execute("SELECT COUNT(*) FROM anime_catalog WHERE anime_key = ?", (key,))
    cnt = c.fetchone()[0]
    print(f"  {key}: {cnt} серий")

conn.close()
