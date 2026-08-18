import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT DISTINCT title, season_id FROM anime_catalog WHERE title LIKE '%Клинок%' OR title LIKE '%класс превос%'")
for r in c.fetchall():
    print(r)
