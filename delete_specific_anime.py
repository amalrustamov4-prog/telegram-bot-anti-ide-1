import asyncio
import sqlite3
import logging
from telethon import TelegramClient

# Настройки
API_ID = 36342825  
API_HASH = "ca51cb7eccecc2b3707c9b0eeb41a5f4"  
TARGET_CHANNEL = -1002360405232  # @fullforeveranime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def get_messages_to_delete():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Ключи для "Магическая битва"
    jjk_keys = ['jjk', 'anime_magicheskaya', 'magicheskaya_bitva_3', 'magicheskaya_bitva_j', 'magicheskaya_bitva_2']
    
    msg_ids_to_delete = []
    
    # 1. Магическая битва - удаляем ИМЕННО AniLibria и Студийная-банда
    cursor.execute(f"SELECT message_id, title, dubbing FROM anime_catalog WHERE anime_key IN ({','.join(['?']*len(jjk_keys))})", jjk_keys)
    jjk_rows = cursor.fetchall()
    
    for row in jjk_rows:
        msg_id, title, dubbing = row
        # Удаляем только AniLibria и Студийная-банда (все сезоны этих озвучек)
        if dubbing in ['AniLibria', 'Студийная-банда']:
            msg_ids_to_delete.append((msg_id, title, dubbing))

    # 2. Адский рай (Hell's Paradise) - удаляем AnimeVost
    cursor.execute("SELECT message_id, title, dubbing FROM anime_catalog WHERE anime_key = 'hellas' AND dubbing = 'AnimeVost'")
    hellas_rows = cursor.fetchall()
    for row in hellas_rows:
        msg_ids_to_delete.append((row[0], row[1], row[2]))

    # 3. Наруто - удаляем полностью
    cursor.execute("SELECT message_id, title, dubbing FROM anime_catalog WHERE anime_key = 'naruto'")
    naruto_rows = cursor.fetchall()
    for row in naruto_rows:
        msg_ids_to_delete.append((row[0], row[1], row[2]))

    conn.close()
    return msg_ids_to_delete


async def main():
    msgs = get_messages_to_delete()
    
    if not msgs:
        logging.info("Не найдено сообщений для удаления!")
        return
        
    logging.info(f"Найдено {len(msgs)} серий для удаления.")
    
    client = TelegramClient('migration_session', API_ID, API_HASH)
    await client.start()
    
    msg_ids_list = [m[0] for m in msgs]
    
    chunk_size = 100
    for i in range(0, len(msg_ids_list), chunk_size):
        chunk = msg_ids_list[i:i+chunk_size]
        try:
            await client.delete_messages(TARGET_CHANNEL, chunk)
            logging.info(f"Удалено {len(chunk)} сообщений из канала...")
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка при удалении чанка: {e}")
            
    await client.disconnect()
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM anime_catalog WHERE message_id IN ({','.join(['?']*len(msg_ids_list))})", msg_ids_list)
    conn.commit()
    conn.close()
    
    logging.info(f"✅ База данных успешно очищена! Удалено {len(msg_ids_list)} записей.")

if __name__ == "__main__":
    asyncio.run(main())
