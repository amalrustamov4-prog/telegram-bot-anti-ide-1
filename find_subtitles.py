import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT DISTINCT title, anime_key FROM anime_catalog")
titles = c.fetchall()

# Simple logic to group titles based on common prefix (e.g. before colon)
groups = {}
for title, key in titles:
    if ':' in title:
        base = title.split(':')[0].strip()
    elif ' — ' in title:
        base = title.split(' — ')[0].strip()
    elif ' - ' in title:
        base = title.split(' - ')[0].strip()
    else:
        # Just use first 3 words as a heuristic
        words = title.split()
        if len(words) >= 3:
            base = ' '.join(words[:3])
        else:
            base = title
    
    if base not in groups:
        groups[base] = set()
    groups[base].add(title)

print(f"Found {len(groups)} potential groups. Showing ones with multiple distinct titles:")
for base, t_set in groups.items():
    if len(t_set) > 1:
        print(f"\n--- {base} ---")
        for t in t_set:
            print(f"  {t}")
