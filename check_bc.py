import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute("SELECT message_id, title, season_id, episode_num, dubbing FROM anime_catalog WHERE anime_key='black_clover' ORDER BY message_id DESC LIMIT 5")
rows = cursor.fetchall()
print('Recent Black Clover episodes:')
for r in rows:
    print(str(r).encode('utf-8'))
conn.close()
