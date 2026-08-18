import asyncio
import re
import logging
from aiogram import Bot

API_TOKEN = "8444831803:AAFKqvjPUNSYYgLuCkeYGspZxSHHhs6WMew"
TARGET_CHANNEL = "@fullforeveranime"

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    bot = Bot(token=API_TOKEN)
    print("✅ Бот авторизован!\n")

    print(f"🔍 Бот не может искать сообщения в истории через aiogram так просто.")
    print("Но у нас есть база данных пользователей! Мы можем достать ID сообщений Ванпис из базы перед удалением (если мы их еще не удалили).")
    
    # К сожалению, мы уже удалили их из базы в delete_onepiece.py!
    # Значит, aiogram не поможет найти их в канале.
    # Нам нужен Telethon или Pyrogram.
    
    pass

if __name__ == "__main__":
    asyncio.run(main())
