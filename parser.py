
import re


def parse_caption(caption: str):
    if not caption:
        return None

    result = {
        "title": None,
        "season": None,
        "arc": None,
        "episode": None,
        "quality": None,
        "dubbing": None
    }

    lines = [i.strip() for i in caption.split("\n") if i.strip()]

    # ---------- Название ----------
    for line in lines:
        if (
            not line.startswith("#")
            and ":" not in line
            and "серия" not in line.lower()
            and "сезон" not in line.lower()
            and "качество" not in line.lower()
            and "озвучка" not in line.lower()
            and "арка" not in line.lower()
        ):
            result["title"] = line
            break

    text = caption.lower()

    # ---------- Серия ----------
    ep = re.search(r"(серия|эпизод|episode|ep)\s*[: ]*\s*(\d+)", text)
    if ep:
        result["episode"] = int(ep.group(2))

    # ---------- Сезон ----------
    season = re.search(r"(\d+)\s*сезон", text)
    if season:
        result["season"] = int(season.group(1))

    # ---------- Арка ----------
    arc = re.search(r"арка\s*[:\-]?\s*(.+)", caption, re.IGNORECASE)
    if arc:
        result["arc"] = arc.group(1).split("\n")[0].strip()

    # ---------- Качество ----------
    quality = re.search(r"(360p|480p|720p|1080p|1440p|2160p|2k|4k)", text)
    if quality:
        result["quality"] = quality.group(1).upper()

    # ---------- Озвучка ----------
    dub = re.search(r"озвучка\s*[:\-]?\s*(.+)", caption, re.IGNORECASE)
    if dub:
        result["dubbing"] = dub.group(1).split("\n")[0].strip()

    return result