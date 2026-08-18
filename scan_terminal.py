import asyncio
import re
import sqlite3
import sys
import logging
import time
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

sys.stdout.reconfigure(encoding='utf-8')

# Импортируем настройки и парсер из проекта
import database as db
from script import (
    API_TOKEN,
    CHANNEL_ANIME,
    ANIME_SOURCE_CHANNELS,
    ADMIN_IDS,
    ONE_PIECE_ARCS,
    get_one_piece_arc,
    parse_caption_to_episode,
)

bot = Bot(token=API_TOKEN)
ADMIN_CHAT_ID = ADMIN_IDS[0]

async def get_channel_last_message_id(source_ch: str) -> int:
    """Быстро и надежно находит последний message_id канала"""
    # 1. Попытка отправить временное сообщение
    try:
        temp_msg = await bot.send_message(source_ch, "⌛ <i>Синхронизация базы...</i>", parse_mode="HTML")
        max_id = temp_msg.message_id
        try:
            await bot.delete_message(source_ch, max_id)
        except Exception:
            pass
        return max_id
    except Exception:
        pass

    # 2. Экспоненциальный поиск границы + бинарный поиск
    async def check_msg(mid: int) -> bool:
        for _ in range(3):
            try:
                fwd = await bot.forward_message(
                    chat_id=ADMIN_CHAT_ID,
                    from_chat_id=source_ch,
                    message_id=mid,
                    disable_notification=True
                )
                try:
                    await bot.delete_message(ADMIN_CHAT_ID, fwd.message_id)
                except Exception:
                    pass
                return True
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Exception:
                return False
        return False

    low = 1
    step = 500
    current = 500
    found_any = False

    while True:
        if await check_msg(current):
            found_any = True
            low = current
            current += step
            step = min(step * 2, 8000)
            if current > 300000:
                high = current
                break
        else:
            high = current
            break
        await asyncio.sleep(0.04)

    if not found_any:
        for test_id in [1, 5, 10, 50, 100, 200]:
            if await check_msg(test_id):
                found_any = True
                low = test_id
                break

    if not found_any:
        return 1

    # Бинарный поиск
    while low < high:
        mid = (low + high + 1) // 2
        if mid == low or mid == high:
            if await check_msg(high):
                low = high
            break
        if await check_msg(mid):
            low = mid
        else:
            high = mid - 1
        await asyncio.sleep(0.04)

    return max(1, low)

async def scan_single_channel(source_ch: str):
    print(f"\n=======================================================")
    print(f"🚀 НАЧИНАЮ СКАНИРОВАНИЕ КАНАЛА: {source_ch}")
    print(f"=======================================================")

    print("⏳ Определение последнего сообщения (max_id)...")
    max_id = await get_channel_last_message_id(source_ch)

    if max_id <= 1:
        print(f"❌ Не удалось получить доступ к сообщениям канала {source_ch}.")
        return 0

    print(f"✅ Найдено последнее сообщение: #{max_id}")

    total_added = 0
    empty_streak = 0
    MAX_EMPTY_STREAK = 5000  # Сканируем до самого конца (до сообщения #1)

    print(f"📥 Сканирование от #{max_id} до #1...")

    for mid in range(max_id, 0, -1):
        try:
            fwd = await bot.forward_message(
                chat_id=ADMIN_CHAT_ID,
                from_chat_id=source_ch,
                message_id=mid,
                disable_notification=True
            )
            empty_streak = 0

            caption = fwd.caption or fwd.text
            has_video = bool(fwd.video or fwd.document)

            try:
                await bot.delete_message(ADMIN_CHAT_ID, fwd.message_id)
            except Exception:
                pass

            if has_video and caption:
                ep_data = parse_caption_to_episode(caption, mid, source_channel=source_ch)
                if ep_data:
                    db.add_dynamic_episode(**ep_data)
                    total_added += 1

        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            continue
        except Exception:
            empty_streak += 1
            if empty_streak > MAX_EMPTY_STREAK:
                print(f"\n⚠️ Превышен лимит пустых сообщений подряд ({MAX_EMPTY_STREAK}). Завершаю скан.")
                break

        # Прогресс бар
        checked = max_id - mid + 1
        percent = int((checked / max_id) * 100) if max_id > 0 else 0
        sys.stdout.write(f"\r[{'=' * (percent // 5)}{' ' * (20 - (percent // 5))}] {percent}% | Проверено: {checked}/{max_id} | Добавлено серий: {total_added}")
        sys.stdout.flush()

        await asyncio.sleep(0.04)

    print(f"\n✅ Канал {source_ch} отсканирован! Добавлено новых/обновлено серий: {total_added}")
    return total_added

async def main():
    print("=======================================================")
    print("📺 ТЕРМИНАЛЬНЫЙ СКАНЕР КАНАЛОВ АНИМЕ")
    print("=======================================================")
    print("Выберите канал для сканирования «до конца»:")
    for i, ch in enumerate(ANIME_SOURCE_CHANNELS, start=1):
        print(f"  {i}. {ch}")
    print(f"  {len(ANIME_SOURCE_CHANNELS) + 1}. Сканировать ВСЕ каналы по очереди")
    print("  0. Выход")
    
    choice = input("\nВведите номер: ").strip()
    
    if choice == "0":
        print("Отмена.")
        return
        
    selected_channels = []
    if choice == str(len(ANIME_SOURCE_CHANNELS) + 1) or choice.lower() == "все" or choice.lower() == "all":
        selected_channels = ANIME_SOURCE_CHANNELS
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ANIME_SOURCE_CHANNELS):
                selected_channels = [ANIME_SOURCE_CHANNELS[idx]]
            else:
                print("❌ Неверный номер.")
                return
        except ValueError:
            print("❌ Неверный ввод.")
            return

    total = 0
    for ch in selected_channels:
        added = await scan_single_channel(ch)
        total += added

    # Финальная синхронизация БД
    print("\n🧹 Запуск финальной структуризации базы данных...")
    from fix_onepiece_catalog import fix_catalog
    fix_catalog()

    print(f"\n🎉 ВСЁ ГОТОВО! Всего обработано и добавлено серий: {total}")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
