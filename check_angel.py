import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT DISTINCT title, anime_key, season_id, dubbing FROM anime_catalog WHERE title LIKE '%Ангел%' OR title LIKE '%Angel%'")
for r in c.fetchall():
    print(r)
