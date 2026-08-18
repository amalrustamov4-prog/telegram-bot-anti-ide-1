import sqlite3
import sys

# Change console encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute("SELECT DISTINCT anime_key, title, dubbing FROM anime_catalog")
rows = c.fetchall()

print("--- Магическая битва ---")
for r in rows:
    if 'магическая' in r[1].lower():
        print(r)

print("\n--- Адский рай ---")
for r in rows:
    if 'адский' in r[1].lower() or 'рай' in r[1].lower():
        print(r)

print("\n--- Наруто ---")
for r in rows:
    if 'наруто' in r[1].lower():
        print(r)
