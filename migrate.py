import json
import os
import asyncio
import sqlite3
import re
import sys
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

# Импортируем единый парсер и список каналов из script.py для 100% согласованности
import database as db
from script import (
    parse_caption_to_episode,
    ANIME_SOURCE_CHANNELS,
    CHANNEL_ANIME,
    ANIME_DB,
)

# Настройки по умолчанию
DEFAULT_API_ID = 35826645
DEFAULT_API_HASH = "30c7cbf520f57160e956edccccaadee1"

TARGET_CHANNEL = CHANNEL_ANIME # "@fullforeveranime"
# Все подключенные каналы-источники (исключая сам целевой канал)
SOURCE_CHANNELS = [ch for ch in ANIME_SOURCE_CHANNELS if ch.lower() != TARGET_CHANNEL.lower()]
PROGRESS_FILE = "migration_progress.json"

def clean_api_id(val: str) -> int:
    """Очищает введенный API ID, исправляя случайную двойную вставку и валидируя диапазон 32-bit int"""
    val = val.strip().replace('"', '').replace("'", "")
    if not val:
        return DEFAULT_API_ID
    
    # Исправление двойной вставки (например, '3582664535826645' -> '35826645')
    if len(val) % 2 == 0:
        half = len(val) // 2
        if val[:half] == val[half:]:
            val = val[:half]
            
    try:
        num = int(val)
        if -2147483648 <= num <= 2147483647:
            return num
        s_num = str(num)
        if len(s_num) > 9:
            num = int(s_num[:8])
            if -2147483648 <= num <= 2147483647:
                return num
    except ValueError:
        pass
        
    return DEFAULT_API_ID

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4)

def normalize_title(title: str) -> str:
    """Удаляет лишние символы, эмодзи и приводит к нижнему регистру для надежного сравнения"""
    if not title:
        return ""
    cleaned = re.sub(r'[🌸🎬🔥✨💫⭐️📌🎥🍿]', '', title)
    cleaned = re.sub(r'^(?:аниме|anime)\s*[:\-]?\s*', '', cleaned, flags=re.I)
    cleaned = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', cleaned)
    return cleaned.lower().strip()

def get_existing_keys_from_db():
    """Собираем ключи всех серий, которые уже есть в БД users.db"""
    existing = set()
    try:
        conn = sqlite3.connect(db.DB_PATH)
        c = conn.cursor()
        c.execute("SELECT anime_key, title, season_id, episode_num, dubbing FROM anime_catalog")
        for row in c.fetchall():
            anime_key = (row[0] or '').lower().strip()
            title = normalize_title(row[1] or '')
            s_id = row[2] if row[2] is not None else 1
            ep_num = row[3] if row[3] is not None else 0
            dub = (row[4] or '').lower().strip()

            if anime_key and ep_num:
                existing.add(f"key:{anime_key}|s:{s_id}|ep:{ep_num}")
                if dub:
                    existing.add(f"key:{anime_key}|s:{s_id}|ep:{ep_num}|dub:{dub}")
            if title and ep_num:
                existing.add(f"title:{title}|s:{s_id}|ep:{ep_num}")
                if dub:
                    existing.add(f"title:{title}|s:{s_id}|ep:{ep_num}|dub:{dub}")

        conn.close()
    except Exception as e:
        print(f"⚠️ Не удалось прочитать БД: {e}")
    return existing

def is_duplicate_episode(ep_data, existing_keys):
    """Строгая проверка дубликата серии"""
    if not ep_data:
        return False

    anime_key = (ep_data.get('anime_key') or '').lower().strip()
    title = normalize_title(ep_data.get('title') or '')
    s_id = ep_data.get('season_id', 1)
    ep_num = ep_data.get('episode_num')
    dub = (ep_data.get('dubbing') or '').lower().strip()

    if not ep_num:
        return False

    # 1. Проверка по anime_key + сезон + серия
    if anime_key and f"key:{anime_key}|s:{s_id}|ep:{ep_num}" in existing_keys:
        return True

    # 2. Проверка по title + сезон + серия
    if title and f"title:{title}|s:{s_id}|ep:{ep_num}" in existing_keys:
        return True

    # 3. Проверка с озвучкой
    if dub and f"key:{anime_key}|s:{s_id}|ep:{ep_num}|dub:{dub}" in existing_keys:
        return True

    # 4. Проверка неполного совпадения по подстроке названия
    if title:
        for exist_key in existing_keys:
            if exist_key.startswith("title:") and f"|s:{s_id}|ep:{ep_num}" in exist_key:
                exist_t = exist_key.split("|")[0].replace("title:", "")
                if exist_t and title and (exist_t in title or title in exist_t):
                    return True

    return False

def add_episode_to_existing(ep_data, existing_keys):
    """Добавляет ключи серии в список существующих"""
    if not ep_data:
        return
    anime_key = (ep_data.get('anime_key') or '').lower().strip()
    title = normalize_title(ep_data.get('title') or '')
    s_id = ep_data.get('season_id', 1)
    ep_num = ep_data.get('episode_num')
    dub = (ep_data.get('dubbing') or '').lower().strip()

    if anime_key and ep_num:
        existing_keys.add(f"key:{anime_key}|s:{s_id}|ep:{ep_num}")
        if dub:
            existing_keys.add(f"key:{anime_key}|s:{s_id}|ep:{ep_num}|dub:{dub}")
    if title and ep_num:
        existing_keys.add(f"title:{title}|s:{s_id}|ep:{ep_num}")
        if dub:
            existing_keys.add(f"title:{title}|s:{s_id}|ep:{ep_num}|dub:{dub}")


async def migrate():
    print("=======================================================")
    print("🚀 Скрипт миграции аниме (100% защита от дубликатов)")
    print("=======================================================\n")
    
    api_id = int(os.getenv("API_ID", "35826645"))
    api_hash = os.getenv("API_HASH", "30c7cbf520f57160e956edccccaadee1").strip()

    print(f"🔑 Подключение к Telegram (API ID: {api_id})...")
    client = TelegramClient('migration_session', api_id, api_hash)
    await client.start()
    print("✅ Авторизация успешна!\n")

    progress = load_progress()
    existing_keys = get_existing_keys_from_db()
    print(f"📂 Загружено из базы данных: {len(existing_keys)} ключей серий")
    print(f"🎯 Целевой канал: {TARGET_CHANNEL}")
    print(f"📡 Источники ({len(SOURCE_CHANNELS)} шт.): {', '.join(SOURCE_CHANNELS)}\n")

    # --- ШАГ 1: Сканируем целевой канал @fullforeveranime, чтобы точно знать всё, что там УЖЕ есть ---
    print("🔍 Сканирую целевой канал для гарантии 0% дубликатов...")
    try:
        target_entity = await client.get_entity(TARGET_CHANNEL)
        target_messages = await client.get_messages(target_entity, limit=None)
        target_added_count = 0
        for t_msg in target_messages:
            if not isinstance(getattr(t_msg, 'media', None), MessageMediaDocument):
                continue
            t_cap = getattr(t_msg, 'message', '') or ''
            if t_cap:
                t_ep = parse_caption_to_episode(t_cap, t_msg.id, source_channel=TARGET_CHANNEL)
                if t_ep:
                    add_episode_to_existing(t_ep, existing_keys)
                    target_added_count += 1
        print(f"✅ Целевой канал проверен: найдено {target_added_count} существующих серий. База ключей обновлена!\n")
    except Exception as e:
        print(f"⚠️ Не удалось просканировать целевой канал напрямую ({e}), продолжаем с базой данных.\n")

    # --- ШАГ 2: Перенос серий из всех каналов-источников ---
    for ch in SOURCE_CHANNELS:
        if ch not in progress:
            progress[ch] = []

    total_migrated_all = 0
    total_skipped_dup_all = 0

    for source in SOURCE_CHANNELS:
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"⏳ Обрабатываю канал-источник: {source}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        try:
            source_entity = await client.get_entity(source)
            messages = await client.get_messages(source_entity, limit=None, reverse=True)

            count_found = 0
            count_sent = 0
            count_skipped_dup = 0
            count_skipped_done = 0

            for msg in messages:
                # Нас интересуют ТОЛЬКО видео/документы (аниме-серии)
                if not isinstance(getattr(msg, 'media', None), MessageMediaDocument):
                    continue

                count_found += 1

                # Уже переносили ранее в прошлых запусках
                if msg.id in progress[source]:
                    count_skipped_done += 1
                    continue

                caption = getattr(msg, 'message', '') or ''
                ep_data = parse_caption_to_episode(caption, msg.id, source_channel=source) if caption else None

                # Проверяем дубликат по единой базе ключей
                if ep_data and is_duplicate_episode(ep_data, existing_keys):
                    progress[source].append(msg.id)
                    count_skipped_dup += 1
                    continue

                # Если это не аниме-серия (нет номера серии в описании) — пропускаем
                if not ep_data and not caption:
                    progress[source].append(msg.id)
                    continue

                # Переносим!
                try:
                    title_info = f" ({ep_data['title']} | s{ep_data['season_id']}e{ep_data['episode_num']})" if ep_data else ""
                    print(f"  [{source}] 📤 Перенос msg_id #{msg.id}{title_info}...")
                    
                    await client.forward_messages(
                        TARGET_CHANNEL,
                        msg,
                        drop_author=True
                    )
                    count_sent += 1
                    total_migrated_all += 1

                    # Добавляем в список "уже есть", чтобы исключить дубли из последующих каналов
                    if ep_data:
                        add_episode_to_existing(ep_data, existing_keys)

                    progress[source].append(msg.id)
                    save_progress(progress)

                    await asyncio.sleep(2.0)

                except Exception as e:
                    err = str(e)
                    print(f"  ❌ Ошибка при переносе msg #{msg.id}: {err}")
                    if "FloodWait" in err or "flood" in err.lower():
                        wait_match = re.search(r'(\d+)', err)
                        wait_sec = int(wait_match.group(1)) if wait_match else 30
                        print(f"  ⚠️ FloodWait! Жду {wait_sec + 5} секунд...")
                        await asyncio.sleep(wait_sec + 5)
                    elif "Cannot send requests while disconnected" in err:
                        print("  🔌 Потеряно соединение! Прогресс сохранен. Перезапустите скрипт.")
                        await client.disconnect()
                        return
                    else:
                        await asyncio.sleep(4.0)

            total_skipped_dup_all += count_skipped_dup
            print(f"✅ {source} завершён! Всего медиа: {count_found} | Перенесено: {count_sent} | Дубликаты (пропущено): {count_skipped_dup} | Ранее перенесено: {count_skipped_done}\n")

        except Exception as e:
            print(f"❌ Ошибка доступа к каналу {source}: {e}\n")

    print("=======================================================")
    print(f"🎉 ВСЯ МИГРАЦИЯ ПОЛНОСТЬЮ ЗАВЕРШЕНА!")
    print(f"📦 Всего новых серий перенесено: {total_migrated_all}")
    print(f"🛡 Всего дубликатов предотвращено: {total_skipped_dup_all}")
    print("=======================================================")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate())
