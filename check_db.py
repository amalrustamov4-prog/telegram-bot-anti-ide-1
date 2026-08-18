import sqlite3

conn = sqlite3.connect('users.db')
conn.text_factory = str  # Force text mode
cursor = conn.cursor()

# Check encoding
cursor.execute("SELECT message_id, anime_key, season_id, arc_name, title, dubbing FROM anime_catalog WHERE anime_key='op_elbaf' ORDER BY season_id LIMIT 20")
rows = cursor.fetchall()
print("One Piece records (raw):")
for r in rows:
    try:
        print(f"  msg_id={r[0]}, season_id={r[2]}, arc_name={repr(r[3])}, title={repr(r[4])}, dub={r[5]}")
    except Exception as e:
        print(f"  Error printing row: {e}")

conn.close()
