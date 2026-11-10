"""
Разбор ленты и карточек на сохранённых страницах Авито (10.11.2026).
HTML лежит в tmp/fixtures (не в git: там имена продавцов); без него тесты пропускаются.
"""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from parsing.research import parse_card, parse_list_page
from profiles import macbook_pro_14 as p

FIX = Path(__file__).resolve().parent.parent / "tmp" / "fixtures"


def soup(name: str) -> BeautifulSoup:
    path = FIX / name
    if not path.exists():
        pytest.skip(f"нет {path}")
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_list_page():
    items = parse_list_page(soup("list_p1.html"))
    assert len(items) == 50
    for it in items:
        assert it["item_id"].isdigit()
        assert it["url"].startswith("https://www.avito.ru/") and "?" not in it["url"]
        assert it["title"]
        assert it["price"] is None or 100000 <= it["price"] <= 200000
    assert sum(1 for it in items if it["location"]) > 25


def test_card_full():
    c = parse_card(soup("8503767714.html"))
    assert c["title"] == "Macbook pro 14 M5 16GB 1TB Space Black"
    assert c["price"] == 134990
    assert c["params"]["Циклов перезарядки"] == "2"
    assert c["params"]["Клавиатура"] == "Нет кириллицы"
    assert c["seller"]["rating"] == 4.9 and c["seller"]["reviews"] == 1054
    assert c["seller"]["since"] == 2021 and c["seller"]["reliable"] and c["seller"]["verified"]
    assert c["views"] == 70 and c["posted"].startswith("5 ноября")
    assert not c["closed"]
    s = p.extract(c["title"], c["description"], c["params"])
    assert p.tier(s) == "B" and s["cyrillic"] is False and s["cycles"] == 2


def test_card_defects_flagged():
    c = parse_card(soup("8314557382.html"))
    s = p.extract(c["title"], c["description"], c["params"])
    assert s["condition"] == "Удовлетворительное"
    assert any(d.startswith("Экран") for d in s["defects"]) and any(d.startswith("Корпус") for d in s["defects"])


def test_card_without_params_block():
    c = parse_card(soup("7261084110.html"))  # заглушка поверх карточки: цена и продавец есть
    assert c["price"] == 155000
    assert c["seller"]["reviews"] == 10


def test_hard_block_page_is_none():
    assert parse_card(soup("8447187352.html")) is None
