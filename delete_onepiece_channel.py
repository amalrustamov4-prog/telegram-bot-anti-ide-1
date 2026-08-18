import asyncio
import re
import logging
from telethon import TelegramClient

API_ID = 36342825
API_HASH = "ca51cb7eccecc2b3707c9b0eeb41a5f4"
TARGET_CHANNEL = "@fullforeveranime"

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    print("=== Удаление Ванпис из канала ===")
    api_id = input("Введите ваш API ID (из my.telegram.org): ").strip()
    api_hash = input("Введите ваш API Hash: ").strip()
    
    if not api_id or not api_hash:
        print("Ошибка: API ID и API Hash обязательны!")
        return

    client = TelegramClient('migration_session', int(api_id), api_hash)
    await client.start()
    print("✅ Авторизован!\n")

    entity = await client.get_entity(TARGET_CHANNEL)
    
    # Собираем все сообщения Ванпис
    print("🔍 Сканирую канал, ищу все серии Ванпис...")
    vanpis_ids = []
    total = 0
    
    async for msg in client.iter_messages(entity, limit=None):
        total += 1
        caption = msg.message or ''
        
        # Проверяем на Ванпис / One Piece
        if re.search(r'ванпис|one\s*piece|ван\s*пис', caption, re.IGNORECASE):
            vanpis_ids.append(msg.id)
        
        if total % 500 == 0:
            print(f"  Проверено {total} сообщений, найдено Ванпис: {len(vanpis_ids)}")

    print(f"\n📊 Итого: проверено {total} сообщений")
    print(f"🎯 Найдено серий Ванпис: {len(vanpis_ids)}")
    
    if not vanpis_ids:
        print("Ванпис не найден в канале!")
        await client.disconnect()
        return

    # Удаляем чанками по 100
    print(f"\n🗑 Удаляю {len(vanpis_ids)} сообщений из канала...")
    chunk_size = 100
    deleted = 0
    for i in range(0, len(vanpis_ids), chunk_size):
        chunk = vanpis_ids[i:i+chunk_size]
        try:
            await client.delete_messages(entity, chunk)
            deleted += len(chunk)
            print(f"  Удалено {deleted}/{len(vanpis_ids)}...")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            await asyncio.sleep(3)
    
    print(f"\n✅ Готово! Удалено {deleted} серий Ванпис из канала @fullforeveranime!")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
