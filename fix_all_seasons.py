import sqlite3
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("SELECT message_id, anime_key, title, season_id FROM anime_catalog")
rows = cursor.fetchall()

fixed_count = 0

# --- ЭТАП 1: Убираем "(Название на английском)" из конца заголовков ---
for msg_id, key, title, s_id in rows:
    clean = re.sub(r'\s*\([A-Za-z0-9:!?.\-_ ]+\)\s*$', '', title).strip()
    # Убираем 🔞 и другие спецсимволы
    clean = clean.replace('🔞', '').strip()
    if clean != title and clean:
        cursor.execute("UPDATE anime_catalog SET title = ? WHERE message_id = ?", (clean, msg_id))
        fixed_count += 1

conn.commit()
print(f"Этап 1 (Убраны английские подписи): {fixed_count} серий")

# --- ЭТАП 2: Перечитываем базу заново, ищем аниме с подзаголовком после ":" ---
cursor.execute("SELECT DISTINCT title, anime_key FROM anime_catalog")
all_titles = cursor.fetchall()

# Строим словарь: базовое название -> список всех вариантов
base_map = {}
for title, key in all_titles:
    base = title.split(':')[0].strip()
    if base not in base_map:
        base_map[base] = []
    if title not in base_map[base]:
        base_map[base].append(title)

# Найдём группы с 2+ разными вариантами
merged_ep_count = 0
merged_anime_count = 0
for base, variants in base_map.items():
    if len(variants) < 2:
        continue
    if len(base) < 5:  # слишком короткое base-название — пропускаем
        continue
    
    # Всем вариантам назначаем:
    # 1. Общее название = base
    # 2. Правильный season_id основываясь на порядке (вариант без : = 1, потом 2, 3...)
    # Но только если base аниме уже есть в списке (вариант без подзаголовка существует)
    has_base = base in variants
    
    for idx, variant in enumerate(variants):
        cursor.execute("SELECT DISTINCT anime_key FROM anime_catalog WHERE title = ?", (variant,))
        keys = [r[0] for r in cursor.fetchall()]
        
        # Определяем правильный ключ (тот что без суффиксов)
        base_key = min(keys, key=len) if keys else None
        
        if variant == base:
            new_season = 1
        else:
            # Пытаемся выдать нормальный номер сезона из подзаголовка
            # Например: "Клинок: Квартал" -> смотрим порядок в списке
            sub = variant.split(':', 1)[-1].strip() if ':' in variant else ''
            
            # Ищем числа в подзаголовке
            nums = re.findall(r'\d+', sub)
            if nums:
                new_season = int(nums[-1])  # берем последнюю цифру
                if new_season > 20:
                    new_season = idx + (1 if has_base else 0)
            else:
                new_season = idx + (1 if has_base else 0)
            
            if new_season == 0:
                new_season = 1
        
        # Обновляем все серии
        cursor.execute("""
            UPDATE anime_catalog 
            SET title = ?, anime_key = ?, season_id = ?
            WHERE title = ? AND anime_key = ?
        """, (base, base_key, new_season, variant, keys[0] if keys else ''))
        
        count = cursor.rowcount
        if count > 0 and variant != base:
            merged_ep_count += count
            print(f"  '{variant}' -> '{base}' (Сезон {new_season}) — {count} серий")

    if any(v != base for v in variants):
        merged_anime_count += 1

conn.commit()
print(f"\nЭтап 2 (Объединены подзаголовки): {merged_ep_count} серий, {merged_anime_count} аниме!")

# --- ЭТАП 3: Убираем "X сезон" из конца названия и обновляем season_id ---
cursor.execute("SELECT message_id, anime_key, title, season_id FROM anime_catalog")
rows = cursor.fetchall()

season_fixed = 0
for msg_id, key, title, s_id in rows:
    match = re.search(r'\s+(\d+)\s+сезон\s*$', title, re.IGNORECASE)
    if match:
        new_season = int(match.group(1))
        clean = re.sub(r'\s+\d+\s+сезон\s*$', '', title, flags=re.IGNORECASE).strip()
        if clean and (s_id != new_season or title != clean):
            cursor.execute("UPDATE anime_catalog SET season_id = ?, title = ? WHERE message_id = ?", (new_season, clean, msg_id))
            season_fixed += 1

conn.commit()
print(f"Этап 3 (Убраны 'X сезон'): {season_fixed} серий")

# --- ЭТАП 4: Финальное слияние дубликатов ключей ---
cursor.execute("SELECT DISTINCT title, anime_key FROM anime_catalog")
title_keys = {}
for title, key in cursor.fetchall():
    if title not in title_keys:
        title_keys[title] = []
    if key not in title_keys[title]:
        title_keys[title].append(key)

merged_keys = 0
for title, keys in title_keys.items():
    if len(keys) > 1:
        base_key = min(keys, key=len)
        cursor.execute("UPDATE anime_catalog SET anime_key = ? WHERE title = ?", (base_key, title))
        merged_keys += 1

conn.commit()
conn.close()
print(f"Этап 4 (Финальное слияние ключей): {merged_keys} аниме!")
print("\n✅ Полная очистка базы данных завершена!")
