import sqlite3
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

DB_PATH = "users.db"

def clean_arc_name(arc_name: str) -> str:
    """Убирает цифры в конце и подчёркивания из названий арок"""
    if not arc_name:
        return arc_name
    import re
    # Убираем подчёркивания -> пробелы
    arc_name = arc_name.replace("_", " ")
    # Убираем цифры в конце (например "Арлонг-Парк5" -> "Арлонг-Парк")
    arc_name = re.sub(r'\d+$', '', arc_name).strip()
    return arc_name

def group_consecutive_episodes(episodes):
    """Группирует числа в диапазоны, например [1, 2, 3, 5, 6] -> '1-3, 5-6'"""
    if not episodes:
        return "нет серий"
    
    episodes = sorted(set(episodes))
    ranges = []
    start = episodes[0]
    prev = episodes[0]
    
    for ep in episodes[1:]:
        if ep == prev + 1:
            prev = ep
        else:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            start = ep
            prev = ep
            
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{prev}")
        
    return ", ".join(ranges)

def build_anime_list_keyboard():
    """Строит клавиатуру со всеми аниме (статика + динамика)"""
    from script import ANIME_DB, clean_anime_title
    import database as db
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for anime_key, info in ANIME_DB.items():
        title = clean_anime_title(info['title'])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=title, callback_data=f"ainfo|{anime_key}")
        ])
    
    dynamic_anime = dict(db.get_all_dynamic_anime_keys())
    for anime_key, title in dynamic_anime.items():
        if anime_key not in ANIME_DB:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"🎬 {title}", callback_data=f"ainfo|{anime_key}")
            ])
    
    return keyboard

def register_audit_handlers(dp: Dispatcher, admin_ids: list):

    @dp.message(Command("info"))
    async def cmd_info_audit(message: Message):
        if message.from_user.id not in admin_ids:
            return
        
        keyboard = build_anime_list_keyboard()
        await message.answer("📊 <b>Аудит базы данных</b>\n\nВыберите аниме для проверки:", reply_markup=keyboard, parse_mode="HTML")

    # Callback: вернуться к списку аниме
    @dp.callback_query(F.data == "ainfo_back")
    async def process_ainfo_back(callback: CallbackQuery):
        if callback.from_user.id not in admin_ids:
            return
        keyboard = build_anime_list_keyboard()
        await callback.message.edit_text("📊 <b>Аудит базы данных</b>\n\nВыберите аниме для проверки:", reply_markup=keyboard, parse_mode="HTML")

    @dp.callback_query(F.data.startswith("ainfo|"))
    async def process_ainfo(callback: CallbackQuery):
        if callback.from_user.id not in admin_ids:
            return
            
        anime_key = callback.data.split("|")[1]
        from script import ANIME_DB, clean_anime_title
        import database as db
        
        anime_info = ANIME_DB.get(anime_key)
        if not anime_info:
            dynamic_anime = dict(db.get_all_dynamic_anime_keys())
            if anime_key in dynamic_anime:
                anime_info = {"title": f"🎬 {dynamic_anime[anime_key]}", "is_dynamic": True}
            else:
                await callback.answer("Аниме не найдено", show_alert=True)
                return
            
        dynamic_dubs = db.get_dynamic_dubs(anime_key)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for dub in dynamic_dubs:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"🎙 {dub}", callback_data=f"ainfodub|{anime_key}|{dub}")
            ])
        
        # Кнопка "Назад" к списку аниме
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔙 К списку аниме", callback_data="ainfo_back")
        ])
            
        if not dynamic_dubs:
            await callback.answer("Нет загруженных серий для этого аниме", show_alert=True)
            return
            
        title = clean_anime_title(anime_info['title'])
        await callback.message.edit_text(
            f"📊 <b>Аудит: {title}</b>\n\nВыберите озвучку:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    @dp.callback_query(F.data.startswith("ainfodub|"))
    async def process_ainfodub(callback: CallbackQuery):
        if callback.from_user.id not in admin_ids:
            return
            
        parts = callback.data.split("|")
        anime_key = parts[1]
        dub_name = parts[2]
        
        from script import ANIME_DB, clean_anime_title, extract_arc_name
        import database as db
        
        anime_info = ANIME_DB.get(anime_key)
        if not anime_info:
            dynamic_anime = dict(db.get_all_dynamic_anime_keys())
            if anime_key in dynamic_anime:
                anime_info = {"title": f"🎬 {dynamic_anime[anime_key]}", "is_dynamic": True}
            else:
                await callback.answer("Аниме не найдено", show_alert=True)
                return
            
        is_arc_only = anime_info.get("is_arc_only", False)
        dynamic_seasons = db.get_dynamic_seasons(anime_key, dub_name)
        
        lines = [f"📊 <b>Сводка по БД</b>\n🎬 {clean_anime_title(anime_info['title'])}\n🎙 Озвучка: <b>{dub_name}</b>\n"]
        
        for s_id in dynamic_seasons:
            if is_arc_only:
                arc_name = db.get_season_arc_name(anime_key, s_id, dub_name)
                if not arc_name:
                    db_title = db.get_season_title(anime_key, s_id, dub_name)
                    arc_name = extract_arc_name(db_title) or f"Сезон {s_id}"
                
                arc_display = clean_arc_name(arc_name)
                lines.append(f"\n🔹 <b>Арка: {arc_display}</b>")
                eps = db.get_dynamic_episodes(anime_key, s_id, dub_name)
                ep_nums = [ep[1] for ep in eps]
                lines.append(f"Серии: {group_consecutive_episodes(ep_nums)}")
            else:
                s_name = anime_info.get("season_names", {}).get(s_id, f"{s_id} сезон")
                lines.append(f"\n📌 <b>{s_name}:</b>")
                
                main_eps = db.get_dynamic_episodes(anime_key, s_id, dub_name, arc_name=None)
                if main_eps:
                    ep_nums = [ep[1] for ep in main_eps]
                    lines.append(f"Серии: {group_consecutive_episodes(ep_nums)}")
                
                arcs = db.get_dynamic_arcs(anime_key, s_id, dub_name)
                if arcs:
                    for arc in arcs:
                        arc_display = clean_arc_name(arc)
                        lines.append(f"  🔹 <i>Арка: {arc_display}</i>")
                        arc_eps = db.get_dynamic_episodes(anime_key, s_id, dub_name, arc_name=arc)
                        ep_nums = [ep[1] for ep in arc_eps]
                        lines.append(f"  Серии: {group_consecutive_episodes(ep_nums)}")
        
        report_text = "\n".join(lines)
        if len(report_text) > 4000:
            report_text = report_text[:4000] + "\n\n... (текст обрезан)"
            
        # Две кнопки: назад к озвучкам и назад к списку аниме
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К озвучкам", callback_data=f"ainfo|{anime_key}")],
            [InlineKeyboardButton(text="🏠 К списку аниме", callback_data="ainfo_back")]
        ])
        
        await callback.message.edit_text(report_text, reply_markup=keyboard, parse_mode="HTML")
