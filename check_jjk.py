import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT DISTINCT season_id, title FROM anime_catalog WHERE anime_key = 'jjk'")
print(c.fetchall())
