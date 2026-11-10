"""
Профиль MacBook Pro 14" под задачи Мишани (согласован 10.11.2026): Python/бэкенд, пара контейнеров,
2 внешних монитора, срок 6+ лет, локальные LLM в будущем, важна автономность.

A - цель: M4 Pro / M5 / M5 Pro / M6 с 24+ ГБ и 1+ ТБ.
B - только при цене заметно ниже медианы: те же чипы 24/512, M4/M5/M6 16/1TB, M4 24+, M3 Max 36+.
X - мимо: M1, M2, M3 / M3 Pro, M4 Max, M5 Max, 16/512, не MacBook Pro.
"""
import re
from typing import Optional

from profiles.base import normalize

NAME = "macbook_pro_14"
TITLE = "MacBook Pro 14"

RAM_SIZES = {8, 16, 18, 24, 32, 36, 48, 64, 96, 128}
# минимальная память у чипа: если продавец её не написал, для тира берём минимум
CHIP_MIN_RAM = {"M3 Pro": 18, "M3 Max": 36, "M4": 16, "M4 Pro": 24, "M4 Max": 36,
                "M5": 16, "M5 Pro": 24, "M5 Max": 36, "M6": 16}
GOOD_CHIPS = {"M4 Pro", "M5", "M5 Pro", "M6"}
SKIP_CHIPS = {"M1", "M1 Pro", "M1 Max", "M2", "M2 Pro", "M2 Max", "M3", "M3 Pro", "M4 Max", "M5 Max"}

_CHIP = re.compile(r"\b[mм]\s?([1-9])(?:\s?(pro|max|про|макс))?\b", re.I)
_CHIP_SUFFIX = {"pro": "Pro", "про": "Pro", "max": "Max", "макс": "Max"}
_SLASH = re.compile(r"\b(\d{1,3})(?:\s?[/\\|]\s?|\s)(\d{1,4})\s?(tb|тб|gb|гб|g|t)?\b", re.I)
_GLUED = re.compile(r"\b(8|16|18|24|32|36|48|64)(256|512|1024|2048|1|2|4)\s?(tb|тб|gb|гб)?\b", re.I)
_RAM = re.compile(r"\b(\d{1,3})\s?(?:gb|гб|g)\b(?!\s?(?:ssd|ссд))", re.I)
_RAM_WORD = re.compile(r"(?:ram|озу|памят\w*|unified)\D{0,12}(\d{1,3})", re.I)
_SSD_TB = re.compile(r"\b([1248])\s?(?:tb|тб|t)\b", re.I)
_SSD_GB = re.compile(r"\b(256|512|1024|2048)\s?(?:gb|гб|g)?\b", re.I)
_CPU = re.compile(r"\b(1[0-8]|[89])\s?(?:cpu|c|core|ядер\w*)\b", re.I)
_GPU = re.compile(r"\b([1-4]\d|[89])\s?(?:gpu|g)\b", re.I)


def _chip(text: str) -> Optional[str]:
    m = _CHIP.search(text)
    if not m:
        return None
    return f"M{m.group(1)}" + (f" {_CHIP_SUFFIX[m.group(2).lower()]}" if m.group(2) else "")


def _ssd_value(num: int, unit: str) -> Optional[int]:
    """ГБ накопителя из пары «число + единица»; None, если это не похоже на SSD."""
    unit = (unit or "").lower()
    if unit in ("tb", "тб", "t") or (not unit and num in (1, 2, 4, 8)):
        return num * 1024 if num in (1, 2, 4, 8) else None
    return num if num in (256, 512, 1024, 2048, 4096) else None


def _ram_ssd(text: str) -> tuple[Optional[int], Optional[int]]:
    ram = ssd = None
    for m in _SLASH.finditer(text):  # «24/1tb», «16/512», «36/512gb»
        a, b, unit = int(m.group(1)), int(m.group(2)), m.group(3)
        s = _ssd_value(b, unit)
        if a in RAM_SIZES and s:
            return a, s
    m = _GLUED.search(text)  # «24512», «161tb»
    if m:
        s = _ssd_value(int(m.group(2)), m.group(3))
        if s:
            return int(m.group(1)), s
    m = _SSD_TB.search(text)
    if m:
        ssd = int(m.group(1)) * 1024
    else:
        m = _SSD_GB.search(text)
        if m:
            ssd = int(m.group(1))
    for rx in (_RAM, _RAM_WORD):
        for m in rx.finditer(text):
            v = int(m.group(1))
            if v in RAM_SIZES and v != ssd:
                ram = v
                break
        if ram:
            break
    return ram, ssd


def is_macbook_pro(title: str) -> bool:
    t = normalize(title).lower()
    if "air" in t or "эйр" in t:
        return False
    if re.search(r"\bpro\s?16\b|\b16[\"”']|\b16\s?(?:дюйм|inch)", t):
        return False
    if not re.search(r"macbook|макбук|\bmbp\b", t):
        return False
    return bool(re.search(r"macbook\s?pro|макбук\s?про|\bmbp\b|\bpro\b", t))


def extract(title: str, description: str = "", params: Optional[dict] = None) -> dict:
    """Характеристики: сначала заголовок, недостающее - из описания."""
    t, d = normalize(title), normalize(description)
    chip = _chip(t) or _chip(d)
    ram, ssd = _ram_ssd(t)
    if ram is None or ssd is None:
        ram_d, ssd_d = _ram_ssd(d)
        ram, ssd = ram or ram_d, ssd or ssd_d
    cpu = _CPU.search(t) or _CPU.search(d)
    gpu = _GPU.search(t) or _GPU.search(d)
    specs = {
        "chip": chip,
        "ram": ram,
        "ssd": ssd,
        "cpu": int(cpu.group(1)) if cpu else None,
        "gpu": int(gpu.group(1)) if gpu else None,
        "is_mbp14": is_macbook_pro(title),
        # поколения чипов, упомянутые в описании: расхождение с заголовком - частый признак подмены
        "desc_chips": sorted({f"M{m.group(1)}" for m in _CHIP.finditer(d)}),
    }
    if params:
        specs["condition"] = params.get("Состояние")
        specs["cycles"] = _int(params.get("Циклов перезарядки"))
        specs["cyrillic"] = _cyrillic(params.get("Клавиатура"))
        specs["kit"] = params.get("Комплект")
        defects = [f"{k}: {v}" for k, v in params.items()
                   if k in ("Экран", "Корпус", "Состояние клавиатуры") and v and v != "Без дефектов"]
        specs["defects"] = defects
    return specs


def _int(v) -> Optional[int]:
    try:
        return int(str(v).replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _cyrillic(v) -> Optional[bool]:
    if not v:
        return None
    v = v.lower()
    return False if "нет" in v else True if "есть" in v else None


def tier(specs: dict) -> str:
    chip = specs.get("chip")
    if specs.get("is_mbp14") is False:
        return "X"
    if not chip:
        return "?"
    if chip in SKIP_CHIPS and not (chip == "M3 Pro" and (specs.get("ram") or 0) >= 36):
        return "X"
    ram = specs.get("ram") or CHIP_MIN_RAM.get(chip)
    ssd = specs.get("ssd")
    if chip == "M3 Max" or (chip == "M3 Pro" and ram >= 36):
        return "B" if ram >= 36 else "X"
    if chip not in GOOD_CHIPS and chip != "M4":
        return "?"  # незнакомый чип (M7 и т.п.) - смотрит человек
    if ssd is None or ram is None:
        return "?"
    if chip in GOOD_CHIPS and ram >= 24 and ssd >= 1024:
        return "A"
    if ram >= 24 and ssd >= 512:
        return "B"
    if ram >= 16 and ssd >= 1024:
        return "B"
    return "X"


def group_key(specs: dict) -> Optional[str]:
    chip, ssd = specs.get("chip"), specs.get("ssd")
    ram = specs.get("ram") or (CHIP_MIN_RAM.get(chip) if chip in ("M4 Pro", "M5 Pro") else None)
    if not (chip and ram and ssd):
        return None
    return f"{chip} / {ram} / {ssd // 1024}TB" if ssd >= 1024 else f"{chip} / {ram} / {ssd}"


def prefilter(title: str, price: Optional[int]) -> bool:
    """Заходить ли в карточку: не тратим запросы на заведомо чужое по заголовку."""
    if not price:
        return False
    return tier(extract(title)) != "X"


def priority(specs: dict) -> int:
    """Порядок очереди карточек: сначала вероятные цели, потом непонятные, потом B."""
    return {"A": 0, "?": 1, "B": 2}.get(tier(specs), 3)
