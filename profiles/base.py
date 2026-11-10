"""
Общее для профилей товаров: нормализация текста объявлений.

Профиль - модуль в пакете profiles с функциями:
    prefilter(title: str, price: int | None) -> bool   - стоит ли заходить в карточку
    extract(title, description, params) -> dict         - характеристики товара
    tier(specs: dict) -> str                            - "A" / "B" / "X" (мимо) / "?" (не понять)
    group_key(specs: dict) -> str | None                - ключ группы для медианы цены
"""
import re

# Продавцы мешают латиницу с кириллицей («Пpoдaю»), чтобы обходить фильтры Авито.
# Латинские двойники приводим к кириллице только внутри слов, где есть кириллица:
# «MacBook» и «M5 Pro» трогать нельзя.
_LAT_TWINS = "aceopxyACEHKMOPTXB"
_CYR_TWINS = "асеорхуАСЕНКМОРТХВ"
assert _LAT_TWINS.isascii() and len(_LAT_TWINS) == len(_CYR_TWINS)
_LAT2CYR = str.maketrans(_LAT_TWINS, _CYR_TWINS)
_CYR2LAT = str.maketrans(_CYR_TWINS, _LAT_TWINS)
_CYR = re.compile(r"[а-яё]", re.I)
_LAT = re.compile(r"[a-z]", re.I)
_WORD = re.compile(r"\w+", re.U)


def _fix_word(m: re.Match) -> str:
    w = m.group(0)
    has_cyr, has_lat = bool(_CYR.search(w)), bool(_LAT.search(w))
    if has_cyr and has_lat:
        # больше кириллицы - слово русское, иначе латинское («MacВook» с кириллической В)
        cyr = len(_CYR.findall(w))
        lat = len(_LAT.findall(w))
        return w.translate(_LAT2CYR) if cyr >= lat else w.translate(_CYR2LAT)
    return w


def normalize(text: str) -> str:
    """Чинит смешанную раскладку внутри слов, схлопывает пробелы."""
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = _WORD.sub(_fix_word, text)
    return re.sub(r"\s+", " ", text).strip()


def is_obfuscated(text: str) -> bool:
    """В тексте есть слова со смешанной раскладкой - признак обхода фильтров Авито."""
    return any(_CYR.search(w) and _LAT.search(w) for w in _WORD.findall(text or ""))
