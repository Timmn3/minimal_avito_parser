"""
Разбор описания объявления по правилам (универсально, для любого товара).

Что ищем: торг (самое интересное для покупателя), срочность, гарантию и документы, «новый/не вскрывался»,
причину продажи, а из плохого - следы ремонта, блокировки и признаки неисправности, наценку за безнал.
Каждая находка идёт с коротким фрагментом текста: решает человек, правила только подсвечивают.
"""
import re
from typing import Optional

from profiles.base import normalize

_NEG_BEFORE = re.compile(r"(?:\bне|\bни|\bбез|\bнет|никогда|ни разу|не было)\W+(?:\w+\W+){0,2}$")


def _prep(text: str) -> str:
    return normalize(text or "").lower().replace("ё", "е")


def _snippet(t: str, start: int, end: int, pad: int = 45) -> str:
    return t[max(0, start - pad):end + pad].replace("\n", " ").strip()


def _negated(t: str, start: int) -> bool:
    """Перед совпадением стоит отрицание («не вскрывался», «без ремонта»)."""
    return bool(_NEG_BEFORE.search(t[max(0, start - 28):start]))


_BARGAIN = re.compile(r"\bторг(?!ов)\w*|уступ(?:лю|им|ка)\b|сброшу|скину|цена не окончательн\w*")
_NO_BARGAIN_AFTER = re.compile(r"^\W*(?:нет|не\b|исключен\w*|не будет)")
_URGENT = re.compile(r"срочн\w+|быстр\w+ продаж\w+|уезжаю|переезд\w*|нужны деньги")
_WARRANTY = re.compile(r"гаранти\w+")
_WARRANTY_OFFICIAL = re.compile(r"официальн\w+ гаранти\w+|гаранти\w+ (?:apple|эппл)|гаранти\w+[^.]{0,20}\d+\s*(?:мес|год|лет)")
_DOCS = re.compile(r"\bчек\w*|кассов\w+ чек|ростест|\bеас\b|документ\w+|коробк\w+")
_SEALED = re.compile(r"запечатан\w*|нераспечатан\w*|не вскрыва\w+|не использовал\w*|новый|как новый|в идеале")
_REASON = re.compile(r"(?:продаю|продам|продается)[^.!\n]{0,40}?(?:так как|потому что|в связи с|ввиду)\s+([^.!\n]{4,80})"
                     r"|(перешел на [^.!\n]{3,30})|(купил (?:новый|другой)[^.!\n]{0,30})|(не подош\w+[^.!\n]{0,30})")

_REPAIR = re.compile(
    r"(?:был|после|делал\w*)\s+ремонт\w*|ремонтирова\w+|"
    r"(?:менял\w*|замен\w+|заменен\w+)\s+(?:экран|матриц\w+|батаре\w+|аккумулятор\w*|плат\w*|клавиатур\w*|топкейс\w*|корпус)|"
    r"вскрыва\w+|\bвскрыт\w*|залит\w*|заливал\w*|реболл\w*|паял\w*")
_BROKEN = re.compile(
    r"заблокирован\w*|привязан\w* к (?:icloud|apple)|\bmdm\b|activation lock|на запчасти|не включа\w+|"
    r"нерабоч\w+|не заряжа\w+|без аккумулятор\w+|не работа(?:ет|ют)")
# наценка за безнал: «Перевод по СБП/QR - +13 % к цене», «Картой через терминал - +15 %»
_SURCHARGE = re.compile(r"(?:карт\w*|сбп|\bqr\b|безнал\w*|перевод\w*|терминал\w*|кредит\w*|рассрочк\w*)"
                        r"[^.]{0,60}?\+\s*(\d{1,2})\s*%")


def analyze(text: Optional[str]) -> dict:
    """
    Возвращает:
      bargain: 'yes' | 'no' | None, bargain_note - фрагмент про торг;
      urgent, warranty, warranty_official, docs, sealed - bool;
      reason - причина продажи (фрагмент) или None;
      repair, broken - списки фрагментов (плохие признаки);
      surcharge_pct - минимальная наценка за безналичную оплату в процентах или None.
    """
    t = _prep(text)
    out = {"bargain": None, "bargain_note": None, "urgent": False, "warranty": False, "warranty_official": False,
           "docs": False, "sealed": False, "reason": None, "repair": [], "broken": [], "surcharge_pct": None}
    if not t:
        return out

    for m in _BARGAIN.finditer(t):
        no = _negated(t, m.start()) or bool(_NO_BARGAIN_AFTER.match(t[m.end():m.end() + 25]))
        out["bargain"] = "no" if no else "yes"
        out["bargain_note"] = _snippet(t, m.start(), m.end())
        if not no:
            break  # «торг возможен» важнее «торга по телефону нет»: берём положительный
    out["urgent"] = bool(_URGENT.search(t))
    out["warranty"] = bool(_WARRANTY.search(t))
    out["warranty_official"] = bool(_WARRANTY_OFFICIAL.search(t))
    out["docs"] = bool(_DOCS.search(t))
    out["sealed"] = any(not _negated(t, m.start()) or m.group(0).startswith("не ") for m in _SEALED.finditer(t))
    r = _REASON.search(t)
    if r:
        out["reason"] = next(g for g in r.groups() if g).strip()
    for m in _REPAIR.finditer(t):
        if not _negated(t, m.start()):
            out["repair"].append(_snippet(t, m.start(), m.end(), 30))
    for m in _BROKEN.finditer(t):
        if not _negated(t, m.start()):
            out["broken"].append(_snippet(t, m.start(), m.end(), 30))
    pcts = [int(m.group(1)) for m in _SURCHARGE.finditer(t)]
    out["surcharge_pct"] = min(pcts) if pcts else None
    return out
