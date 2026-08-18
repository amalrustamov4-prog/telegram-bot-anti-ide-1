import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Считаем сколько серий Ванпис
c.execute("SELECT COUNT(*) FROM anime_catalog WHERE anime_key = 'op_elbaf'")
cnt = c.fetchone()[0]
print(f"Ванпис в базе: {cnt} серий")

# Удаляем ВСЕ записи Ванпис из базы
c.execute("DELETE FROM anime_catalog WHERE anime_key = 'op_elbaf'")
deleted = c.rowcount
conn.commit()

# Также удаляем из хэштегов если есть
c.execute("DELETE FROM anime_hashtags WHERE anime_key = 'op_elbaf'")
conn.commit()
conn.close()

print(f"✅ Удалено {deleted} серий Ванпис из базы данных!")
print("Теперь при миграции из @shachiburi_one_piece Ванпис зайдёт с нуля.")
