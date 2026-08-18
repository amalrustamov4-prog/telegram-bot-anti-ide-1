import sqlite3
import asyncio
from aiogram import Bot
import os

# Токен вашего бота
API_TOKEN = "8444831803:AAFjuOVu7hgF-V46SSbIiE7dxNfn4ztgHTw"
TARGET_CHANNEL = "@fullforeveranime"
DB_PATH = "database.db"

# Список названий, которые нужно удалить (достаточно части названия)
BAD_TITLES = [
    "Пожалуйста, оденьтесь, Такаминэ",
    "Слегка настойчивая тёмная эльфийка",
    "Обычный роман в Коулуне",
    "Восход Луны",
    "Быть героем Икс",
    "Прячься, Макина!",
    "Перерождение мужчины средних лет в дочь дворянина"
]

async def main():
    print("=== Скрипт удаления запрещенных аниме ===")
    
    bot = Bot(token=API_TOKEN)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_deleted = 0
    
    for title in BAD_TITLES:
        print(f"\n🔍 Ищу: {title}...")
        
        # Находим все ключи и сообщения, где название похоже на искомое
        cursor.execute("SELECT message_id, anime_key, title FROM anime_catalog WHERE title LIKE ?", (f"%{title}%",))
        rows = cursor.fetchall()
        
        if not rows:
            print("  Не найдено в базе данных.")
            continue
            
        print(f"  Найдено серий: {len(rows)}")
        
        for msg_id, anime_key, full_title in rows:
            try:
                # 1. Удаляем из Telegram канала
                await bot.delete_message(chat_id=TARGET_CHANNEL, message_id=msg_id)
                print(f"  [Telegram] Удалено сообщение {msg_id} ({full_title})")
            except Exception as e:
                err = str(e).lower()
                if "message to delete not found" in err:
                    print(f"  [Telegram] Сообщение {msg_id} уже было удалено из канала.")
                else:
                    print(f"  [Telegram] Ошибка удаления {msg_id}: {e}")
            
            # 2. Удаляем из базы данных
            cursor.execute("DELETE FROM anime_catalog WHERE message_id = ?", (msg_id,))
            total_deleted += 1
            
            # Небольшая пауза, чтобы Telegram не ругался на спам запросами
            await asyncio.sleep(0.5)
            
        conn.commit()
    
    conn.close()
    await bot.session.close()
    
    print(f"\n✅ Готово! Всего удалено серий из канала и базы: {total_deleted}")

if __name__ == "__main__":
    asyncio.run(main())
