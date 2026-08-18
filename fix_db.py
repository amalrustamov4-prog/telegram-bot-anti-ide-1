import sqlite3, re
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
rows = cursor.execute('SELECT message_id, anime_key, season_id, arc_name FROM anime_catalog WHERE arc_name IS NOT NULL').fetchall()
arc_map = {}
updates = 0
for mid, akey, sid, arc in rows:
    clean_arc = re.sub(r'\d+$', '', arc).replace('_', ' ').strip()
    if not clean_arc: continue
    map_key = (akey, clean_arc)
    if map_key not in arc_map:
        min_sid = cursor.execute('SELECT MIN(season_id) FROM anime_catalog WHERE anime_key=? AND arc_name LIKE ?', (akey, clean_arc+'%')).fetchone()[0]
        arc_map[map_key] = min_sid if min_sid else sid
    target_sid = arc_map[map_key]
    if sid != target_sid or arc != clean_arc:
        cursor.execute('UPDATE anime_catalog SET season_id=?, arc_name=? WHERE message_id=?', (target_sid, clean_arc, mid))
        updates += 1
conn.commit()
print(f'Updated {updates} rows')
