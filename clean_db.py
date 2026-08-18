import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def clean_database():
    print(f"Подключение к базе данных {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем количество записей до удаления
        cursor.execute("SELECT COUNT(*) FROM anime_catalog")
        count_before = cursor.fetchone()[0]
        print(f"Всего записей в каталоге до очистки: {count_before}")
        
        # Очищаем таблицу anime_catalog
        cursor.execute("DELETE FROM anime_catalog")
        
        conn.commit()
        print(f"✅ Таблица anime_catalog успешно очищена! Удалено {count_before} записей.")
        print("Теперь запустите бота и отправьте команду /scan в личные сообщения боту, чтобы он заново просканировал канал (уже без эдитов и мусора).")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    clean_database()
