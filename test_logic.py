import sqlite3
import sys

# Add directory to sys.path to import script
import sys
sys.path.append('.')

try:
    from script import ANIME_DB, extract_arc_name
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)

anime_id = 'black_clover'
anime_info = ANIME_DB.get(anime_id)
print('anime_info season_names:', anime_info.get('season_names', {}))

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT season_id FROM anime_catalog WHERE anime_key='black_clover' AND dubbing LIKE '%Анилибрия%'")
rows = cursor.fetchall()
all_seasons_raw = [r[0] for r in rows]
print('all_seasons_raw:', all_seasons_raw)

seasons_with_names = []
for s_id in all_seasons_raw:
    s_name = None
    if s_id in all_seasons_raw and anime_info.get('is_arc_only'):
        print('is_arc_only branch')
    
    if not s_name:
        s_name = anime_info.get('season_names', {}).get(s_id, f'{s_id} сезон')
    seasons_with_names.append((s_id, s_name))

for k, v in seasons_with_names:
    print(k, str(v).encode('utf-8'))
conn.close()
