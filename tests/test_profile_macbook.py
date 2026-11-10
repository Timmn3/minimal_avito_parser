"""Профиль MacBook Pro 14 на реальных заголовках из выдачи Авито (10.11.2026)."""
import pytest

from profiles import macbook_pro_14 as p
from profiles.base import is_obfuscated, normalize

CASES = [
    ("MacBook Pro 14 M6 12/12 32/1TB Black", "A", "M6", 32, 1024),
    ("Macbook pro 14 M4 16/512 (91%)", "X", "M4", 16, 512),
    ("Macbook Pro 14 M3 8 гб 1 тб", "X", "M3", 8, 1024),
    ('Apple MacBook Pro M3 14" 36/512, новый', "X", "M3", 36, 512),
    ("Macbook Pro 14 m5 24/1tb (4 цикла, как новый)", "A", "M5", 24, 1024),
    ('Apple MacBook Pro M4 14" 24/512, идеал', "B", "M4", 24, 512),
    ("MacBook Pro 14 2023 M2 Max 32Gb 1Tb Silver", "X", "M2 Max", 32, 1024),
    ("MacBook Pro 14 M5 24gb 1tb", "A", "M5", 24, 1024),
    ("Macbook pro 14 M5 16GB 1TB Space Black", "B", "M5", 16, 1024),
    ("MacBook Pro 14 2025 M5 24/512 black 10c 10g", "B", "M5", 24, 512),
    ("Macbook Pro 14 m5 16/1TB (7 часов использования)", "B", "M5", 16, 1024),
    ("MacBook Pro 14 M5 24GB 1TB Silver 9 циклов новый", "A", "M5", 24, 1024),
    ("Apple macbook pro 14 M4 Pro 1 tb (14 cpu / 20 GPU)", "A", "M4 Pro", None, 1024),
    ("Macbook pro 14 m1pro 16 1tb", "X", "M1 Pro", None, None),
    ("Ноутбук Lenovo Thinkpad T14 Ryzen 5 PRO, 16/512", "X", None, None, None),
    ("MacBook Pro 14 M5 Pro 24/1TB", "A", "M5 Pro", 24, 1024),
    ("MacBook Air 13 M4 16/512", "X", "M4", 16, 512),
    ("Macbook Pro 14 M3 Max 36/1tb", "B", "M3 Max", 36, 1024),
    ("Макбук про 14 м4 про 24 512", "B", "M4 Pro", 24, 512),
    ("MacBook Pro 14 M4 Pro", "?", "M4 Pro", None, None),
    ("Macbook pro 14 M5 24512 black", "B", "M5", 24, 512),
    ("MacBook Pro 14 M5 161tb", "B", "M5", 16, 1024),
    ("MacBook Pro 16 M4 Max 36GB 1TB", "X", "M4 Max", None, None),
]


@pytest.mark.parametrize("title,tier,chip,ram,ssd", CASES)
def test_title(title, tier, chip, ram, ssd):
    s = p.extract(title)
    assert p.tier(s) == tier
    assert s["chip"] == chip
    if ram is not None:
        assert s["ram"] == ram
    if ssd is not None:
        assert s["ssd"] == ssd


def test_prefilter_skips_junk_and_needs_price():
    assert p.prefilter("MacBook Pro 14 M5 24/1tb", 150000)
    assert p.prefilter("MacBook Pro 14 M4 Pro", 150000)  # непонятно - заходим в карточку
    assert not p.prefilter("Macbook pro 14 M4 16/512", 150000)
    assert not p.prefilter("MacBook Pro 14 M5 24/1tb", None)


def test_description_fills_gaps_and_params():
    params = {"Состояние": "Отличное", "Экран": "Белые пятна", "Корпус": "Без дефектов",
              "Циклов перезарядки": "5", "Клавиатура": "Есть кириллица", "Комплект": "Зарядное устройство"}
    s = p.extract("MacBook Pro 14 M4 Pro", "Память 24 гб, ssd 1 тб", params)
    assert (s["ram"], s["ssd"]) == (24, 1024)
    assert s["cycles"] == 5 and s["cyrillic"] is True
    assert s["defects"] == ["Экран: Белые пятна"]
    assert p.tier(s) == "A"


def test_group_key():
    assert p.group_key(p.extract("MacBook Pro 14 M5 24/1tb")) == "M5 / 24 / 1TB"
    assert p.group_key(p.extract("MacBook Pro 14 M4 Pro 1tb")) == "M4 Pro / 24 / 1TB"
    assert p.group_key(p.extract("MacBook Pro 14 M5")) is None


def test_normalize_homoglyphs():
    assert normalize("Пpoдaю cвой мак") == "Продаю свой мак"
    assert normalize("MacВook Pro") == "MacBook Pro"
    assert is_obfuscated("Пpoдaю") and not is_obfuscated("Продаю MacBook")


def test_focus_group_goes_first_in_queue():
    focus = p.extract("MacBook Pro 14 M4 Pro 24/512")
    assert p.tier(focus) == "B" and p.priority(focus) == -1
    assert p.priority(p.extract("MacBook Pro 14 M5 24/1tb")) == 0 < p.priority(p.extract("MacBook Pro 14 M4 24/512"))
    # без указания памяти: у M4 Pro минимум 24 ГБ, группа та же
    assert p.priority(p.extract("MacBook Pro 14 M4 Pro 512gb")) == -1
    assert p.priority(p.extract("MacBook Pro 14 M4 Pro 24/1tb")) == 0  # 1 ТБ - уже A, не фокус
