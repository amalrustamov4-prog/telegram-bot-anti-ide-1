import asyncio
import logging
import time


from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

import re
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import database as db

# =========================
# КОНФИГУРАЦИЯ
# =========================
API_TOKEN = os.getenv("BOT_TOKEN", "8444831803:AAFKqvjPUNSYYgLuCkeYGspZxSHHhs6WMew")
CHANNEL_ANIME = os.getenv("CHANNEL_ANIME", "@fullforeveranime") # Основной канал (для постинга через бота)
# Все каналы-источники аниме, которые бот сканирует и берёт видео
ANIME_SOURCE_CHANNELS = [
    "@fullforeveranime",
    "@TeliusOFF_Anime",
    "@AniVosto",
    "@shachiburi_one_piece",
    "@vseq_seriiw_animea",
    "@anime_sha",
    "@huntenters",
]
raw_channels_sub = os.getenv("CHANNELS_SUB", "@fullanimeorg")
CHANNELS_SUB = [c.strip() for c in raw_channels_sub.split(",") if c.strip()]
LOG_GROUP_ID = None  # СЮДА НУЖНО ВПИСАТЬ ID ВАШЕЙ ГРУППЫ БАЗЫ ДАННЫХ (например: -1001234567890)
SUGGESTIONS_GROUP = os.getenv("SUGGESTIONS_GROUP", "https://t.me/+inLuRtmQE1A3YWQy")
raw_admins = os.getenv("ADMIN_IDS", "6726066474")
ADMIN_IDS = [int(i.strip()) for i in raw_admins.split(",") if i.strip().isdigit()]
USER_REWARD_COOLDOWN = {} # id -> timestamp последнего получения награды

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_errors.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

@dp.error()
async def global_error_handler(event, exception=None):
    """Глобальный перехватчик ошибок: предотвращает падение бота при любых сбоях API или сети"""
    logging.exception(f"⚠️ Перехвачена ошибка: {exception or event}")
    return True

# =========================
# БАЗА КОНТЕНТА (Категории -> Элементы)
# =========================
ANIME_DB = {
    "jjk": {
        "title": "🎬 Магическая битва",
        "dubs": {
            "anilibria": {
                "name": "Anilibria",
                "quality": "1080p ✨",
                "seasons": {}
            },
            "animevost": {
                "name": "AnimeVost",
                "quality": "720p",
                "seasons": {}
            }
        },
        "short_tags": ["магическаябитва", "jjk", "jujutsukaisen", "магичка"]
    },
    "witch_hat": {
        "title": "🧙‍♀️ Ателье колдовских колпаков",
        "quality": "720p",
        "dubbing": "AnimeVost",
        "seasons": {},
        "short_tags": ["колдовскихколпаков", "ательеколдовскихколпаков", "witchhat"]
    },
    "op_elbaf": {
        "title": "🏴‍☠️ Ван-Пис",
        "dubs": {
            "Shachiburi": {
                "name": "Ван пис (shachiburi)",
                "quality": "1080p ✨",
                "seasons": {}
            },
            "Субтитры (Макс Летов)": {
                "name": "Ван пис (Субтитры от Макс Летова)",
                "quality": "1080p ✨",
                "seasons": {}
            },
            "Субтитры": {
                "name": "Ван пис (Субтитры)",
                "quality": "1080p ✨",
                "seasons": {}
            }
        },
        "short_tags": ["ванпис", "ванпис", "onepiece", "one_piece", "op", "эльбаф", "ванпіс"],
        "is_one_piece": True,
        "is_arc_only": True
    },
    "mushoku_tensei": {
        "title": "🪄 Реинкарнация безработного",
        "short_tags": [
            "реинкарнациябезработного", "mushokutensei", "mushoku", "реинкарнация",
            "безработный", "реинкарнациябезработного2", "mushoku_tensei", "реинкарнацыя",
            "реинкарнации", "реинкорнации", "реинкорнация", "реинкорнацыя",
            "безработного", "реинкарнациябезработногоисторияоприключенияхвдругоммире"
        ],
        "has_arcs": True
    },
    "hunter_x_hunter": {
        "title": "🎣 Хантер х Хантер",
        "short_tags": [
            "hunterxhunter", "hunter", "хантерххантер", "хантер", "хантерхантер",
            "hxh", "hunter_x_hunter", "охотникхохотник", "huntenters"
        ],
        "has_arcs": True
    },
    "hellas": {
        "title": "🔥 Адский рай",
        "quality": "720p",
        "dubbing": "AnimeVost",
        "seasons": {},
        "short_tags": ["адскийрай", "hellas", "jigokuraku"]
    },
    "slime": {
        "title": "💧 О моём перерождении в слизь",
        "quality": "720p",
        "dubbing": "AnimeVost",
        "seasons": {},
        "short_tags": ["слизь", "slime", "перерождениевслизь", "омоемперерождениивслизь", "tensei_shitara_slime_datta_ken", "перерождение", "перерождениивслизь"]
    },
    "angel_next_door": {
        "title": "👼 Ангел по соседству меня балует",
        "quality": "720p",
        "dubbing": "AnimeVost",
        "seasons": {},
        "short_tags": ["ангелпососедству", "ангелпососедствуменябалует", "angelnextdoor"]
    },
    "classroom_elite": {
        "title": "🏫 Добро пожаловать в класс превосходства",
        "quality": "720p",
        "dubbing": "AnimeVost",
        "seasons": {},
        "short_tags": ["класс", "превосходство", "дпвкп", "класспревосходства", "classroomoftheelite"]
    },
    "black_clover": {
        "title": "🍀 Чёрный клевер",
        "dubs": {
            "animevost": {
                "name": "AnimeVost",
                "quality": "720p",
                "seasons": {}
            },
            "odnogolosovoe": {
                "name": "Одноголосовое",
                "quality": "720p",
                "seasons": {}
            }
        },
        "short_tags": ["чёрныйклевер", "черныйклевер", "blackclover", "клевер", "чорныйклевер"],
        "has_arcs": True
    }
}

# =========================
# КАНОНИЧНЫЕ АРКИ ВАН-ПИС (One Piece)
# =========================
ONE_PIECE_ARCS = [
    {"name": "На заре приключений", "range": (1, 3), "is_filler": False},
    {"name": "Оранж-Таун", "range": (4, 8), "is_filler": False},
    {"name": "Деревня Сиропа", "range": (9, 18), "is_filler": False},
    {"name": "Ресторан Барати", "range": (19, 30), "is_filler": False},
    {"name": "Арлонг-Парк", "range": (31, 45), "is_filler": False},
    {"name": "История Багги", "range": (46, 47), "is_filler": False},
    {"name": "Логтаун", "range": (48, 53), "is_filler": False},
    {"name": "Апис", "range": (54, 61), "is_filler": True},
    {"name": "Реверс-Маунтин", "range": (62, 63), "is_filler": False},
    {"name": "Виски-Пик", "range": (64, 67), "is_filler": False},
    {"name": "История Коби и Хельмеппо", "range": (68, 69), "is_filler": False},
    {"name": "Литл-Гарден", "range": (70, 77), "is_filler": False},
    {"name": "Остров Драм", "range": (78, 91), "is_filler": False},
    {"name": "Алабаста", "range": (92, 130), "is_filler": False},
    {"name": "После Алабасты", "range": (131, 135), "is_filler": True},
    {"name": "Козий остров", "range": (136, 138), "is_filler": True},
    {"name": "Остров Рулука", "range": (139, 143), "is_filler": True},
    {"name": "Джая", "range": (144, 152), "is_filler": False},
    {"name": "Скайпия", "range": (153, 195), "is_filler": False},
    {"name": "G-8", "range": (196, 206), "is_filler": True},
    {"name": "Длинно-круглая земля", "range": (207, 219), "is_filler": False},
    {"name": "Океанский Сон", "range": (220, 224), "is_filler": True},
    {"name": "Возвращение Фокси", "range": (225, 228), "is_filler": False},
    {"name": "Water 7", "range": (229, 263), "is_filler": False},
    {"name": "Эниес-Лобби", "range": (264, 312), "is_filler": False},
    {"name": "После Эниес-Лобби", "range": (313, 325), "is_filler": False},
    {"name": "Ледяной Охотник", "range": (326, 336), "is_filler": True},
    {"name": "Триллер-Барк", "range": (337, 381), "is_filler": False},
    {"name": "Остров — спа", "range": (382, 384), "is_filler": True},
    {"name": "Архипелаг Сабаоди", "range": (385, 407), "is_filler": False},
    {"name": "Амазония Лили", "range": (408, 421), "is_filler": False},
    {"name": "Импел-Даун ч.1", "range": (422, 425), "is_filler": False},
    {"name": "Литл Ист Блю", "range": (426, 429), "is_filler": True},
    {"name": "Импел-Даун ч.2", "range": (430, 456), "is_filler": False},
    {"name": "Маринфорд", "range": (457, 489), "is_filler": False},
    {"name": "После Войны", "range": (490, 516), "is_filler": False},
    {"name": "Возвращение на Сабаоди", "range": (517, 526), "is_filler": False},
    {"name": "Остров Рыболюдей", "range": (527, 574), "is_filler": False},
    {"name": "Амбиции Z", "range": (575, 578), "is_filler": True},
    {"name": "Панк Хазард", "range": (579, 625), "is_filler": False},
    {"name": "Возвращение Цезаря", "range": (626, 628), "is_filler": True},
    {"name": "Дресс Роза", "range": (629, 746), "is_filler": False},
    {"name": "Серебряный рудник", "range": (747, 750), "is_filler": True},
    {"name": "Зоя", "range": (751, 779), "is_filler": False},
    {"name": "Дозорные-сверхновые", "range": (780, 782), "is_filler": True},
    {"name": "Пирожный Остров", "range": (783, 877), "is_filler": False},
    {"name": "Совет Королей", "range": (878, 889), "is_filler": False},
    {"name": "Страна Вано", "range": (890, 1085), "is_filler": False},
    {"name": "Яичная Голова", "range": (1086, 1155), "is_filler": False},
    {"name": "Эльбаф", "range": (1156, 999999), "is_filler": False},
]

def get_one_piece_arc(ep_num: int):
    """Возвращает (arc_id, arc_name, is_filler) по номеру серии"""
    for arc_idx, arc in enumerate(ONE_PIECE_ARCS, start=1):
        a_min, a_max = arc["range"]
        if a_min <= ep_num <= a_max:
            return arc_idx, arc["name"], arc["is_filler"]
            
    return len(ONE_PIECE_ARCS), ONE_PIECE_ARCS[-1]["name"], False

# =========================
# КАНОНИЧНЫЕ АРКИ ХАНТЕР Х ХАНТЕР (Hunter x Hunter 2011)
# =========================
HUNTER_X_HUNTER_ARCS = [
    {"name": "Экзамен на охотника", "range": (1, 21), "is_filler": False},
    {"name": "Семья Золдик", "range": (22, 26), "is_filler": False},
    {"name": "Небесная арена", "range": (27, 36), "is_filler": False},
    {"name": "Город Йоркнью", "range": (37, 58), "is_filler": False},
    {"name": "Остров жадности", "range": (59, 75), "is_filler": False},
    {"name": "Муравьи-химеры", "range": (76, 136), "is_filler": False},
    {"name": "Выборы 13-го председателя охотников", "range": (137, 148), "is_filler": False},
]

def get_hunter_x_hunter_arc(ep_num: int):
    """Возвращает (arc_id, arc_name, is_filler) по номеру серии для Хантер х Хантер"""
    for arc_idx, arc in enumerate(HUNTER_X_HUNTER_ARCS, start=1):
        a_min, a_max = arc["range"]
        if a_min <= ep_num <= a_max:
            return arc_idx, arc["name"], arc["is_filler"]
            
    return len(HUNTER_X_HUNTER_ARCS), HUNTER_X_HUNTER_ARCS[-1]["name"], False

# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================
def format_number(n):
    """Форматирует число с точками как разделителями (например, 10.000)"""
    return f"{n:,}".replace(",", ".")

def clean_anime_title(title: str) -> str:
    """Удаляет лишние дублирующиеся эмодзи и префиксы, оставляя ровно один эмодзи в начале"""
    if not title:
        return "🎬 Аниме"
    title = title.strip()
    # Удаляем служебные эмодзи-префиксы
    for p in ["🎬", "🎥"]:
        if title.startswith(p):
            title = title[len(p):].strip()
    # Если название уже начинается с буквы или цифры, добавляем стандартное 🎬
    if re.match(r'^[a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', title):
        return f"🎬 {title}"
    return title

def resolve_arc_slug(anime_key: str, season_id: int, dub_name: str, arc_slug: str) -> str | None:
    """Находит оригинальное название арки по её латинскому slug-варианту"""
    if not arc_slug:
        return None
    arcs = db.get_dynamic_arcs(anime_key, season_id, dub_name)
    for arc in arcs:
        if slugify(arc) == arc_slug:
            return arc
    return None
def transliterate(text: str) -> str:
    """Транслитерация кириллицы в латиницу для безопасных callback_data"""
    dic = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z',
        'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ъ': '', 'ь': ''
    }
    result = []
    for char in text.lower():
        result.append(dic.get(char, char))
    return "".join(result)

def slugify(text: str) -> str:
    """Создает короткий безопасный латинский ключ для dub_id"""
    return re.sub(r"[^a-z0-9]", "", transliterate(text)).lower()[:12]

def extract_arc_name(db_title: str) -> str | None:
    """Извлекает название арки из заголовка (старого или нового формата)"""
    if not db_title:
        return None
    arc_name = None
    # 1. Проверяем формат с новой строкой "арка: Название"
    arc_match = re.search(r"(?:арка|arc)\s*[:\-]?\s*([^\n]+)", db_title, re.I)
    if arc_match:
        arc_name = arc_match.group(1).strip()
    # 2. Проверяем формат "Название — Арка"
    elif " — " in db_title:
        arc_name = db_title.split(" — ", 1)[1].strip()
        
    return arc_name

def clean_arc_display_name(arc_name: str) -> str:
    """Убирает цифру-порядок из конца названия арки для красивого отображения.
    Пользователь пишет 'Оранж-Таун2' — показываем 'Оранж-Таун', сортируем по 2."""
    return re.sub(r'\d+$', '', arc_name).replace('_', ' ').strip()

def get_arc_order_num(arc_name: str) -> int | None:
    """Извлекает порядковый номер арки из конца названия (поставленный пользователем)."""
    m = re.search(r'(\d+)\s*$', arc_name)
    return int(m.group(1)) if m else None

def get_season_sort_key(s_id: int, s_name: str) -> tuple[int, int]:
    """Сортировочный ключ для сезонов. Сначала по числу в конце (порядок арки от пользователя), потом по s_id."""
    # 1. Ищем число в конце строки (например, "Арлонг-Парк5") — это номер арки от пользователя
    end_num_match = re.search(r'(\d+)\s*$', s_name)
    if end_num_match:
        return (int(end_num_match.group(1)), s_id)
    
    # 2. Ищем первое число в строке (например, "1 сезон")
    any_num_match = re.search(r'\d+', s_name)
    if any_num_match:
        return (int(any_num_match.group(0)), s_id)
        
    # Fallback на s_id
    return (999, s_id)

def resolve_dubbing_key(anime_id: str, dub_key: str) -> tuple[str | None, str | None]:
    """Возвращает оригинальный dub_id и отображаемое имя озвучки по короткому ключу."""
    if not dub_key:
        return None, None

    anime_info = ANIME_DB.get(anime_id, {})
    dub_slug = slugify(dub_key)
    dynamic_dubs = db.get_dynamic_dubs(anime_id)

    for sd in anime_info.get("dubs", {}).keys():
        if slugify(sd) == dub_slug or sd.lower() == dub_key.lower():
            return sd, anime_info["dubs"][sd].get("name", sd.capitalize())

    for dd in dynamic_dubs:
        if slugify(dd) == dub_slug or dd.lower() == dub_key.lower():
            return dd, dd

    return None, dub_key

async def check_sub(user_id: int):
    """Проверка подписки на каналы"""
    try:
        for channel in CHANNELS_SUB:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        logging.error(f"Ошибка проверки подписки {user_id}: {e}")
        return False

async def restrict_unsubscribed(callback: CallbackQuery) -> bool:
    """Ограничение доступа для неподписанных"""
    if not await check_sub(callback.from_user.id):
        try:
            await callback.answer(
                "❌ Доступ ограничен! Пожалуйста, подпишитесь на канал, чтобы пользоваться ботом.",
                show_alert=True
            )
        except Exception:
            pass
        return False
    return True

def home_button():
    """Кнопка возврата в главное меню"""
    return [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back")]

def anime_menu(anime_id: str, season_id: int, page: int, dub_id: str = None):
    """Генерация меню серий с пагинацией"""
    anime_info = ANIME_DB.get(anime_id)
    if not anime_info:
        return None

    # Берем эпизоды из озвучки или из основного словаря
    if dub_id and "dubs" in anime_info:
        episodes = anime_info["dubs"][dub_id]["seasons"].get(season_id, [])
    else:
        episodes = anime_info["seasons"].get(season_id, [])

    per_page = 12
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    items = episodes[start_idx:end_idx]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Кнопки серий по 3 в ряд
    for i in range(0, len(items), 3):
        row = []
        for j, ep in enumerate(items[i:i+3]):
            # Расчет номера серии
            full_idx = start_idx + i + j
            start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
            ep_num = full_idx + start_ep

            # В callback_data добавляем dub_id если он есть
            cb_data = f"ep_{anime_id}_{dub_id}_{season_id}_{ep}" if dub_id else f"ep_{anime_id}_{season_id}_{ep}"

            # Если есть кастомное название серии (например, "Фильм") — используем его
            ep_btn_text = anime_info.get("episode_names", {}).get(ep, f"{ep_num} серия")
            row.append(InlineKeyboardButton(text=ep_btn_text, callback_data=cb_data))
        keyboard.inline_keyboard.append(row)

    # Навигация
    nav_row = []
    if page > 1:
        nav_p_data = f"page_{anime_id}_{dub_id}_{season_id}_{page-1}" if dub_id else f"page_{anime_id}_{season_id}_{page-1}"
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=nav_p_data))
    if end_idx < len(episodes):
        nav_n_data = f"page_{anime_id}_{dub_id}_{season_id}_{page+1}" if dub_id else f"page_{anime_id}_{season_id}_{page+1}"
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=nav_n_data))

    if nav_row:
        keyboard.inline_keyboard.append(nav_row)

    back_cb = f"dub_{anime_id}_{dub_id}" if dub_id else f"anime_{anime_id}"
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    keyboard.inline_keyboard.append(home_button())

    # Добавляем серии из базы данных (если есть)
    dynamic_eps = db.get_dynamic_episodes(anime_id, season_id, dubbing=dub_id)
    if dynamic_eps:
        # Убираем дубликаты (если серия уже есть в ANIME_DB)
        existing_eps = set(episodes)
        for d_ep in dynamic_eps:
            if d_ep[0] not in existing_eps:
                # Вставляем в начало или конец? Лучше в конец
                pass

    return keyboard

def anime_menu_v2(anime_id: str, season_id: int, page: int, dub_id: str = None, arc_slug: str = None):
    """Генерация меню серий с учетом динамических данных из базы.
    Формат callback_data использует | как разделитель чтобы избежать конфликтов с _ в anime_id/dub_id.
    Форматы: ep|anime_id|dub_id|season_id|msg_id  или  ep|anime_id||season_id|msg_id
    """
    anime_info = ANIME_DB.get(anime_id) or {}

    # Находим оригинальное название озвучки по короткому Latin slug (dub_id)
    static_dub_id, display_name = resolve_dubbing_key(anime_id, dub_id)
    db_dub_name = static_dub_id or dub_id

    # Разрешаем arc_slug в оригинальное название арки
    arc_name = None
    if arc_slug:
        arc_name = resolve_arc_slug(anime_id, season_id, db_dub_name, arc_slug)

    # Статические серии из кода (показываем только если нет фильтра по арке)
    static_eps = []
    if not arc_slug:
        if static_dub_id and "dubs" in anime_info:
            raw = anime_info["dubs"].get(static_dub_id, {}).get("seasons", {}).get(season_id, [])
            start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
            static_eps = [(msg_id, i + start_ep) for i, msg_id in enumerate(raw)]
        elif not dub_id and "seasons" in anime_info:
            raw = anime_info["seasons"].get(season_id, [])
            start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
            static_eps = [(msg_id, i + start_ep) for i, msg_id in enumerate(raw)]

    # Динамические серии из базы с использованием ОРИГИНАЛЬНОГО названия озвучки и арки
    dynamic_eps = db.get_dynamic_episodes(anime_id, season_id, dubbing=db_dub_name, arc_name=arc_name)

    # Дедупликация по номеру серии (приоритет статике)
    final_dict = {}
    filler_set = set() # Хранит номера серий, которые являются филлерами
    for msg_id, ep_num in static_eps:
        final_dict[ep_num] = msg_id
    for msg_id, ep_num, is_filler in dynamic_eps:
        if ep_num not in final_dict:
            final_dict[ep_num] = msg_id
            if is_filler:
                filler_set.add(ep_num)

    all_eps = sorted([(msg_id, ep_num) for ep_num, msg_id in final_dict.items()], key=lambda x: x[1])

    per_page = 12
    total_eps = len(all_eps)
    total_pages = max(1, (total_eps + per_page - 1) // per_page)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    items = all_eps[start_idx:end_idx]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    d = dub_id or ""
    if items:
        for i in range(0, len(items), 3):
            row = []
            for ep_msg_id, ep_num in items[i:i+3]:
                is_filler = ep_num in filler_set
                ep_btn_text = anime_info.get("episode_names", {}).get(ep_msg_id)
                if not ep_btn_text:
                    suffix = " 💤" if is_filler else ""
                    ep_btn_text = f"{ep_num} серия{suffix}"
                cb_data = f"ep|{anime_id}|{d}|{season_id}|{ep_msg_id}"
                row.append(InlineKeyboardButton(text=ep_btn_text, callback_data=cb_data))
            keyboard.inline_keyboard.append(row)
    else:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="⚠️ Серии не найдены для этого сезона.", callback_data=f"anime_{anime_id}")
        ])

    # Навигация
    nav_row = []
    a_slug = f"|{arc_slug}" if arc_slug else ""
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page|{anime_id}|{d}|{season_id}|{page-1}{a_slug}"))
    if end_idx < len(all_eps):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"page|{anime_id}|{d}|{season_id}|{page+1}{a_slug}"))
    if nav_row:
        keyboard.inline_keyboard.append(nav_row)

    # Кнопка назад возвращает к аркам, если они выбраны, иначе к сезонам/озвучкам
    if arc_slug:
        back_cb = f"season|{anime_id}|{d}|{season_id}"
    else:
        back_cb = f"dub|{anime_id}|{d}" if dub_id else f"anime_{anime_id}"
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    keyboard.inline_keyboard.append(home_button())
    return keyboard

async def db_update_tasks(user, anime_id, ep):
    """Фоновые задачи для обновления БД и наград"""
    try:
        user_id = user.id
        db.add_user(user_id=user_id, username=user.username, full_name=user.full_name)

        if user_id in ADMIN_IDS:
            return

        current_time = time.time()
        if current_time - USER_REWARD_COOLDOWN.get(user_id, 0) < 60:
            return

        USER_REWARD_COOLDOWN[user_id] = current_time
        db.increment_request(user_id)
        db.update_balance(user_id, 10)
        level_up = db.add_xp(user_id, 100)

        # Инфо о юзере для проверок достижений
        u_info = db.get_user_info(user_id)
        if not u_info: return

        # 1. Level up!
        if level_up:
            db.update_balance(user_id, 200)
            await bot.send_message(user_id, "🥳 <b>LEVEL UP!</b>\nТы достиг нового уровня! Твой бонус: +200 баллов.", parse_mode="HTML")

        # 2. Юбилей 100 серий
        if u_info['requests_count'] == 100:
            db.update_balance(user_id, 1000)
            db.add_xp(user_id, 500)
            await bot.send_animation(
                chat_id=user_id,
                animation="https://media.tenor.com/KXBZpf5EfQMAAAAC/congratulations.gif",
                caption="🏆 <b>НЕВЕРОЯТНО! НАСТОЯЩИЙ ОТАКУ!</b> 🏆\n\nВы посмотрели уже 100 серий! Бонус: <b>+1000 баллов</b> и <b>+500 XP</b>!",
                parse_mode="HTML"
            )

        # 3. Первый просмотр
        if u_info['requests_count'] == 1:
            rating_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{i}") for i in range(1, 6)
            ]])
            await bot.send_animation(
                chat_id=user_id,
                animation="https://media.tenor.com/vYQaxVAZVaIAAAAC/bon-fire-night-fireworks.gif",
                caption="🎇 <b>С ПЕРВЫМ ПРОСМОТРОМ!</b> 🎇\n\nПожалуйста, оцените наш бот:",
                reply_markup=rating_kb,
                parse_mode="HTML"
            )

        # 4. Конец сезона
        anime_info = ANIME_DB.get(anime_id)
        if anime_info and "seasons" in anime_info:
            for s_id, episodes in anime_info["seasons"].items():
                if ep == episodes[-1]:
                    db.update_balance(user_id, 15)
                    await bot.send_message(user_id, "🏆 <b>Сезон завершен!</b>\nБонус: <b>+15 баллов</b>.", parse_mode="HTML")
                    break

    except Exception as e:
        logging.error(f"Ошибка в фоновых задачах: {e}")

# =========================
# ОБРАБОТЧИКИ КОМАНД
# =========================
@dp.message(Command("start"))
async def start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    if message.chat.type != "private":
        return

    # Проверка реферала
    referred_by = None
    if command.args:
        try:
            referred_by = int(command.args)
            if referred_by == message.from_user.id:
                referred_by = None # Нельзя пригласить самого себя
        except ValueError:
            pass

    # Создаем/обновляем пользователя
    is_new = db.get_user_info(message.from_user.id) is None
    db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    # Награда за реферала (только если юзер новый)
    if is_new and referred_by:
        db.update_balance(referred_by, 500)
        db.add_xp(referred_by, 200)
        try:
            await bot.send_message(
                chat_id=referred_by,
                text=f"🤝 <b>Новый реферал!</b>\n\nПо вашей ссылке зашел {message.from_user.full_name}.\n💰 Вам начислено 500 баллов и 200 XP!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    if not CHANNELS_SUB or await check_sub(message.from_user.id):
        await main_menu(message)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNELS_SUB[0].replace('@', '')}")],
        [InlineKeyboardButton(text="✅ Я подписался (Начать)", callback_data="check")]
    ])

    user_name = message.from_user.first_name
    text = (
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "✨ <b>Добро пожаловать в Full Forever Anime!</b> ✨\n\n"
        "🎬 <i>Смотрите любимые аниме прямо в Telegram!</i>\n"
        "🚀 Быстро, удобно и без рекламы.\n\n"
        "🔔 <b>Важное условие:</b>\n"
        "Для работы бота нужно подписаться на наш канал. Там мы публикуем новости и обновления!\n\n"
        "👇 <b>Подпишитесь и нажмите кнопку ниже:</b>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Справка по командам:</b>\n\n"
        "🏠 /start — Главное меню\n"
        "👤 /profile — Твой прогресс и баланс\n"
        "🆔 /id — Информация об ID\n"
        "🕹 /games — Мини-игры для заработка XP\n"
        "🎁 /daily — Забрать ежедневный бонус\n"
        "❓ /help — Показать это сообщение"
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Быстрый переход в главное меню"""
    await main_menu(message)

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Быстрый переход в поддержку/администрацию или панель админа"""
    if message.from_user.id in ADMIN_IDS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Сканировать канал", callback_data="admin_scan")],
            [InlineKeyboardButton(text="🧹 Очистить базу (удалённые серии)", callback_data="admin_cleanup")],
            [InlineKeyboardButton(text="🔄 Перезапустить бота", callback_data="admin_restart")],
            [InlineKeyboardButton(text="🛑 Выключить бота", callback_data="admin_stop")],
            [InlineKeyboardButton(text="💬 Меню поддержки", callback_data="support")]
        ])
        await message.answer("👑 <b>Панель администратора:</b>\nВыберите действие:", reply_markup=keyboard, parse_mode="HTML")
    else:
        await support(message)


async def send_profile(user_id: int, send_method):
    user_info = db.get_user_info(user_id)
    if not user_info:
        await send_method("❌ Информация не найдена. Попробуй /start", parse_mode="HTML")
        return

    # Расчет прогресса до след. уровня
    next_level_xp = user_info['level'] * 500
    progress_bar = "🟢" * int((user_info['xp'] / next_level_xp) * 10) + "⚪" * (10 - int((user_info['xp'] / next_level_xp) * 10))

    username_text = f"@{user_info['username']}" if user_info['username'] else "нет"
    game_pts = user_info.get('game_balance', 0)
    game_sign = f"+{game_pts}" if game_pts > 0 else f"{game_pts}"

    profile_text = (
        f"<b>👤 ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:</b> {username_text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{user_info['user_id']}</code>\n"
        f"📝 <b>Имя:</b> {user_info['full_name']}\n"
        f"🔗 <b>Никнейм:</b> {username_text}\n"
        f"📅 <b>Зашёл в бота:</b> {user_info['join_date'].split(' ')[0]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 <b>Статистика {username_text}</b>\n"
        f"🍿 <b>Просмотрено аниме:</b> <code>{user_info['requests_count']}</code>\n"
        f"🎮 <b>Очки в мини-игре:</b> <code>{game_sign}</code>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌟 <b>Уровень:</b> <code>{user_info['level']}</code>\n"
        f"📈 <b>Опыт:</b> {user_info['xp']} / {next_level_xp} XP\n"
        f"{progress_bar}\n"
        f"💰 <b>Общий баланс:</b> <code>{user_info['balance']}</code> баллов\n"
        f"━━━━━━━━━━━━━━\n"
        f"🤝 <b>Реферальная ссылка:</b>\n"
        f"<code>https://t.me/{(await bot.get_me()).username}?start={user_info['user_id']}</code>\n"
        f"━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

    await send_method(profile_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    await send_profile(message.from_user.id, message.answer)


@dp.message(Command("id"))
async def cmd_id(message: Message):
    # Если переслано сообщение — показываем ID оригинала (полезно для админа)
    if message.forward_from_chat:
        resp = (
            f"📢 <b>Канал:</b> {message.forward_from_chat.title}\n"
            f"🆔 <b>Message ID:</b> <code>{message.forward_from_message_id}</code>\n\n"
            f"<i>Используй этот ID в ANIME_DB для добавления серий!</i>"
        )
    elif message.reply_to_message and message.reply_to_message.forward_from_chat:
         resp = (
            f"📢 <b>Канал:</b> {message.reply_to_message.forward_from_chat.title}\n"
            f"🆔 <b>Message ID:</b> <code>{message.reply_to_message.forward_from_message_id}</code>"
        )
    else:
        resp = f"🆔 <b>Твой ID:</b> <code>{message.from_user.id}</code>"

    await message.answer(resp, parse_mode="HTML")


# =========================
# ОБРАБОТЧИКИ CALLBACK
# =========================
@dp.callback_query(F.data == "check")
async def check(callback: CallbackQuery):
    if await check_sub(callback.from_user.id):
        await callback.answer("✅ Подписка подтверждена!")
        await callback.message.delete()
        await main_menu(callback.message)
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

async def main_menu(message: Message, edit: bool = False):
    user_id = message.chat.id
    last_watched = db.get_last_watched(user_id)
    
    keyboard_rows = []
    
    # Если есть история просмотров, добавляем кнопку продолжения
    if last_watched:
        anime_info = ANIME_DB.get(last_watched['anime_key'])
        # Очищаем заголовок от эмодзи для кнопки продолжения
        raw_title = anime_info.get('title', last_watched['anime_key']) if anime_info else last_watched['anime_key']
        anime_title = raw_title.lstrip("🎥 ").strip() if raw_title.startswith("🎥") else raw_title
        if len(anime_title) > 15:
            anime_title = anime_title[:12] + "..."
            
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"🕒 Продолжить: {anime_title} ({last_watched['episode_num']} сер.)",
                callback_data="resume_watch"
            )
        ])
        
    keyboard_rows.extend([
        [
            InlineKeyboardButton(text="🎬 Каталог", callback_data="anime_list"),
            InlineKeyboardButton(text="⭐️ Избранное", callback_data="my_favorites"),
        ],
        [
            InlineKeyboardButton(text="🏆 Топ", callback_data="top_list"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile_cb"),
        ],
        [InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{CHANNEL_ANIME.replace('@', '')}")],
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    stats = db.get_global_stats()
    formatted_users = format_number(stats['total_users'])

    welcome_text = (
        f"🔥 <b>PREMIUM ANIME PLATFORM</b>\n"
        f"👥 <b>{formatted_users} пользователей</b>\n"
        f"━━━━━━━━━━━━━━\n"
        "Добро пожаловать в обновленное меню! Выбирай категорию ниже и наслаждайся контентом:\n\n"
        "🍿 <b>Смотри</b> новинки аниме и кино\n"
        "🌟 <b>Прокачивай</b> свой уровень\n"
        "━━━━━━━━━━━━━━"
    )

    if edit:
        try:
            await message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "support")
async def support(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Группа для жалоб и предложений", url=SUGGESTIONS_GROUP)],
        [InlineKeyboardButton(text="👑 Владелец бота", url="https://t.me/fullforev")],
        [InlineKeyboardButton(text="🛠 Админ", url="https://t.me/not_goku_0919")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

    text = "<b>💬 Поддержка и Администрация:</b>\n\nЕсли у вас есть вопросы или предложения, обращайтесь к нам!"

    if isinstance(event, CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

PAGE_SIZE = 15  # Аниме на одной странице каталога

def build_anime_list_keyboard(available_anime, page: int) -> tuple[InlineKeyboardMarkup, int]:
    """Строит клавиатуру каталога — одна кнопка на аниме. Поток: Аниме → Озвучка → Сезон → Серии."""
    static_keys = list(ANIME_DB.keys())

    def sort_key(item):
        k, t = item
        if k in static_keys:
            return (0, static_keys.index(k))
        return (1, t)

    available_anime = sorted(available_anime, key=sort_key)
    total_pages = max(1, (len(available_anime) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = available_anime[start:end]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Показываем по 2 аниме в ряд для компактности
    row = []
    for anime_key, title in page_items:
        if anime_key in ANIME_DB:
            display_title = clean_anime_title(ANIME_DB[anime_key]['title'])
        else:
            display_title = clean_anime_title(title)

        btn = InlineKeyboardButton(
            text=f"🎬 {display_title}",
            callback_data=f"anime_{anime_key}"
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    # Навигационные кнопки
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"anime_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"anime_page_{page + 1}"))
    keyboard.inline_keyboard.append(nav_row)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back")])

    return keyboard, total_pages



@dp.callback_query(F.data == "anime_list")
async def anime_list(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        if not await restrict_unsubscribed(event):
            return
        await event.answer()
        message = event.message
    else:
        if not await check_sub(event.from_user.id):
            await event.answer("❌ Доступ ограничен! Пожалуйста, подпишитесь на канал.")
            return
        message = event

    available_anime = db.get_all_dynamic_anime_keys()
    keyboard, total_pages = build_anime_list_keyboard(available_anime, page=0)
    text = "🎬 <b>Выберите аниме для просмотра:</b>"

    if isinstance(event, CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data.startswith("anime_page_"))
async def anime_list_page(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    await callback.answer()
    page = int(callback.data.split("_")[-1])
    available_anime = db.get_all_dynamic_anime_keys()
    keyboard, _ = build_anime_list_keyboard(available_anime, page=page)
    text = "🎬 <b>Выберите аниме для просмотра:</b>"
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.answer()
    except Exception:
        pass
    await main_menu(callback.message, edit=True)


@dp.callback_query(F.data == "profile_cb")
async def profile_callback(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    await callback.message.delete()
    await send_profile(callback.from_user.id, callback.message.answer)


@dp.callback_query(F.data == "daily")
async def daily_callback(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass # Answer early to avoid timeout
    if db.check_daily(callback.from_user.id):
        reward = 100
        db.update_balance(callback.from_user.id, reward)
        db.add_xp(callback.from_user.id, 50)
        await callback.answer(f"🎁 Ты получил {reward} баллов и 50 XP!", show_alert=True)
        await profile_callback(callback)
    else:
        await callback.answer("⏳ Бонус еще не готов! Заходи через 24 часа.", show_alert=True)



@dp.callback_query(F.data.startswith("anime_"))
async def anime_selector(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
    anime_id = callback.data[len("anime_"):]
    anime_info = ANIME_DB.get(anime_id)
    if not anime_info:
        dynamic_keys = dict(db.get_all_dynamic_anime_keys())
        if anime_id in dynamic_keys:
            anime_info = {"title": f"🎬 {dynamic_keys[anime_id]}"}
        else:
            return

    # Объединяем статические и динамические озвучки с безопасными латинскими ключами
    # Показываем только те, у которых есть реальные серии в БД
    dubs_map = {}  # slug -> original_name
    real_dubs_in_db = db.get_dynamic_dubs(anime_id)  # дубляжи у которых есть серии
    real_dubs_lower = {d.lower() for d in real_dubs_in_db}

    for sd in anime_info.get("dubs", {}).keys():
        dub_display_name = anime_info["dubs"][sd].get("name", sd.capitalize())
        # Показываем статичную озвучку только если есть серии в БД или есть статичные сезоны
        has_static_seasons = bool(anime_info["dubs"][sd].get("seasons", {}))
        has_db_episodes = dub_display_name.lower() in real_dubs_lower
        if has_static_seasons or has_db_episodes:
            sd_slug = re.sub(r'[^a-z0-9]', '', transliterate(sd))[:12]
            dubs_map[sd_slug] = dub_display_name

    dynamic_dubs = real_dubs_in_db
    for dd in dynamic_dubs:
        dd_slug = re.sub(r'[^a-z0-9]', '', transliterate(dd))[:12]
        if dd_slug not in dubs_map:
            dubs_map[dd_slug] = dd

    user_id = callback.from_user.id
    is_fav = db.is_favorite(user_id, anime_id)
    fav_text = "❌ Убрать из избранного" if is_fav else "⭐️ Добавить в избранное"
    fav_cb = f"fav_toggle|{anime_id}"

    # Достаём чистый заголовок без лишнего эмодзи
    display_title = clean_anime_title(anime_info['title'])

    # Всегда показываем экран выбора озвучки (даже если одна) — чистый поток Аниме → Озвучка → Сезон → Серии
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text=fav_text, callback_data=fav_cb)])

    if dubs_map:
        for dub_key, dub_name_val in sorted(dubs_map.items(), key=lambda x: x[1]):
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"🎙 {dub_name_val}", callback_data=f"dub|{anime_id}|{dub_key}")])
    else:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="📭 Озвучек пока нет", callback_data="noop")])

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="anime_list")])
    keyboard.inline_keyboard.append(home_button())
    try:
        await callback.message.edit_text(
            f"<b>🎬 {display_title}</b>\n\n🎙 Выбери озвучку:",
            reply_markup=keyboard, parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"<b>🎬 {display_title}</b>\n\n🎙 Выбери озвучку:",
            reply_markup=keyboard, parse_mode="HTML"
        )
    return

# Новый формат: dub|anime_id|dub_key
@dp.callback_query(F.data.startswith("dub|"))
async def dub_selector(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass

    # format: dub|anime_id|dub_key
    _, anime_id, dub_key = callback.data.split("|", 2)

    anime_info = ANIME_DB.get(anime_id) or {"title": "Аниме", "dubs": {}}
    if not ANIME_DB.get(anime_id):
        dynamic_keys = dict(db.get_all_dynamic_anime_keys())
        if anime_id in dynamic_keys:
            anime_info = {"title": f"🎬 {dynamic_keys[anime_id]}", "dubs": {}}

    static_dub_id, display_name = resolve_dubbing_key(anime_id, dub_key)
    db_dub_name = static_dub_id or dub_key
    display_dub_name = display_name or dub_key.capitalize()

    if anime_id == "op_elbaf":
        available_seasons = set(db.get_dynamic_seasons(anime_id, db_dub_name))
        seasons_with_names = []
        for s_id, arc in enumerate(ONE_PIECE_ARCS, start=1):
            if s_id in available_seasons or not available_seasons:
                seasons_with_names.append((s_id, arc["name"]))
    elif anime_id == "hunter_x_hunter":
        available_seasons = set(db.get_dynamic_seasons(anime_id, db_dub_name))
        seasons_with_names = []
        for s_id, arc in enumerate(HUNTER_X_HUNTER_ARCS, start=1):
            if s_id in available_seasons or not available_seasons:
                seasons_with_names.append((s_id, arc["name"]))
    else:
        # Сезоны: статика + динамика
        static_seasons = []
        if static_dub_id and "dubs" in anime_info:
            static_seasons = list(anime_info.get("dubs", {}).get(static_dub_id, {}).get("seasons", {}).keys())

        dynamic_seasons = db.get_dynamic_seasons(anime_id, db_dub_name)
        all_seasons_raw = list(set(static_seasons + dynamic_seasons))

        seasons_with_names = []
        for s_id in all_seasons_raw:
            s_name = None
            if s_id in dynamic_seasons and anime_info.get("is_arc_only"):
                s_name = db.get_season_arc_name(anime_id, s_id, db_dub_name)
                if not s_name:
                    db_title = db.get_season_title(anime_id, s_id, db_dub_name)
                    s_name = extract_arc_name(db_title)
            if not s_name:
                s_name = anime_info.get("season_names", {}).get(s_id, f"{s_id} сезон")
            seasons_with_names.append((s_id, s_name))

    def sort_key(item):
        s_id, s_name = item
        if anime_id in ["op_elbaf", "hunter_x_hunter"]:
            return (0, s_id)
        arc_order = get_arc_order_num(s_name)
        if arc_order is not None:
            return (0, arc_order)
        season_min_eps = db.get_season_min_episodes(anime_id)
        if s_id in season_min_eps:
            return (1, season_min_eps[s_id])
        return (2, s_id)

    seasons_with_names.sort(key=sort_key)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if not seasons_with_names:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="⚠️ Нет доступных арок для этой озвучки", callback_data=f"anime_{anime_id}")
        ])
    else:
        for s_id, s_name in seasons_with_names:
            if anime_id == "op_elbaf":
                btn_text = f"🏴‍☠️ {s_id}. {s_name}"
            elif anime_id == "hunter_x_hunter":
                btn_text = f"🎣 {s_id}. {s_name}"
            else:
                display_name_btn = clean_arc_display_name(s_name) if anime_info.get("is_arc_only") else s_name
                prefix = "🎬 " if not display_name_btn.startswith("🎬") else ""
                btn_text = f"{prefix}{display_name_btn}"
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"season|{anime_id}|{dub_key}|{s_id}")])

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 К озвучкам", callback_data=f"anime_{anime_id}")])
    keyboard.inline_keyboard.append(home_button())

    msg_text_prefix = "Выбери арку:" if (anime_id in ["op_elbaf", "hunter_x_hunter"] or anime_info.get("is_arc_only") or anime_info.get("has_arcs")) else "Выбери сезон:"

    try:
        await callback.message.edit_text(f"{clean_anime_title(anime_info['title'])}\n{msg_text_prefix}\n🎙 Озвучка: {display_dub_name}", reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        try: await callback.message.delete()
        except Exception: pass
        await callback.message.answer(f"{clean_anime_title(anime_info['title'])}\n{msg_text_prefix}\n🎙 Озвучка: {display_dub_name}", reply_markup=keyboard, parse_mode="HTML")

# Новый формат: season|anime_id|dub_key|season_id  (dub_key может быть пустым)
@dp.callback_query(F.data.startswith("season|"))
async def season_selector(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass

    # format: season|anime_id|dub_key|season_id
    _, anime_id, dub_key, season_str = callback.data.split("|")
    season_id = int(season_str)
    dub_id = dub_key if dub_key else None

    anime_info = ANIME_DB.get(anime_id) or {"title": "Аниме"}
    if not ANIME_DB.get(anime_id):
        dynamic_keys = dict(db.get_all_dynamic_anime_keys())
        if anime_id in dynamic_keys:
            anime_info = {"title": f"🎬 {dynamic_keys[anime_id]}"}

    # Находим оригинальное название озвучки по короткому Latin slug (dub_key)
    static_dub_id, display_name = resolve_dubbing_key(anime_id, dub_id)
    db_dub_name = static_dub_id or dub_id
    display_dub_name = display_name or (dub_id.capitalize() if dub_id else "")

    # Проверяем, есть ли зарегистрированные под-арки в этом сезоне
    arcs = db.get_dynamic_arcs(anime_id, season_id, db_dub_name)
    has_main = db.has_episodes_without_arc(anime_id, season_id, db_dub_name)
    
    # Показываем под-арки только если это не One Piece (где season_id = арка) и есть под-арки
    if arcs and anime_id != "op_elbaf" and not anime_info.get("is_arc_only"):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        if has_main:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="🎬 Основные серии", callback_data=f"arc|{anime_id}|{dub_key}|{season_id}|main")
            ])
        for arc in arcs:
            arc_slug = slugify(arc)
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"🎬 {arc}", callback_data=f"arc|{anime_id}|{dub_key}|{season_id}|{arc_slug}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"dub|{anime_id}|{dub_key}")])
        keyboard.inline_keyboard.append(home_button())
        
        display_title = clean_anime_title(anime_info['title'])
        try:
            await callback.message.edit_text(
                f"<b>{display_title}</b>\n📌 {season_id} сезон\n\nВыбери арку:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            try: await callback.message.delete()
            except Exception: pass
            await callback.message.answer(
                f"<b>{display_title}</b>\n📌 {season_id} сезон\n\nВыбери арку:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return

    if anime_id == "op_elbaf":
        if 1 <= season_id <= len(ONE_PIECE_ARCS):
            arc_label = f"{season_id}. {ONE_PIECE_ARCS[season_id - 1]['name']}"
        else:
            arc_label = f"Арка {season_id}"
    else:
        s_name = anime_info.get("season_names", {}).get(season_id)
        if not s_name:
            s_name = db.get_season_arc_name(anime_id, season_id, db_dub_name)
            if not s_name:
                db_title = db.get_season_title(anime_id, season_id, db_dub_name)
                s_name = extract_arc_name(db_title)
            if not s_name:
                s_name = f"{season_id} сезон"
        arc_label = f"Арка {s_name}" if (anime_info.get("is_arc_only")) and not s_name.lower().startswith("арка") else s_name

    try:
        await callback.message.edit_text(
            f"<b>{clean_anime_title(anime_info['title'])}</b>\n📌 {arc_label}\n\nВыбери серию:",
            reply_markup=anime_menu_v2(anime_id, season_id, 1, dub_id),
            parse_mode="HTML"
        )
    except Exception:
        try: await callback.message.delete()
        except Exception: pass
        await callback.message.answer(
            f"<b>{clean_anime_title(anime_info['title'])}</b>\n📌 {arc_label}\n\nВыбери серию:",
            reply_markup=anime_menu_v2(anime_id, season_id, 1, dub_id),
            parse_mode="HTML"
        )

# Новый обработчик для выбора арки: arc|anime_id|dub_key|season_id|arc_slug
@dp.callback_query(F.data.startswith("arc|"))
async def arc_selector(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass

    _, anime_id, dub_key, season_str, arc_slug = callback.data.split("|")
    season_id = int(season_str)
    dub_id = dub_key if dub_key else None

    anime_info = ANIME_DB.get(anime_id) or {"title": "Аниме"}
    if not ANIME_DB.get(anime_id):
        dynamic_keys = dict(db.get_all_dynamic_anime_keys())
        if anime_id in dynamic_keys:
            anime_info = {"title": f"🎬 {dynamic_keys[anime_id]}"}

    # Находим оригинальное название озвучки по короткому Latin slug (dub_key)
    dub_name = None
    if dub_id:
        static_dub_id, dub_name = resolve_dubbing_key(anime_id, dub_id)
        if not dub_name:
            dynamic_dubs = db.get_dynamic_dubs(anime_id)
            for d in dynamic_dubs:
                d_slug = re.sub(r'[^a-z0-9]', '', transliterate(d))[:12]
                if d_slug == dub_id:
                    dub_name = d
                    break
        if not dub_name:
            dub_name = dub_id.capitalize()

    # Разрешаем название арки по её латинскому слагаемому
    resolved_arc = resolve_arc_slug(anime_id, season_id, dub_name, arc_slug)
    s_name = resolved_arc if resolved_arc else f"{season_id} сезон"

    try:
        await callback.message.edit_text(
            f"<b>{clean_anime_title(anime_info['title'])}</b>\n📌 {s_name}\n\nВыбери серию:",
            reply_markup=anime_menu_v2(anime_id, season_id, 1, dub_id, arc_slug),
            parse_mode="HTML"
        )
    except Exception:
        try: await callback.message.delete()
        except Exception: pass
        await callback.message.answer(
            f"<b>{clean_anime_title(anime_info['title'])}</b>\n📌 {s_name}\n\nВыбери серию:",
            reply_markup=anime_menu_v2(anime_id, season_id, 1, dub_id, arc_slug),
            parse_mode="HTML"
        )

# Новый формат: page|anime_id|dub_key|season_id|page
@dp.callback_query(F.data.startswith("page|"))
async def page_selector(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    # format: page|anime_id|dub_key|season_id|page|[arc_slug]
    parts = callback.data.split("|")
    anime_id = parts[1]
    dub_key = parts[2]
    season_id = int(parts[3])
    page = int(parts[4])
    arc_slug = parts[5] if len(parts) > 5 else None
    dub_id = dub_key if dub_key else None

    anime_info = ANIME_DB.get(anime_id) or {"title": "Аниме"}
    if not ANIME_DB.get(anime_id):
        dynamic_keys = dict(db.get_all_dynamic_anime_keys())
        if anime_id in dynamic_keys:
            anime_info = {"title": f"🎬 {dynamic_keys[anime_id]}"}
    # Находим оригинальное название озвучки по короткому Latin slug (dub_key)
    dub_name = None
    if dub_id:
        static_dub_id, dub_name = resolve_dubbing_key(anime_id, dub_id)
        if not dub_name:
            dynamic_dubs = db.get_dynamic_dubs(anime_id)
            for d in dynamic_dubs:
                d_slug = re.sub(r'[^a-z0-9]', '', transliterate(d))[:12]
                if d_slug == dub_id:
                    dub_name = d
                    break
        if not dub_name:
            dub_name = dub_id.capitalize()

    s_name = anime_info.get("season_names", {}).get(season_id)
    if arc_slug:
        resolved_arc = resolve_arc_slug(anime_id, season_id, dub_name, arc_slug)
        if resolved_arc:
            s_name = resolved_arc
    if not s_name:
        db_title = db.get_season_title(anime_id, season_id, dub_name)
        s_name = extract_arc_name(db_title)
        if not s_name:
            s_name = f"{season_id} сезон"

    try:
        if callback.message.video or callback.message.document or callback.message.photo:
            ep_keyboard = anime_menu_v2(anime_id, season_id, page, dub_id, arc_slug)
            rating_row = [InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_an_{anime_id}_{i}") for i in range(1, 6)]
            combined_kb = InlineKeyboardMarkup(inline_keyboard=[rating_row] + ep_keyboard.inline_keyboard)
            await callback.message.edit_reply_markup(reply_markup=combined_kb)
        else:
            await callback.message.edit_text(
                f"<b>{clean_anime_title(anime_info['title'])}</b>\n📌 {s_name} | Страница {page}\n\nВыбери серию:",
                reply_markup=anime_menu_v2(anime_id, season_id, page, dub_id, arc_slug),
                parse_mode="HTML"
            )
    except Exception:
        pass


# ОБРАБОТЧИКИ ДЛЯ ИЗБРАННОГО И ИСТОРИИ
# ==========================================

@dp.callback_query(F.data.startswith("fav_toggle|"))
async def fav_toggle_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
        
    _, anime_id = callback.data.split("|", 1)
    user_id = callback.from_user.id
    
    if db.is_favorite(user_id, anime_id):
        db.remove_from_favorites(user_id, anime_id)
        await callback.answer("❌ Удалено из избранного", show_alert=False)
    else:
        db.add_to_favorites(user_id, anime_id)
        await callback.answer("⭐️ Добавлено в избранное!", show_alert=False)
        
    # Обновляем меню выбора аниме
    callback.data = f"anime_{anime_id}"
    await anime_selector(callback)


@dp.callback_query(F.data == "my_favorites")
async def my_favorites_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
        
    user_id = callback.from_user.id
    favorites = db.get_favorites(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    if not favorites:
        text = "⭐️ <b>Моё избранное</b>\n\nУ тебя пока нет избранных аниме. Добавь их, нажав кнопку «⭐️ Добавить в избранное» на странице любого аниме!"
    else:
        text = "⭐️ <b>Моё избранное:</b>\n\nВыбери аниме из списка:"
        for anime_key in favorites:
            anime_info = ANIME_DB.get(anime_key)
            if anime_info:
                title = clean_anime_title(anime_info['title'])
            else:
                dynamic_keys = dict(db.get_all_dynamic_anime_keys())
                title = clean_anime_title(dynamic_keys.get(anime_key, anime_key))
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=title, callback_data=f"anime_{anime_key}")])
            
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="back")])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        try: await callback.message.delete()
        except Exception: pass
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "resume_watch")
async def resume_watch_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
        
    user_id = callback.from_user.id
    last_watched = db.get_last_watched(user_id)
    if not last_watched:
        await callback.answer("❌ История просмотров пуста!", show_alert=True)
        return
        
    anime_id = last_watched['anime_key']
    season_id = last_watched['season_id']
    ep_num = last_watched['episode_num']
    
    anime_info = ANIME_DB.get(anime_id) or {}
    msg_id = None
    dub_key = ""
    
    # Сначала ищем в динамической базе
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_id, dubbing FROM anime_catalog
        WHERE anime_key = ? AND season_id = ? AND episode_num = ?
        ORDER BY added_at DESC LIMIT 1
    """, (anime_id, season_id, ep_num))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        msg_id, dub_name = row
        if dub_name:
            dub_key = slugify(dub_name)
    else:
        # Если нет в динамике, ищем в статике
        if "seasons" in anime_info and season_id in anime_info["seasons"]:
            episodes = anime_info["seasons"][season_id]
            start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
            idx = ep_num - start_ep
            if 0 <= idx < len(episodes):
                msg_id = episodes[idx]
        elif "dubs" in anime_info:
            for d_id, d_info in anime_info["dubs"].items():
                if season_id in d_info.get("seasons", {}):
                    episodes = d_info["seasons"][season_id]
                    start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
                    idx = ep_num - start_ep
                    if 0 <= idx < len(episodes):
                        msg_id = episodes[idx]
                        dub_key = slugify(d_id)
                        break
                        
    if msg_id:
        callback.data = f"ep|{anime_id}|{dub_key}|{season_id}|{msg_id}"
        await episode_selector(callback)
    else:
        await callback.answer("❌ Серия не найдена в базе данных.", show_alert=True)


# Новый формат: ep|anime_id|dub_key|season_id|msg_id
@dp.callback_query(F.data.startswith("ep|"))
async def episode_selector(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return

    # format: ep|anime_id|dub_key|season_id|msg_id
    _, anime_id, dub_key, season_str, ep_str = callback.data.split("|")
    ep = int(ep_str)
    season_id = int(season_str)
    dub_id = dub_key if dub_key else None

    anime_info = ANIME_DB.get(anime_id) or {}

    if ep == 0:
        await callback.answer("⏳ Эта серия еще загружается!", show_alert=True)
        return

    user_id = callback.from_user.id
    gave_reward = False
    current_time = time.time()
    if current_time - USER_REWARD_COOLDOWN.get(user_id, 0) >= 60:
        USER_REWARD_COOLDOWN[user_id] = current_time
        gave_reward = True
        db.increment_request(user_id)

    # Инициализируем переменные по умолчанию
    episodes = []
    full_idx = 0
    page = 1

    meta = db.get_episode_metadata(ep)
    if meta:
        clean_title = meta['title']
        s_name = extract_arc_name(clean_title) or f"{meta['season_id']} сезон"
        ep_num = meta['episode_num']
        quality = meta['quality']
        dubbing = meta['dubbing']
    else:
        clean_title = anime_info.get('title', '').replace("🎬 ", "").replace("🧙‍♀️ ", "").replace("🏴‍☠️ ", "").replace("🔥 ", "").replace("💧 ", "").replace("👼 ", "").strip()
        if dub_id and "dubs" in anime_info:
            static_dub_id, dub_name = resolve_dubbing_key(anime_id, dub_id)
            dub_info = anime_info["dubs"].get(static_dub_id or dub_id, {})
            episodes = dub_info.get("seasons", {}).get(season_id, [])
            quality = dub_info.get("quality", "720p")
            dubbing = dub_name or dub_id.capitalize()
        else:
            episodes = anime_info.get("seasons", {}).get(season_id, [])
            quality = anime_info.get("quality", "720p")
            dubbing = anime_info.get("dubbing", "AnimeVost")

        if ep not in episodes:
            await callback.answer("❌ Эта серия недоступна или была удалена.", show_alert=True)
            return

        s_name = anime_info.get("season_names", {}).get(season_id)
        if not s_name:
            db_title = db.get_season_title(anime_id, season_id, dubbing)
            s_name = extract_arc_name(db_title)
            if not s_name:
                s_name = f"{season_id} сезон"
        full_idx = episodes.index(ep)
        start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
        ep_num = full_idx + start_ep
        page = (full_idx // 12) + 1

    anime_tag = clean_title.replace(" ", "").replace("-", "").replace("—", "").lower()
    custom_ep_name = anime_info.get("episode_names", {}).get(ep) if not meta else None
    if custom_ep_name:
        caption_text = f"<b>{clean_title}</b>\n{custom_ep_name}\nКачество: {quality}\nОзвучка: {dubbing}\n\n#{season_id}{anime_tag}{ep_num}"
    else:
        caption_text = f"<b>{clean_title}</b>\n{s_name} {ep_num} серия\nКачество: {quality}\nОзвучка: {dubbing}\n\n#{season_id}{anime_tag}{ep_num}"

    # Сохраняем просмотр в историю
    db.add_to_history(user_id, anime_id, season_id, ep_num)

    # Находим следующую серию для автоплея и собираем все серии для вычисления текущей страницы
    next_ep_cb = None
    static_dub_id, display_name = resolve_dubbing_key(anime_id, dub_id)
    db_dub_name = static_dub_id or dub_id

    static_eps = []
    if static_dub_id and "dubs" in anime_info:
        raw = anime_info["dubs"].get(static_dub_id, {}).get("seasons", {}).get(season_id, [])
        start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
        static_eps = [(m_id, e_num) for i, m_id in enumerate(raw)]
    elif not dub_id and "seasons" in anime_info:
        raw = anime_info["seasons"].get(season_id, [])
        start_ep = anime_info.get("start_ep", {}).get(season_id, 1)
        static_eps = [(m_id, e_num) for i, m_id in enumerate(raw)]

    dynamic_eps = db.get_dynamic_episodes(anime_id, season_id, dubbing=db_dub_name)

    final_dict = {}
    for m_id, e_num in static_eps:
        final_dict[e_num] = m_id
    for m_id, e_num, is_filler in dynamic_eps:
        if e_num not in final_dict:
            final_dict[e_num] = m_id

    all_eps = sorted([(m_id, e_num) for e_num, m_id in final_dict.items()], key=lambda x: x[1])
    
    current_idx = -1
    for idx, (m_id, e_num) in enumerate(all_eps):
        if m_id == ep:
            current_idx = idx
            break
            
    if current_idx != -1:
        page = (current_idx // 12) + 1
        if current_idx + 1 < len(all_eps):
            next_msg_id = all_eps[current_idx + 1][0]
            next_ep_cb = f"ep|{anime_id}|{dub_id or ''}|{season_id}|{next_msg_id}"

    ep_keyboard = anime_menu_v2(anime_id, season_id, page, dub_id)
    rating_row = [InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_an_{anime_id}_{i}") for i in range(1, 6)]

    inline_kb_list = [rating_row]

    # Проверяем доступность 4K или HD качества для данной серии
    quality_row = []
    if ep_num:
        m_id_4k = db.get_4k_episode(anime_id, ep_num)
        if quality == "4K":
            m_id_hd = db.get_hd_episode(anime_id, ep_num, dubbing)
            if m_id_hd:
                quality_row.append(InlineKeyboardButton(text="📺 Смотреть в HD/1080p", callback_data=f"ep_hd|{anime_id}|{dub_id or ''}|{season_id}|{ep_num}"))
        elif m_id_4k and m_id_4k != ep:
            quality_row.append(InlineKeyboardButton(text="🎥 Смотреть в 4K", callback_data=f"ep_4k|{anime_id}|{dub_id or ''}|{season_id}|{ep_num}"))

    if quality_row:
        inline_kb_list.append(quality_row)

    if next_ep_cb:
        inline_kb_list.append([InlineKeyboardButton(text="▶️ Следующая серия", callback_data=next_ep_cb)])
        
    combined_kb = InlineKeyboardMarkup(inline_keyboard=inline_kb_list + ep_keyboard.inline_keyboard)

    # Отправляем серию через copy_message.
    # Сначала пробуем канал, из которого серия была взята (source_channel в БД),
    # затем перебираем все каналы-источники как fallback.
    sent = False
    ep_meta = db.get_episode_metadata(ep)
    ep_source = ep_meta.get("source_channel") if ep_meta else None

    # Составляем список каналов для попытки: сначала сохранённый источник
    channels_to_try = []
    if ep_source:
        channels_to_try.append(ep_source)
    for ch in ANIME_SOURCE_CHANNELS:
        if ch not in channels_to_try:
            channels_to_try.append(ch)

    for from_chat in channels_to_try:
        try:
            await callback.bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat,
                message_id=ep,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=combined_kb,
            )
            sent = True
            break
        except Exception as e:
            logging.error(f"copy_message ошибка ({from_chat}): {e}")
            err_str = str(e).lower()
            if "message to copy not found" in err_str or "message not found" in err_str:
                # Только если перебрали все каналы — удаляем из БД
                if from_chat == channels_to_try[-1]:
                    if ep_meta:
                        db.delete_episode(ep)
                        logging.info(f"🗑 Серия ID {ep} удалена из БД — не найдена ни в одном канале.")

    if not sent:
        await callback.answer("❌ Ошибка: серия недоступна. Убедись, что бот — администратор канала!", show_alert=True)
        return

    await callback.answer("🍿 Приятного просмотра!")

    if gave_reward:
        db.update_balance(user_id, 10)
        level_up = db.add_xp(user_id, 100)
        if level_up:
            db.update_balance(user_id, 200)
            await bot.send_message(user_id, "🥳 <b>LEVEL UP!</b>\nТвой бонус: +200 баллов.", parse_mode="HTML")
        u_info = db.get_user_info(user_id)
        if u_info and u_info['requests_count'] == 100:
            db.update_balance(user_id, 1000)
            db.add_xp(user_id, 500)
            await bot.send_animation(chat_id=user_id, animation="https://media.tenor.com/KXBZpf5EfQMAAAAC/congratulations.gif",
                caption="🏆 <b>НЕВЕРОЯТНО! НАСТОЯЩИЙ ОТАКУ!</b> 🏆\n\nВы посмотрели уже 100 серий! Бонус: <b>+1000 баллов</b> и <b>+500 XP</b>!", parse_mode="HTML")
        if u_info and u_info['requests_count'] == 1:
            rating_kb_bot = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{i}") for i in range(1, 6)]])
            await bot.send_animation(chat_id=user_id, animation="https://media.tenor.com/vYQaxVAZVaIAAAAC/bon-fire-night-fireworks.gif",
                caption="🎇 <b>С ПЕРВЫМ ПРОСМОТРОМ!</b> 🎇\n\nОцените наш бот:", reply_markup=rating_kb_bot, parse_mode="HTML")
        if episodes and ep == episodes[-1]:
            db.update_balance(user_id, 15)
            await bot.send_message(user_id, "🏆 <b>Сезон завершен!</b>\nБонус: <b>+15 баллов</b>.", parse_mode="HTML")


@dp.callback_query(F.data.startswith("ep_4k|"))
async def episode_4k_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
    _, anime_id, dub_key, season_str, ep_num_str = callback.data.split("|")
    ep_num = int(ep_num_str)
    season_id = int(season_str)
    m_id_4k = db.get_4k_episode(anime_id, ep_num)
    if not m_id_4k:
        await callback.answer("❌ 4K версия для этой серии не найдена.", show_alert=True)
        return
    callback.data = f"ep|{anime_id}|{dub_key}|{season_id}|{m_id_4k}"
    await episode_selector(callback)


@dp.callback_query(F.data.startswith("ep_hd|"))
async def episode_hd_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass
    _, anime_id, dub_key, season_str, ep_num_str = callback.data.split("|")
    ep_num = int(ep_num_str)
    season_id = int(season_str)
    static_dub_id, dub_name = resolve_dubbing_key(anime_id, dub_key)
    m_id_hd = db.get_hd_episode(anime_id, ep_num, dub_name)
    if not m_id_hd:
        await callback.answer("❌ HD версия для этой серии не найдена.", show_alert=True)
        return
    callback.data = f"ep|{anime_id}|{dub_key}|{season_id}|{m_id_hd}"
    await episode_selector(callback)


@dp.callback_query(F.data.startswith("rate_an_"))
async def rate_anime_handler(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    parts = callback.data.split("_")
    rating = int(parts[-1])
    anime_id = "_".join(parts[2:-1])

    db.set_anime_rating(callback.from_user.id, anime_id, rating)

    rating_info = db.get_anime_rating_info(anime_id)
    # Re-using the prompt message or sending alert
    try:
        await callback.message.answer(f"✅ Твоя оценка {rating} ⭐ принята!\nТеперь у аниме рэйтинг {rating_info['avg']} ⭐")
    except Exception:
        pass


@dp.callback_query(F.data == "top_list")
async def top_list_handler(callback: CallbackQuery):
    if not await restrict_unsubscribed(callback):
        return
    try:
        await callback.answer()
    except Exception:
        pass

    top_data = db.get_top_anime(10)

    if not top_data:
        text = "😔 <b>Топ пока пуст!</b>\nСтаньте первым, кто поставит оценку любому аниме!"
    else:
        text = "🏆 <b>ТОП-10 ПОПУЛЯРНЫХ АНИМЕ:</b>\n"
        text += "━━━━━━━━━━━━━━\n"
        for i, (anime_id, avg, count) in enumerate(top_data, 1):
            anime_title = ANIME_DB.get(anime_id, {}).get("title", "Неизвестно")
            text += f"{i}. <b>{anime_title}</b>\n   ⭐️ {avg} ({count} гол.)\n\n"
        text += "━━━━━━━━━━━━━━\n"
        text += "🍿 <i>Нажми на аниме ниже, чтобы смотреть:</i>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for anime_id, avg, count in top_data:
        anime_title = ANIME_DB.get(anime_id, {}).get("title", "Аниме")
        # Убираем эмодзи из начала если есть, для кнопок
        clean_title = anime_title.split(" ", 1)[-1] if " " in anime_title else anime_title
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=clean_title, callback_data=f"anime_{anime_id}")])

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")



@dp.callback_query(F.data.startswith("rate_"))
async def rate_handler(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    rating = callback.data.split("_")[1]

    # Уведомляем пользователя (меняем подпись у гифки)
    try:
        await callback.message.edit_caption(
            caption=f"🎇 <b>С ПЕРВЫМ ПРОСМОТРОМ!</b> 🎇\n\n✅ Спасибо за вашу оценку в <b>{rating} ⭐</b>!\nМы очень ценим ваш отзыв.",
            parse_mode="HTML"
        )
    except Exception as e:
        # Если гифка удалена или что-то пошло не так
        await callback.answer(f"Спасибо за {rating} звезд!", show_alert=True)

    # Отправляем сообщение админам
    username_text = f"@{callback.from_user.username}" if callback.from_user.username else f"Пользователь с ID {callback.from_user.id}"
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=f"📊 <b>Новая оценка бота!</b>\n\n{username_text} поставил боту: <b>{rating} ⭐</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

# =========================
# АДМИН-КОМАНДЫ
# =========================
@dp.message(Command("news"))
async def cmd_news_template(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    template_text = (
        "Рассылка/Пост\n\n"
        "🔔 <b>ВНИМАНИЕ, ДОРОГИЕ ЗРИТЕЛИ!</b> 🔔\n\n"
        "👉 [Ваш заголовок]\n\n"
        "[Здесь ваш текст новости. Напишите, что добавили новое аниме, новую серию или важную информацию о боте]\n\n"
        "👇 <i>С уважением, Администрация проекта.</i>"
    )

    await message.answer(
        "📝 <b>Вот ваш шаблон для новости!</b>\n\n"
        "Скопируйте текст ниже, вставьте его в строку ввода, исправьте под себя (замените текст в скобках) и просто <b>ответьте (Reply)</b> на свое готовое сообщение командой <code>/send</code>.",
        parse_mode="HTML"
    )
    # Отправляем сам текст без форматирования HTML, чтобы админу было удобно его скопировать
    await message.answer(f"<code>{template_text}</code>", parse_mode="HTML")

@dp.message(Command("send"))
async def send_newsletter(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return

    users_info = db.get_all_users_info()
    if not users_info:
        await message.answer("❌ База пользователей пуста.")
        return

    content_is_post = False
    anime_post_text = ""
    post_keyboard = None

    if command.args and not message.reply_to_message:
        parts = command.args.split()
        if len(parts) >= 2 and parts[0] in ANIME_DB:
            anime_id = parts[0]
            try:
                season_id = int(parts[1])
                anime_info = ANIME_DB[anime_id]
                s_name = anime_info.get("season_names", {}).get(season_id, f"{season_id} сезон")
                quality = anime_info.get("quality", "1080p ✨")
                dubbing = anime_info.get("dubbing", " ANIMEVOST 🎙")

                bot_info = await bot.get_me()
                post_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🍿 Смотреть в боте", url=f"https://t.me/{bot_info.username}")]
                ])

                anime_post_text = (
                    f"🔥 <b>НОВЫЕ СЕРИИ УЖЕ В БОТЕ!</b> 🔥\n\n"
                    f"{anime_info['title']}\n"
                    f"📺 Сезон: {s_name}\n"
                    f"📀 Качество: {quality}\n"
                    f"🗣 Озвучка: {dubbing}\n\n"
                    f"👇 Скорее переходи и смотри прямо в Telegram без рекламы!"
                )
                content_is_post = True
            except ValueError:
                pass

    if message.reply_to_message:
        content = message.reply_to_message
    elif content_is_post:
        content = anime_post_text
    elif command.args:
        content = command.args
    else:
        await message.answer(
            "⚠️ <b>Как использовать рассылку:</b>\n\n"
            "1. Рассылка текста: <code>/send Ваш текст</code>\n"
            "2. Пересылка: Ответьте на сообщение командой <code>/send</code>\n"
            "3. <b>Анонс аниме:</b> <code>/send [айди] [сезон]</code> (Например: <code>/send slime 4</code>)\n"
            "   <i>Бот автоматически сверстает пост и отправит его в Канал и всем пользователям!</i>",
            parse_mode="HTML"
        )
        return

    # Отправка в канал, если это анонс
    if content_is_post:
        try:
            await bot.send_message(chat_id=CHANNEL_ANIME, text=content, reply_markup=post_keyboard, parse_mode="HTML", disable_web_page_preview=True)
            await message.answer(f"✅ Пост успешно опубликован на канале {CHANNEL_ANIME}!")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка публикации в канал: {e}")

    status_msg = await message.answer(f"⏳ Начинаю рассылку для {len(users_info)} пользователей...")

    success, fail = 0, 0
    errors = []
    delivered_to = []
    broadcast_id = db.create_broadcast()

    try:
        for i, info in enumerate(users_info):
            user_id = info["user_id"]
            name = info["full_name"] or info["username"] or f"ID: {user_id}"

            try:
                if isinstance(content, str):
                    if content_is_post:
                        sent = await bot.send_message(chat_id=user_id, text=content, reply_markup=post_keyboard, parse_mode="HTML", disable_web_page_preview=True)
                    else:
                        sent = await bot.send_message(chat_id=user_id, text=content, disable_web_page_preview=True)
                else:
                    sent = await content.copy_to(chat_id=user_id)

                db.save_sent_message(broadcast_id, user_id, sent.message_id)
                success += 1
                delivered_to.append(name)
            except Exception as e:
                fail += 1
                errors.append((user_id, name, str(e)))
                logging.warning(f"[Рассылка] Ошибка у {name} ({user_id}): {e}")

            if (i + 1) % 15 == 0:
                try:
                    await status_msg.edit_text(f"⏳ Рассылка: {i+1}/{len(users_info)} | ✅ {success} / ❌ {fail}")
                except Exception:
                    pass

            await asyncio.sleep(0.05)


        # Формируем итоговый отчёт
        report = (
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"👤 Всего: <b>{len(users_info)}</b>\n"
            f"✅ Успешно: <b>{success}</b>\n"
            f"❌ Ошибок: <b>{fail}</b>\n\n"
        )

        if delivered_to:
            report += "📥 <b>Сообщение получили:</b>\n"
            names_text = ", ".join(delivered_to[:50]) # Показываем первые 50 имен
            report += f"<i>{names_text}</i>"
            if len(delivered_to) > 50:
                report += f" ...и еще {len(delivered_to) - 50} чел."
            report += "\n\n"

        if errors:
            report += "⚠️ <b>Ошибки отправки:</b>\n"
            for uid, uname, reason in errors[:10]:
                report += f"• {uname} (<code>{uid}</code>): {reason[:50]}\n"

        report += "\n💡 Чтобы удалить эту рассылку у всех, введи: /del"

        await message.answer(report, parse_mode="HTML")

    except Exception as critical_error:
        logging.error(f"[Рассылка] Критическая ошибка: {critical_error}")
        await message.answer(f"🚨 <b>Критическая ошибка!</b>\n<code>{str(critical_error)[:200]}</code>", parse_mode="HTML")

@dp.message(Command("clone_jjk"))
async def cmd_clone_jjk(message: Message):
    """Команда для клонирования серий JJK с поиском"""
    if message.from_user.id not in ADMIN_IDS:
        return

    source_channel = "@Magicheskayabitva_Animehd"
    target_channel = CHANNEL_ANIME

    # Попробуем найти серии в диапазоне от 1 до 50
    status_msg = await message.answer(f"⏳ Ищу серии в {source_channel} и копирую в {target_channel}...")

    success_count = 0
    for i in range(1, 51):
        try:
            # Сначала пытаемся просто получить информацию о сообщении (или копируем)
            # Если в канале стоит защита от копирования, это может не сработать
            sent = await bot.copy_message(
                chat_id=target_channel,
                from_chat_id=source_channel,
                message_id=i,
                caption=f"Магическая битва\nСерия найдена (ID: {i})\nОзвучка: Anilibria\n\n#jjk_clone",
                parse_mode="HTML"
            )
            success_count += 1
            await status_msg.edit_text(f"✅ Нашел и скопировал сообщение №{i}. Всего: {success_count}")
            await asyncio.sleep(3) # Увеличим задержку
        except Exception as e:
            # Если сообщения нет или ошибка доступа
            logging.info(f"Сообщение {i} пропущено: {e}")
            continue

    await status_msg.edit_text(f"✅ Поиск завершен! Успешно перенесено: {success_count} сообщений.")

@dp.message(Command("del"))
async def delete_last_broadcast(message: Message):
    """Удаляет сообщения последней рассылки у всех пользователей"""
    if message.from_user.id not in ADMIN_IDS:
        return

    messages = db.get_last_broadcast_messages()
    if not messages:
        await message.answer("❌ Нет данных о последней рассылке для удаления.")
        return

    status_msg = await message.answer(f"⏳ Начинаю удаление у {len(messages)} пользователей...")

    deleted, failed = 0, 0
    for i, (user_id, msg_id) in enumerate(messages):
        try:
            await bot.delete_message(chat_id=user_id, message_id=msg_id)
            deleted += 1
        except Exception:
            failed += 1

        if (i + 1) % 20 == 0:
            try: await status_msg.edit_text(f"⏳ Удаление: {i+1}/{len(messages)}...")
            except Exception: pass

        await asyncio.sleep(0.04)

    await message.answer(
        f"🗑 <b>Удаление завершено!</b>\n\n"
        f"✅ Удалено сообщений: {deleted}\n"
        f"❌ Не удалось "
        f"(уже удалено или бот заблокирован): {failed}",
        parse_mode="HTML"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = command.args.split() if command.args else []

    if not args:
        stats = db.get_global_stats()
        report = (
            "📊 <b>АДМИН-СТАТИСТИКА</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"👥 Пользователи: <b>{stats['total_users']}</b>\n"
            f"🔥 Активные: <b>{stats['active_users']}</b>\n"
            f"🍿 Просмотры: <b>{stats['total_views']}</b>\n\n"
            "💡 Команды:\n"
            "<code>/stats list</code> — список всех\n"
            "<code>/stats [ID]</code> — инфо о юзере"
        )
        await message.answer(report, parse_mode="HTML")

    elif args[0] == "list":
        users = db.get_all_users_detailed()
        text = "📋 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ:</b>\n\n"
        for u in users[:20]: # Лимит 20 для сообщения
            text += f"• <code>{u[0]}</code> | Lvl {u[3]} | {u[2] or 'User'}\n"
        if len(users) > 20: text += f"\n<i>...и еще {len(users)-20} чел.</i>"
        await message.answer(text, parse_mode="HTML")

    else:
        try:
            target_id = int(args[0])
            u = db.get_user_info(target_id)
            if u:
                text = (
                    f"👤 <b>ИНФО О ЮЗЕРЕ:</b>\n"
                    f"🆔 ID: <code>{u['user_id']}</code>\n"
                    f"📝 Имя: {u['full_name']}\n"
                    f"🌟 Уровень: {u['level']} ({u['xp']} XP)\n"
                    f"💰 Баланс: {u['balance']}\n"
                    f"🍿 Просмотры: {u['requests_count']}"
                )
                await message.answer(text, parse_mode="HTML")
            else:
                await message.answer("❌ Пользователь не найден.")
        except ValueError:
            await message.answer("❌ Неверный формат ID.")


@dp.message(Command("users"))
async def cmd_users_legacy(message: Message, command: CommandObject):
    await cmd_stats(message, command)

def parse_caption_to_episode(caption: str, message_id: int, source_channel: str = None) -> dict | None:
    """Парсит описание поста и возвращает данные эпизода или None"""
    caption = caption.replace('\r', '').strip()

    # Игнорируем эдиты, AMV и стикеры
    bad_words = ["edit", "эдит", "amv", "тикток", "tiktok", "amw"]
    if any(word in caption.lower() for word in bad_words):
        return None

    # ============================================================
    # СПЕЦИАЛЬНЫЙ ПАРСЕР ДЛЯ ВАН-ПИС (ONE PIECE) ПО ЦИФРАМ (НОМЕРУ СЕРИИ)
    # ============================================================
    caption_lower = caption.lower()
    op_channels = ["@shachiburi_one_piece"]
    is_op_channel = source_channel in op_channels
    is_op_text = (
        "ванпис" in caption_lower or
        "ван-пис" in caption_lower or
        "ван пис" in caption_lower or
        "one piece" in caption_lower or
        "#onepiece" in caption_lower or
        "#ванпис" in caption_lower or
        "эльбаф" in caption_lower or
        "egghead" in caption_lower or
        "эггхед" in caption_lower or
        "вегапанк" in caption_lower or
        "луффи" in caption_lower or
        "luffy" in caption_lower or
        "shachiburi" in caption_lower or
        "шачибури" in caption_lower
    )
    is_op = is_op_channel or is_op_text

    # Поиск номера серии строго по цифрам
    ep_match = re.search(r"(\d+)\s*(?:серия|qism|seriya|ep|e)\b", caption, re.I)
    if not ep_match:
        ep_match = re.search(r"(?:серия|episode|ep)\s*[:\-]?\s*(\d+)\b", caption, re.I)
    if not ep_match:
        ep_match = re.search(r"#серия_?(\d+)\b", caption, re.I)
    if not ep_match:
        ep_match = re.search(r"#(\d+)\s*серия\b", caption, re.I)
    if not ep_match:
        ep_match = re.search(r"(\d+)\s*\.", caption)
    if not ep_match:
        ep_match = re.search(r"^\s*(\d+)\b", caption)
    if not ep_match and is_op:
        # Fallback: берем первое подходящее число (не являющееся разрешением 480, 720, 1080, 2160)
        nums = [int(n) for n in re.findall(r"\b\d+\b", caption) if int(n) not in (480, 720, 1080, 2160, 4)]
        if nums:
            episode_num = nums[0]
            ep_match = True
        else:
            ep_match = None

    if ep_match and is_op:
        if not isinstance(ep_match, bool):
            episode_num = int(ep_match.group(1))

        if "макс летов" in caption_lower or "макса летова" in caption_lower:
            dubbing = "Субтитры (Макс Летов)"
        elif "субтитры" in caption_lower or "subtitles" in caption_lower or "субтитр" in caption_lower:
            dubbing = "Субтитры"
        else:
            dubbing = "Shachiburi"

        if "4к" in caption_lower or "4k" in caption_lower or "2160p" in caption_lower:
            quality = "4K"
        elif "1080p" in caption_lower or "1080" in caption_lower:
            quality = "1080p"
        elif "480p" in caption_lower or "480" in caption_lower:
            quality = "480p"
        else:
            quality = "720p"

        arc_id, arc_name, is_filler = get_one_piece_arc(episode_num)

        return {
            "message_id": message_id,
            "anime_key": "op_elbaf",
            "title": "🏴‍☠️ Ван-Пис",
            "season_id": arc_id,
            "episode_num": episode_num,
            "quality": quality,
            "dubbing": dubbing,
            "is_filler": 1 if is_filler else 0,
            "arc_name": arc_name,
            "source_channel": source_channel,
        }

    # ============================================================
    # СПЕЦИАЛЬНЫЙ ПАРСЕР ДЛЯ ХАНТЕР Х ХАНТЕР (HUNTER X HUNTER) ПО СЕРИИ
    # ============================================================
    hxh_channels = ["@huntenters"]
    is_hxh_channel = source_channel in hxh_channels
    is_hxh_text = (
        "хантер" in caption_lower or
        "hunter" in caption_lower or
        "hxh" in caption_lower or
        "#hunterxhunter" in caption_lower or
        "#хантер" in caption_lower or
        "золдик" in caption_lower or
        "йоркнью" in caption_lower or
        "йоркшин" in caption_lower or
        "муравьи-химеры" in caption_lower or
        "химеры" in caption_lower or
        "остров жадности" in caption_lower or
        "небесная арена" in caption_lower or
        "экзамен на охотника" in caption_lower
    )
    is_hxh = is_hxh_channel or is_hxh_text

    if ep_match and is_hxh and not is_op:
        if not isinstance(ep_match, bool):
            episode_num = int(ep_match.group(1))

        if 1 <= episode_num <= 148:
            dub_match = re.search(r"(?:Озвучка|Dub|Ovoz|Dublyaj|Ovozlash)[:\s]+([^\n]+)", caption, re.I)
            dubbing = dub_match.group(1).strip() if dub_match else "Дубляж"
            q_match = re.search(r"(?:Качество|Quality|Sifat|Sifati)[:\s]*(\S+)", caption, re.I)
            quality = q_match.group(1).strip() if q_match else "720p"

            arc_id, arc_name, is_filler = get_hunter_x_hunter_arc(episode_num)

            return {
                "message_id": message_id,
                "anime_key": "hunter_x_hunter",
                "title": "🎣 Хантер х Хантер",
                "season_id": arc_id,
                "episode_num": episode_num,
                "quality": quality,
                "dubbing": dubbing,
                "is_filler": 1 if is_filler else 0,
                "arc_name": arc_name,
                "source_channel": source_channel,
            }

    # ============================================================
    # СПЕЦИАЛЬНЫЙ ПАРСЕР: формат каналов AniVosto / TeliusOFF_Anime
    # Пример:
    # 🌸 Аниме: 100 девушек, которые очень сильно тебя любят 3 / Kimi no ...
    # 🌸 Серия: 5 из 12
    # 🌸 Формат: TV             <- игнорируем
    # 🌸 Возрастной рейтинг: 16+ <- игнорируем
    # 🌸 Жанр: ...              <- игнорируем
    # 🌸 Озвучка: AniLiberty
    # 🌸 Год выпуска: ...       <- игнорируем
    # 🌸 Премьера: ...          <- игнорируем
    # #хэштег
    # ============================================================
    if "🌸 аниме:" in caption.lower() or re.search(r"🌸\s*аниме\s*:", caption, re.I):
        flower_title = None
        flower_episode = None
        flower_season = None
        flower_dubbing = "Неизвестно"
        flower_quality = "720p"
        flower_arc = None
        flower_hashtag = None

        for line in caption.splitlines():
            line = line.strip()
            if not line:
                continue

            # 🌸 Аниме: <русское название> / <ромадзи или другое>
            m = re.match(r"🌸\s*аниме\s*:\s*(.+)", line, re.I)
            if m:
                raw_title = m.group(1).strip()
                slash_idx = raw_title.find(" /")
                if slash_idx != -1:
                    flower_title = raw_title[:slash_idx].strip()
                else:
                    slash_idx2 = raw_title.find("/")
                    if slash_idx2 != -1:
                        before = raw_title[:slash_idx2].strip()
                        if re.search(r"[а-яёА-ЯЁ]", before):
                            flower_title = before
                        else:
                            flower_title = raw_title
                    else:
                        flower_title = raw_title
                continue

            # 🌸 Серия: 5 из 12
            m = re.match(r"🌸\s*серия\s*:\s*(\d+)(?:\s+из\s+\d+)?", line, re.I)
            if m:
                flower_episode = int(m.group(1))
                continue

            # 🌸 Озвучка: AniLiberty
            m = re.match(r"🌸\s*озвучка\s*:\s*(.+)", line, re.I)
            if m:
                flower_dubbing = m.group(1).strip()
                continue

            # 🌸 Качество: 1080p
            m = re.match(r"🌸\s*качество\s*:\s*(\S+)", line, re.I)
            if m:
                flower_quality = m.group(1).strip()
                continue

            # Хэштег
            if line.startswith("#") and flower_hashtag is None:
                flower_hashtag = line.lstrip("#").strip()

            # Сезон
            m_s = re.search(r"(\d+)\s*(?:сезон|season)", line, re.I)
            if m_s and flower_season is None:
                flower_season = int(m_s.group(1))

        if flower_title and flower_episode is not None:
            anime_key = None
            if flower_hashtag:
                tag_name = re.sub(r'^\d+', '', flower_hashtag)
                tag_name = re.sub(r'\d+$', '', tag_name).lower()
                db_hashtag_info = db.get_anime_key_by_hashtag(tag_name)
                if db_hashtag_info:
                    anime_key = db_hashtag_info["anime_key"]
                    flower_title = db_hashtag_info["anime_title"]
                else:
                    for key, info in ANIME_DB.items():
                        db_clean = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', info['title']).lower()
                        short_tags = [t.lower() for t in info.get("short_tags", [])]
                        if tag_name == db_clean or tag_name in short_tags:
                            anime_key = key
                            break

            if not anime_key:
                clean_title = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', flower_title).lower()
                caption_clean_all = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', caption).lower()
                for key, info in ANIME_DB.items():
                    db_clean = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', info['title']).lower()
                    short_tags = [t.lower() for t in info.get("short_tags", [])]
                    if clean_title == db_clean or clean_title in short_tags or any(tag in clean_title for tag in short_tags if len(tag) >= 4) or any(tag in caption_clean_all for tag in short_tags if len(tag) >= 5):
                        anime_key = key
                        flower_title = info['title']
                        break

            if not anime_key:
                latin_title = transliterate(flower_title)
                anime_key = re.sub(r'[^a-z0-9_]', '', re.sub(r'\s+', '_', latin_title.lower().strip()))[:20]
                anime_key = re.sub(r'_+', '_', anime_key).strip('_')
                if not anime_key:
                    anime_key = "unknown_anime"

            season_id = flower_season if flower_season else 1

            return {
                "message_id": message_id,
                "anime_key": anime_key,
                "title": flower_title,
                "season_id": season_id,
                "episode_num": flower_episode,
                "quality": flower_quality,
                "dubbing": flower_dubbing,
                "is_filler": 0,
                "arc_name": flower_arc,
                "source_channel": source_channel,
            }
        else:
            return None


    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    title_line = ""
    arc_name = None

    # Ищем арку только в начале строки, чтобы не ловить случайные упоминания
    for line in lines:
        arc_match = re.match(r"^(?:арка|arc)\s*[:\-]?\s*(.+)$", line, re.I)
        if arc_match:
            arc_name = arc_match.group(1).strip()
            break

    # Ищем арку в хэштегах (#Полугодовая_тренировка и др.)
    hashtags_all = re.findall(r"#([a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9_]+)", caption)
    if not arc_name and hashtags_all:
        for tag in hashtags_all:
            tag_clean = tag.lower()
            if any(w in tag_clean for w in ["тренировк", "арка", "битва", "экзамен", "война", "рейд", "остров"]):
                arc_name = tag.replace("_", " ").strip()
                break

    # Находим первую строку, которая содержит название (не является только служебной строкой)
    for line in lines:
        if re.match(r"^(?:арка|arc|серия|episode|сезон|season|Качество|Озвучка|Sifat|Ovoz|Dublyaj|\d+[\s\-]*(?:серия|сезон|qism|ep|s))\b", line, re.I):
            continue
        if re.search(r"[а-яёА-ЯЁa-zA-Z]", line):
            title_line = line
            break
    if not title_line and lines:
        title_line = lines[0]

    # Если название содержит метки арки, вырезаем их
    title_line = re.sub(r"(?:арка|arc)\s*[:\-]?\s*([^\n]+)", "", title_line, flags=re.I).strip()

    # Название = всё до первого числа/метки сезона/серии/качества/озвучки
    title_end = re.search(
        r"(?:\d+\s*(?:сезон|mavsum|fasl)|\d+\s*(?:серия|qism|seriya)|"
        r"Качество:|Озвучка:|Sifat:|Ovoz:|Dublyaj:|season|episode)",
        title_line,
        re.I
    )
    if title_end:
        title = title_line[:title_end.start()].replace("🎬", "").strip()
    else:
        title = title_line.replace("🎬", "").strip()

    title = re.sub(r"\b(?:арка|arc)\s*[:\-]?\s*", "", title, flags=re.I).strip()
    title = re.sub(r"^[#\s]*\d+[\s#:\-]*", "", title).strip()
    title = re.sub(r"\s{2,}", " ", title).strip()

    # Гибкий поиск сезона (рус/англ/узб)
    season_match = re.search(
        r"(?:season|сезон|mavsum|fasl|s)[ \t]*[:\-]?[ \t]*(\d+)|"
        r"(\d+)[ \t]*(?:season|сезон|mavsum|fasl|s)",
        caption,
        re.I
    )

    # Гибкий поиск серии (рус/англ/узб/хэштеги #серия154)
    episode_match = re.search(
        r"(?:episode|серия|qism|seriya|ep|e)[ \t]*[:\-]?[ \t]*(\d+)|"
        r"(\d+)[ \t]*(?:episode|серия|qism|seriya|ep|e)",
        caption,
        re.I
    )
    if not episode_match:
        episode_match = re.search(r"#серия_?(\d+)\b", caption, re.I)
    if not episode_match:
        episode_match = re.search(r"#(\d+)\s*серия\b", caption, re.I)

    if not episode_match:
        return None  # Если нет слова "серия"/"qism" — пропускаем

    episode_num = int(episode_match.group(1) or episode_match.group(2))

    quality_match = re.search(r"(?:Качество|Quality|Sifat|Sifati):\s*(\S+)", caption, re.I)
    dubbing_match = re.search(r"(?:Озвучка|Dub|Ovoz|Dublyaj|Ovozlash):\s*([^\n]+)", caption, re.I)

    quality = quality_match.group(1).strip() if quality_match else "720p"
    dubbing = dubbing_match.group(1).strip() if dubbing_match else "Неизвестно"
    anime_key = None

    # 1. Сначала пробуем через хештеги (самый точный способ)
    hashtags = re.findall(r"#([a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]+)", caption)
    if hashtags:
        for tag_raw in hashtags:
            tag_name = re.sub(r'^\d+', '', tag_raw)
            tag_name = re.sub(r'\d+$', '', tag_name).lower()
            
            db_hashtag_info = db.get_anime_key_by_hashtag(tag_name)
            if db_hashtag_info:
                anime_key = db_hashtag_info["anime_key"]
                title = db_hashtag_info["anime_title"]
                break
                
            for key, info in ANIME_DB.items():
                db_clean = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', info['title']).lower()
                short_tags = [t.lower() for t in info.get("short_tags", [])]
                if tag_name == db_clean or tag_name in short_tags:
                    anime_key = key
                    title = info['title']
                    break
            if anime_key: break

    # 2. Если по хештегу не нашли, ищем по названию и по тексту поста
    if not anime_key:
        clean_title = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', title).lower()
        caption_clean_all = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', caption).lower()
        for key, info in ANIME_DB.items():
            db_clean = re.sub(r'[^a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u04010-9]', '', info['title']).lower()
            short_tags = [t.lower() for t in info.get("short_tags", [])]
            if clean_title == db_clean or clean_title in short_tags or any(tag in clean_title for tag in short_tags if len(tag) >= 4) or any(tag in caption_clean_all for tag in short_tags if len(tag) >= 5):
                anime_key = key
                title = info['title']
                break

        # Специальное правило для Ван-Пис / Хантер х Хантер
        if not anime_key:
            if "эльбаф" in caption_lower or "ванпис" in caption_lower or "onepiece" in caption_lower:
                anime_key = "op_elbaf"
                title = "🏴‍☠️ Ван-Пис"
            elif "хантер" in caption_lower or "hunter" in caption_lower or "hxh" in caption_lower:
                anime_key = "hunter_x_hunter"
                title = "🎣 Хантер х Хантер"

    if not anime_key:
        latin_title = transliterate(title)
        anime_key = re.sub(r'[^a-z0-9_]', '', re.sub(r'\s+', '_', latin_title.lower().strip()))[:20]
        anime_key = re.sub(r'_+', '_', anime_key).strip('_')
        if not anime_key: anime_key = "unknown_anime"

    # Вычисляем season_id
    if anime_key == "hunter_x_hunter" and 1 <= episode_num <= 148:
        arc_id, arc_name, is_filler = get_hunter_x_hunter_arc(episode_num)
        season_id = arc_id
    elif season_match:
        season_id = int(season_match.group(1) or season_match.group(2))
    elif arc_name:
        max_static = 1
        if anime_key in ANIME_DB:
            seasons = ANIME_DB[anime_key].get("seasons", {}).keys()
            season_names = ANIME_DB[anime_key].get("season_names", {}).keys()
            all_static_seasons = list(seasons) + list(season_names)
            if all_static_seasons:
                max_static = max(all_static_seasons)
        season_id = db.get_or_create_season_id_for_arc(anime_key, arc_name, dubbing, max_static)
    else:
        season_id = 1

    # Проверяем, является ли серия филлером
    is_filler = 0
    if "filler" in caption.lower() or "филлер" in caption.lower():
        is_filler = 1

    return {
        "message_id": message_id,
        "anime_key": anime_key,
        "title": title,
        "season_id": season_id,
        "episode_num": episode_num,
        "quality": quality,
        "dubbing": dubbing,
        "is_filler": is_filler,
        "arc_name": arc_name,
        "source_channel": source_channel,
    }


@dp.message(Command("scan"))
async def cmd_scan_message(message: Message):
    """Команда /scan для запуска сканирования"""
    await cmd_scan_channel(message)

@dp.callback_query(F.data == "admin_cleanup")
async def cmd_admin_cleanup(callback: CallbackQuery):
    """Вручную запускает очистку базы от удалённых серий"""
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.answer()
    
    status = await callback.message.answer(
        "🧹 <b>Запускаю проверку базы...</b>\nПроверяю все серии в канале, это может занять несколько минут.",
        parse_mode="HTML"
    )
    
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT message_id FROM anime_catalog")
    rows = cursor.fetchall()
    conn.close()
    
    message_ids = [row[0] for row in rows]
    deleted_count = 0
    total = len(message_ids)
    
    for i, msg_id in enumerate(message_ids):
        try:
            bot_info = await bot.get_me()
            await bot.copy_message(
                chat_id=bot_info.id,
                from_chat_id=CHANNEL_ANIME,
                message_id=msg_id,
                disable_notification=True
            )
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in [
                "message to copy not found", "message not found",
                "invalid message", "message_id_invalid",
                "message to forward not found"
            ]):
                db.delete_episode(msg_id)
                deleted_count += 1
        
        # Обновляем статус каждые 50 сообщений
        if (i + 1) % 50 == 0:
            try:
                await status.edit_text(
                    f"🧹 <b>Проверка...</b>\nПроверено: {i+1}/{total}\nУдалено из базы: {deleted_count}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.4)
    
    await status.edit_text(
        f"✅ <b>Очистка завершена!</b>\n\n"
        f"🔍 Проверено серий: <b>{total}</b>\n"
        f"🗑 Удалено из базы: <b>{deleted_count}</b>\n\n"
        f"{'Теперь удалённые сезоны и серии не будут появляться в меню.' if deleted_count > 0 else 'Все серии в канале на месте.'}",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_scan")
async def cmd_scan_channel(event: Message | CallbackQuery):
    """Выводит меню выбора канала для сканирования «до конца»"""
    user_id = event.from_user.id
    if user_id not in ADMIN_IDS:
        return

    if isinstance(event, CallbackQuery):
        try:
            await event.answer()
        except Exception:
            pass
        message = event.message
    else:
        message = event

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for ch in ANIME_SOURCE_CHANNELS:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"📡 {ch}", callback_data=f"scan_ch|{ch}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🌐 Сканировать ВСЕ каналы", callback_data="scan_ch|all")
    ])
    keyboard.inline_keyboard.append(home_button())

    text = (
        "📡 <b>ВЫБОР КАНАЛА ДЛЯ СКАНИРОВАНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите канал, который вы хотите отсканировать <b>до конца</b>:\n\n"
        "<i>(Бот отсканирует все посты канала с самых свежих до 1-го сообщения)</i>"
    )

    if isinstance(event, CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

async def get_channel_last_message_id(source_ch: str, admin_chat_id: int) -> int:
    """Быстро и безопасно находит максимальный message_id канала"""
    # 1. Попытка отправить временное сообщение
    try:
        temp_msg = await bot.send_message(source_ch, "⌛ <i>Синхронизация...</i>", parse_mode="HTML")
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
                    chat_id=admin_chat_id,
                    from_chat_id=source_ch,
                    message_id=mid,
                    disable_notification=True
                )
                try:
                    await bot.delete_message(admin_chat_id, fwd.message_id)
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

@dp.callback_query(F.data.startswith("scan_ch|"))
async def scan_channel_start_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    try:
        await callback.answer()
    except Exception:
        pass

    target_ch = callback.data.split("|")[1]
    if target_ch == "all":
        channels_to_scan = ANIME_SOURCE_CHANNELS
        label_text = f"ВСЕХ ({len(ANIME_SOURCE_CHANNELS)}) каналов"
    else:
        channels_to_scan = [target_ch]
        label_text = f"канала <code>{target_ch}</code>"

    status = await callback.message.edit_text(
        f"🔍 <b>Запускаю глубокое сканирование {label_text}...</b>\n"
        "Сканирование идет от последнего сообщения к 1-му. Пожалуйста, подождите.",
        parse_mode="HTML"
    )

    total_added = 0
    admin_chat_id = callback.message.chat.id

    for source_ch in channels_to_scan:
        added = 0
        try:
            await status.edit_text(
                f"🔍 <b>Определяю последнее сообщение в {source_ch}...</b>\n"
                f"📥 Всего добавлено серий: <b>{total_added}</b>",
                parse_mode="HTML"
            )

            max_id = await get_channel_last_message_id(source_ch, admin_chat_id)
            if max_id <= 1:
                logging.warning(f"Канал {source_ch} недоступен или пуст (max_id={max_id})")
                continue

            MAX_EMPTY_STREAK = 5000
            empty_streak = 0
            last_status_update = time.time()

            for mid in range(max_id, 0, -1):
                try:
                    fwd = await bot.forward_message(
                        chat_id=admin_chat_id,
                        from_chat_id=source_ch,
                        message_id=mid,
                        disable_notification=True
                    )
                    empty_streak = 0

                    caption = fwd.caption or fwd.text
                    has_video = bool(fwd.video or fwd.document)

                    try:
                        await bot.delete_message(chat_id=admin_chat_id, message_id=fwd.message_id)
                    except Exception:
                        pass

                    if has_video and caption:
                        ep_data = parse_caption_to_episode(caption, mid, source_channel=source_ch)
                        if ep_data:
                            db.add_dynamic_episode(**ep_data)
                            added += 1
                            total_added += 1

                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after + 1)
                    continue
                except Exception:
                    empty_streak += 1
                    if empty_streak > MAX_EMPTY_STREAK:
                        break

                checked_count = max_id - mid + 1
                now = time.time()
                if now - last_status_update >= 2.5 or mid == 1:
                    last_status_update = now
                    percent = int((checked_count / max_id) * 100) if max_id > 0 else 0
                    try:
                        await status.edit_text(
                            f"🔍 <b>Сканирование {source_ch}:</b>\n"
                            f"📥 Добавлено из этого канала: <b>{added}</b>\n"
                            f"⏩ Проверено: <b>{checked_count}/{max_id}</b> ({percent}%)\n"
                            f"📊 Всего добавлено: <b>{total_added}</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

                await asyncio.sleep(0.04)

            logging.info(f"✅ [{source_ch}] Глубокий скан завершён. Добавлено: {added}")

        except Exception as e:
            logging.error(f"Ошибка сканирования {source_ch}: {e}")
            try:
                await status.edit_text(
                    f"⚠️ Ошибка при сканировании <code>{source_ch}</code>: {e}\n"
                    f"Продолжаю...",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # Автоматическая синхронизация и нормализация арок Ван-Пис после скана
    try:
        from fix_onepiece_catalog import fix_catalog
        fix_catalog()
    except Exception as e:
        logging.error(f"Ошибка fix_catalog после сканирования: {e}")

    await status.edit_text(
        f"✅ <b>Сканирование завершено!</b>\n\n"
        f"📡 Сканируемый объект: {label_text}\n"
        f"📥 Найдено и добавлено серий: <b>{total_added}</b>\n\n"
        f"Все доступные серии и арки Ван-Пис успешно обновлены в меню бота!",
        parse_mode="HTML"
    )



@dp.callback_query(F.data == "admin_restart")
async def admin_restart_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    try:
        await callback.answer()
    except Exception:
        pass
    await callback.message.answer("🔄 Перезапускаю бота (внутренний перезапуск)...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@dp.callback_query(F.data == "admin_stop")
async def admin_stop_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    try:
        await callback.answer()
    except Exception:
        pass
    await callback.message.answer("🛑 Бот выключен.")
    os._exit(0)


# =========================
# УПРАВЛЕНИЕ КАТАЛОГОМ
# =========================

@dp.message(Command("catalog"))
async def cmd_catalog(message: Message, command: CommandObject):
    """
    Команды управления каталогом аниме.

    Использование:
      /catalog                       — статистика каталога + список аниме
      /catalog del <anime_key>       — удалить всё аниме целиком
      /catalog del <anime_key> ep <message_id>   — удалить одну серию
      /catalog del <anime_key> dub <название>    — удалить всю озвучку
    """
    if message.from_user.id not in ADMIN_IDS:
        return

    args = command.args.split() if command.args else []

    # ── /catalog (без аргументов) ──────────────────────────────────────────
    if not args:
        stats = db.get_catalog_stats()
        all_anime = db.get_all_dynamic_anime_keys()

        lines = []
        for key, title in all_anime:
            dubs = db.get_dynamic_dubs(key)
            seasons = db.get_dynamic_seasons(key)
            total_eps = sum(len(db.get_dynamic_episodes(key, s)) for s in seasons)
            dubs_str = ", ".join(dubs) if dubs else "—"
            lines.append(f"• <code>{key}</code> | {title} | {total_eps} сер. | {dubs_str}")

        anime_list_text = "\n".join(lines) if lines else "<i>Каталог пуст</i>"

        text = (
            "📚 <b>КАТАЛОГ АНИМЕ</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"🎬 Аниме: <b>{stats['anime']}</b>\n"
            f"🍿 Серий: <b>{stats['episodes']}</b>\n"
            f"🎙 Озвучек: <b>{stats['dubs']}</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"{anime_list_text}\n\n"
            "━━━━━━━━━━━━━━\n"
            "💡 <b>Команды удаления:</b>\n"
            "<code>/catalog del &lt;ключ&gt;</code> — удалить аниме\n"
            "<code>/catalog del &lt;ключ&gt; ep &lt;msg_id&gt;</code> — удалить серию\n"
            "<code>/catalog del &lt;ключ&gt; dub &lt;озвучка&gt;</code> — удалить озвучку\n"
            "<code>/clearcatalog</code> — 🗑 очистить весь каталог"
        )
        await message.answer(text, parse_mode="HTML")
        return

    # ── /catalog del ... ───────────────────────────────────────────────────
    if args[0].lower() == "del":
        if len(args) < 2:
            await message.answer(
                "⚠️ Укажи ключ аниме.\n"
                "Пример: <code>/catalog del jjk</code>",
                parse_mode="HTML"
            )
            return

        anime_key = args[1].lower()

        # /catalog del jjk ep 12345
        if len(args) >= 4 and args[2].lower() == "ep":
            try:
                msg_id = int(args[3])
            except ValueError:
                await message.answer("❌ message_id должен быть числом.", parse_mode="HTML")
                return
            deleted = db.delete_episode(msg_id)
            if deleted:
                await message.answer(
                    f"✅ Серия с ID <code>{msg_id}</code> удалена из каталога.\n"
                    f"Аниме: <code>{anime_key}</code>",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"❌ Серия с ID <code>{msg_id}</code> не найдена в каталоге.",
                    parse_mode="HTML"
                )
            return

        # /catalog del jjk dub Anilibria
        if len(args) >= 4 and args[2].lower() == "dub":
            dubbing = " ".join(args[3:])
            count = db.delete_dubbing(anime_key, dubbing)
            if count > 0:
                await message.answer(
                    f"✅ Удалено <b>{count}</b> серий озвучки «{dubbing}» у аниме <code>{anime_key}</code>.",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"❌ Серии с озвучкой «{dubbing}» для <code>{anime_key}</code> не найдены.",
                    parse_mode="HTML"
                )
            return

        # /catalog del jjk — удалить всё аниме
        # Показываем подтверждение с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"catalog_del_confirm_{anime_key}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="catalog_del_cancel")
            ]
        ])
        # Покажем сколько серий будет удалено
        seasons = db.get_dynamic_seasons(anime_key)
        total_eps = sum(len(db.get_dynamic_episodes(anime_key, s)) for s in seasons)
        dubs = db.get_dynamic_dubs(anime_key)
        await message.answer(
            f"⚠️ <b>Подтверди удаление!</b>\n\n"
            f"Аниме: <code>{anime_key}</code>\n"
            f"Серий: <b>{total_eps}</b>\n"
            f"Озвучки: {', '.join(dubs) if dubs else '—'}\n\n"
            f"Это удалит <b>все серии</b> этого аниме из каталога (кнопки в меню пропадут).",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    await message.answer(
        "❌ Неверная команда. Используй <code>/catalog</code> для справки.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("catalog_del_confirm_"))
async def catalog_del_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    try:
        await callback.answer()
    except Exception:
        pass
    anime_key = callback.data.replace("catalog_del_confirm_", "")
    count = db.delete_anime(anime_key)
    await callback.message.edit_text(
        f"🗑 <b>Удалено!</b>\n\n"
        f"Аниме <code>{anime_key}</code> удалено из каталога.\n"
        f"Серий удалено: <b>{count}</b>\n\n"
        f"Кнопка в меню больше не появится (пока не добавишь снова через канал или /scan).",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "catalog_del_cancel")
async def catalog_del_cancel(callback: CallbackQuery):
    await callback.answer("Отменено")
    await callback.message.edit_text("✅ Удаление отменено.", parse_mode="HTML")


@dp.message(Command("clearcatalog"))
async def cmd_clear_catalog(message: Message):
    """Полная очистка каталога с подтверждением"""
    if message.from_user.id not in ADMIN_IDS:
        return
    stats = db.get_catalog_stats()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Да, очистить всё!", callback_data="clearcatalog_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="clearcatalog_cancel")
        ]
    ])
    await message.answer(
        f"⚠️ <b>ВНИМАНИЕ! Полная очистка каталога</b>\n\n"
        f"Будет удалено:\n"
        f"🎬 Аниме: <b>{stats['anime']}</b>\n"
        f"🍿 Серий: <b>{stats['episodes']}</b>\n"
        f"🎙 Озвучек: <b>{stats['dubs']}</b>\n\n"
        f"После этого меню аниме будет пустым. Используй <code>/scan</code> чтобы заполнить заново.\n\n"
        f"Ты уверен?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "clearcatalog_confirm")
async def clearcatalog_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    try:
        await callback.answer()
    except Exception:
        pass
    count = db.clear_catalog()
    await callback.message.edit_text(
        f"✅ <b>Каталог полностью очищен!</b>\n\n"
        f"Удалено записей: <b>{count}</b>\n\n"
        f"Теперь в меню останутся только аниме из кода (статичные).\n"
        f"Когда начнёшь выкладывать аниме в канал — они автоматически появятся в меню.\n"
        f"Или используй /scan для сканирования канала.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "clearcatalog_cancel")
async def clearcatalog_cancel(callback: CallbackQuery):
    await callback.answer("Отменено")
    await callback.message.edit_text("✅ Очистка отменена. Каталог не изменён.", parse_mode="HTML")

# ==========================================
# УПРАВЛЕНИЕ ХЭШТЕГАМИ АНИМЕ (АДМИН)
# ==========================================

@dp.message(Command("addanime"))
async def cmd_add_anime(message: Message, command: CommandObject):
    """
    Привязать хэштег к ключу аниме.
    Использование: /addanime <hashtag> <anime_key> <title>
    """
    if message.from_user.id not in ADMIN_IDS:
        return

    if not command.args:
        await message.answer(
            "⚠️ <b>Использование команды:</b>\n"
            "<code>/addanime &lt;хештег&gt; &lt;ключ_аниме&gt; &lt;Название&gt;</code>\n\n"
            "Пример:\n"
            "<code>/addanime blackclover black_clover Чёрный клевер</code>",
            parse_mode="HTML"
        )
        return

    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Недостаточно аргументов. Пример: <code>/addanime blackclover black_clover Чёрный клевер</code>", parse_mode="HTML")
        return

    hashtag, anime_key, title = parts
    hashtag = hashtag.lstrip('#').lower().strip()
    anime_key = anime_key.lower().strip()
    title = title.strip()

    db.add_anime_hashtag(hashtag, anime_key, title)
    
    # Обновляем все имеющиеся записи этого аниме в каталоге с новым ключом и красивым названием
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE anime_catalog
        SET anime_key = ?, title = ?
        WHERE anime_key = ? OR title LIKE ?
    """, (anime_key, title, anime_key, f"%{title}%"))
    updated_rows = cursor.rowcount
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ <b>Аниме зарегистрировано!</b>\n\n"
        f"#️⃣ Хэштег: <code>#{hashtag}</code>\n"
        f"🔑 Ключ: <code>{anime_key}</code>\n"
        f"🎬 Название: <b>{title}</b>\n"
        f"🔄 Обновлено строк в БД: <b>{updated_rows}</b>",
        parse_mode="HTML"
    )

@dp.message(Command("listhashtags"))
async def cmd_list_hashtags(message: Message):
    """Показать все зарегистрированные хэштеги"""
    if message.from_user.id not in ADMIN_IDS:
        return
        
    hashtags = db.get_all_anime_hashtags()
    if not hashtags:
        await message.answer("Словарь хэштегов пуст.")
        return
        
    lines = []
    for h, key, title in hashtags:
        lines.append(f"• <code>#{h}</code> → <code>{key}</code> | <b>{title}</b>")
        
    await message.answer("📋 <b>Список зарегистрированных хэштегов:</b>\n\n" + "\n".join(lines), parse_mode="HTML")

@dp.message(Command("delhashtag"))
async def cmd_del_hashtag(message: Message, command: CommandObject):
    """Удалить хэштег из словаря"""
    if message.from_user.id not in ADMIN_IDS:
        return
        
    if not command.args:
        await message.answer("Укажите хэштег для удаления. Пример: <code>/delhashtag blackclover</code>", parse_mode="HTML")
        return
        
    hashtag = command.args.strip().lstrip('#').lower()
    rowcount = db.delete_anime_hashtag(hashtag)
    
    if rowcount > 0:
        await message.answer(f"✅ Хэштег <code>#{hashtag}</code> успешно удален.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Хэштег <code>#{hashtag}</code> не найден.", parse_mode="HTML")




@dp.channel_post()
@dp.edited_channel_post()
async def on_channel_post(message: Message):
    """Обработчик новых и отредактированных постов в канале — автоматически обновляет базу"""
    # Принимаем посты только из каналов-источников аниме
    if message.chat.username:
        chat_username = "@" + message.chat.username.lower()
        allowed = [ch.lower() for ch in ANIME_SOURCE_CHANNELS]
        if chat_username not in allowed:
            return
        current_source = "@" + message.chat.username
    else:
        return  # У канала нет username — пропускаем

    if not message.video and not message.document:
        return

    caption = message.caption or message.text
    if not caption:
        return

    logging.info(f"🆕 Новый пост в {current_source}! Парсим описание: {caption[:80]}...")

    try:
        ep_data = parse_caption_to_episode(caption, message.message_id, source_channel=current_source)
        if ep_data:
            anime_key = ep_data['anime_key']
            
            # Проверяем, является ли это аниме новым (нет в ANIME_DB и нет в БД)
            dynamic_keys = [k[0] for k in db.get_all_dynamic_anime_keys()]
            is_new = (anime_key not in ANIME_DB) and (anime_key not in dynamic_keys)
            
            db.add_dynamic_episode(**ep_data)
            logging.info(f"✅ Добавлено: {ep_data['title']} | {ep_data['season_id']} сезон | {ep_data['episode_num']} серия | {ep_data['quality']} | {ep_data['dubbing']} | источник: {current_source}")
            
            if is_new:
                # Отправляем предупреждение всем админам
                warn_text = (
                    f"⚠️ <b>Обнаружено новое аниме в канале!</b>\n\n"
                    f"📝 Название: <b>{ep_data['title']}</b>\n"
                    f"🔑 Создан ключ: <code>{anime_key}</code>\n"
                    f"🎬 Серия: {ep_data['episode_num']} (сезон {ep_data['season_id']})\n"
                    f"📡 Источник: {current_source}\n\n"
                    f"💡 Если это ошибка или вы хотите привязать его к хэштегу, используйте:\n"
                    f"<code>/addanime &lt;хештег&gt; {anime_key} &lt;Красивое Название&gt;</code>\n"
                    f"<i>Например: /addanime blackclover black_clover Чёрный клевер</i>"
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, warn_text, parse_mode="HTML")
                    except Exception as e:
                        logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        else:
            logging.info(f"⏩ Пост из {current_source} пропущен — не найдено слово 'серия' в описании.")
    except Exception as e:
        logging.error(f"❌ Ошибка автоматического добавления: {e}")


async def cleanup_deleted_messages_loop():
    """Фоновая задача для проверки удаленных и новых сообщений во всех каналах-источниках."""
    await asyncio.sleep(60)  # Даем боту запуститься нормально перед первым циклом
    while True:
        try:
            logging.info("🔄 Запуск фоновой проверки обновлений во всех каналах-источниках...")
            import sqlite3
            conn = sqlite3.connect(db.DB_PATH)
            cursor = conn.cursor()
            
            # Инициализация статистики
            scan_stats = {ch: {'added': 0, 'deleted': 0} for ch in ANIME_SOURCE_CHANNELS}
            scan_stats[CHANNEL_ANIME] = {'added': 0, 'deleted': 0}
            total_added = 0
            
            # --- 1. ПРОВЕРКА НА НОВЫЕ СЕРИИ (по всем каналам) ---
            cursor.execute("SELECT MAX(message_id) FROM anime_catalog")
            max_db_id = cursor.fetchone()[0] or 0
            
            bot_info = await bot.get_me()

            for source_ch in ANIME_SOURCE_CHANNELS:
                try:
                    if source_ch.lower() == CHANNEL_ANIME.lower():
                        try:
                            temp_msg = await bot.send_message(source_ch, "⌛", disable_notification=True)
                            max_channel_id = temp_msg.message_id
                            await bot.delete_message(source_ch, max_channel_id)
                        except Exception as e:
                            logging.warning(f"Не удалось определить max_id для {source_ch}: {e}")
                            continue
                    else:
                        max_channel_id = max_db_id + 200  # смотрим 200 вперёд
                    
                    if max_channel_id > max_db_id:
                        start_id = max(max_db_id + 1, max_channel_id - 100)
                        for mid in range(start_id, max_channel_id + 1):
                            try:
                                fwd = await bot.forward_message(
                                    chat_id=bot_info.id,
                                    from_chat_id=source_ch,
                                    message_id=mid,
                                    disable_notification=True
                                )
                                caption = fwd.caption or fwd.text
                                if caption and (fwd.video or fwd.document):
                                    ep_data = parse_caption_to_episode(caption, mid, source_channel=source_ch)
                                    if ep_data:
                                        db.add_dynamic_episode(**ep_data)
                                        if source_ch not in scan_stats:
                                            scan_stats[source_ch] = {'added': 0, 'deleted': 0}
                                        scan_stats[source_ch]['added'] += 1
                                        total_added += 1
                            except Exception:
                                pass  # Сообщение не существует или не является аниме
                            await asyncio.sleep(1.0)
                            
                except Exception as e:
                    logging.error(f"❌ Ошибка проверки новых сообщений в {source_ch}: {e}")

            # --- 2. ПРОВЕРКА НА УДАЛЕННЫЕ СЕРИИ ---
            try:
                cursor.execute("PRAGMA table_info(anime_catalog)")
                cols = [col[1] for col in cursor.fetchall()]
                if "source_channel" in cols:
                    cursor.execute("SELECT message_id, source_channel FROM anime_catalog")
                    rows = [(row[0], row[1] or CHANNEL_ANIME) for row in cursor.fetchall()]
                else:
                    cursor.execute("SELECT message_id FROM anime_catalog")
                    rows = [(row[0], CHANNEL_ANIME) for row in cursor.fetchall()]
            except Exception:
                cursor.execute("SELECT message_id FROM anime_catalog")
                rows = [(row[0], CHANNEL_ANIME) for row in cursor.fetchall()]

            total_deleted = 0
            for msg_id, src_channel in rows:
                try:
                    await bot.copy_message(
                        chat_id=bot_info.id,
                        from_chat_id=src_channel,
                        message_id=msg_id,
                        disable_notification=True
                    )
                except Exception as e:
                    err_str = str(e).lower()
                    if any(x in err_str for x in [
                        "message to copy not found",
                        "message not found",
                        "invalid message",
                        "message_id_invalid",
                        "chat not found",
                        "message to forward not found"
                    ]):
                        db.delete_episode(msg_id)
                        if src_channel not in scan_stats:
                            scan_stats[src_channel] = {'added': 0, 'deleted': 0}
                        scan_stats[src_channel]['deleted'] += 1
                        total_deleted += 1

                await asyncio.sleep(0.5)

            # Отправка отчета, если были изменения
            if total_added > 0 or total_deleted > 0:
                cursor.execute("SELECT COUNT(*) FROM anime_catalog")
                total_anime_eps = cursor.fetchone()[0] or 0
                
                report_lines = ["📊 <b>Отчёт о сканировании базы:</b>\n"]
                for ch, stat in scan_stats.items():
                    if stat['added'] > 0 or stat['deleted'] > 0:
                        report_lines.append(f"📡 <b>{ch}</b>\n  ➕ Добавлено: {stat['added']}\n  🗑 Удалено: {stat['deleted']}")
                
                report_lines.append(f"\n📂 Всего серий в базе: <b>{total_anime_eps}</b>")
                report_text = "\n".join(report_lines)
                
                logging.info(report_text.replace("<b>", "").replace("</b>", ""))
                
                if LOG_GROUP_ID:
                    try:
                        await bot.send_message(LOG_GROUP_ID, report_text, parse_mode="HTML")
                    except Exception as e:
                        logging.error(f"Не удалось отправить отчет в группу {LOG_GROUP_ID}: {e}")

            conn.close()

        except Exception as e:
            logging.error(f"❌ Ошибка в фоновом цикле проверки сообщений: {e}")

        await asyncio.sleep(21600)  # Проверка каждые 6 часов (не нагружаем API)



# =========================
# ЗАПУСК
# =========================
# =========================
# ПОИСК АНИМЕ (Текст и Inline)
# =========================

@dp.message(F.text & ~F.text.startswith('/'))
async def text_search_handler(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer("❌ Доступ ограничен! Пожалуйста, подпишитесь на канал.")
        return

    query = message.text.lower().strip()
    if len(query) < 2:
        await message.answer("⚠️ Введите хотя бы 2 буквы для поиска.")
        return

    results = []

    # Ищем в статике
    for anime_id, info in ANIME_DB.items():
        title = info['title'].lower()
        if query in title or anime_id.lower() in query:
            results.append((anime_id, info['title']))

    # Ищем в динамике
    dynamic_keys = db.get_all_dynamic_anime_keys()
    for anime_key, title in dynamic_keys:
        if query in title.lower() or query in anime_key.lower():
            if not any(r[0] == anime_key for r in results):
                results.append((anime_key, f"🎬 {title}"))

    if not results:
        await message.answer(f"🔍 По запросу <b>{message.text}</b> ничего не найдено.\nПопробуй написать название иначе.", parse_mode="HTML")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for anime_id, title in results[:20]:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=title, callback_data=f"anime_{anime_id}")])

    await message.answer(f"🔍 <b>Результаты поиска:</b>\nНайдено совпадений: {len(results)}", reply_markup=keyboard, parse_mode="HTML")

@dp.inline_query()
async def inline_search_handler(inline_query: InlineQuery):
    query = inline_query.query.lower().strip()

    all_anime = []
    for anime_id, info in ANIME_DB.items():
        all_anime.append((anime_id, info['title']))

    dynamic_keys = db.get_all_dynamic_anime_keys()
    for anime_key, title in dynamic_keys:
        if not any(a[0] == anime_key for a in all_anime):
            all_anime.append((anime_key, f"🎬 {title}"))

    filtered = []
    if query:
        for anime_id, title in all_anime:
            if query in title.lower() or query in anime_id.lower():
                filtered.append((anime_id, title))
    else:
        filtered = all_anime[:20]

    results = []
    me = await bot.me()
    for i, (anime_id, title) in enumerate(filtered[:50]):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="▶️ Смотреть аниме", url=f"https://t.me/{me.username}")
        ]])

        results.append(
            InlineQueryResultArticle(
                id=f"search_{anime_id}_{i}",
                title=title,
                description="Нажми, чтобы отправить",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎬 <b>{title}</b>\n\nСмотри это аниме в нашем боте: @{me.username}",
                    parse_mode="HTML"
                ),
                reply_markup=kb
            )
        )

    await inline_query.answer(results, cache_time=10, is_personal=True)

async def main():
    db.init_db()
    logging.info("🚀 Бот запущен!")
    
    try:
        import audit
        audit.register_audit_handlers(dp, ADMIN_IDS)
    except Exception as e:
        logging.error(f"Failed to load audit handlers: {e}")

    # Фоновая очистка удалённых постов
    asyncio.create_task(cleanup_deleted_messages_loop())

    # Установка команд бота
    try:
        commands = [
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="menu", description="📋 Основное меню"),
            BotCommand(command="admin", description="👑 Администрация")
        ]
        await bot.set_my_commands(commands)
        logging.info("✅ Команды меню успешно обновлены!")
    except Exception as e:
        logging.error(f"⚠️ Ошибка обновления команд: {e}")

    # Удаляем вебхуки и старые обновления для чистого запуска
    await bot.delete_webhook(drop_pending_updates=True)

    # Уведомляем админов о запуске
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 <b>Бот успешно запущен и готов к работе!</b>", parse_mode="HTML")
        except Exception:
            pass

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"⚠️ Ошибка поллинга: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")