"""Скоринг research: флаги, решение «слать ли», текст уведомления."""
from database.models import Listing
from profiles import macbook_pro_14 as p
from services.research_scoring import evaluate, format_message, worth_notifying

GOOD_SELLER = {"rating": 4.9, "reviews": 30, "reliable": True}
GOOD_PARAMS = {"Состояние": "Отличное", "Экран": "Без дефектов", "Корпус": "Без дефектов",
               "Циклов перезарядки": "40", "Клавиатура": "Есть кириллица", "Комплект": "Зарядное устройство, Коробка"}
MEDIANS = {"M5 / 24 / 1TB": (160000, 12), "M5 / 16 / 1TB": (135000, 20)}


def row(title, price, status="ok", params=GOOD_PARAMS, seller=GOOD_SELLER, desc="Продаю, всё работает",
        location="Москва"):
    return Listing(title=title, price=price, detail_status=status, params=params, seller=seller,
                   description=desc, location=location, url="https://www.avito.ru/x_1")


def test_good_a_below_median_is_sent():
    r = row("MacBook Pro 14 M5 24/1TB", 150000)
    ev = evaluate(r, p, MEDIANS)
    assert ev["tier"] == "A" and ev["flags"] == [] and round(ev["ratio"], 2) == 0.94
    assert worth_notifying(r, ev)
    assert "кириллица" in ev["pluses"] and "коробка" in ev["pluses"] and "Москва" in ev["pluses"]


def test_a_above_median_not_sent():
    r = row("MacBook Pro 14 M5 24/1TB", 175000)
    assert not worth_notifying(r, evaluate(r, p, MEDIANS))


def test_b_needs_real_discount():
    r = row("MacBook Pro 14 M5 16/1TB", 130000)  # 96% медианы - мало
    assert not worth_notifying(r, evaluate(r, p, MEDIANS))
    r = row("MacBook Pro 14 M5 16/1TB", 120000)  # 89%
    assert worth_notifying(r, evaluate(r, p, MEDIANS))


def test_red_flags_block():
    cases = [
        row("MacBook Pro 14 M5 24/1TB", 110000),  # 69% медианы
        row("MacBook Pro 14 M5 24/1TB", 150000, params=dict(GOOD_PARAMS, Экран="Белые пятна")),
        row("MacBook Pro 14 M5 24/1TB", 150000, desc="Только предоплата, отправлю СДЭК"),
        row("MacBook Pro 14 M5 24/1TB", 150000, seller={"reviews": 0}),
        row("MacBook Pro 14 M5 24/1TB", 150000, params=dict(GOOD_PARAMS, Состояние="Удовлетворительное")),
    ]
    for r in cases:
        ev = evaluate(r, p, MEDIANS)
        assert ev["flags"] and not worth_notifying(r, ev), r.title


def test_chip_mismatch_title_vs_description():
    r = row("MacBook Pro 14 M5 24/1TB", 150000, desc="МacBооk Pro 14 2024 М4 24Gb/1Тb новый")
    ev = evaluate(r, p, MEDIANS)
    assert any("чип в заголовке M5" in f for f in ev["flags"]) and not worth_notifying(r, ev)
    # честное упоминание прежнего ноутбука рядом с тем же чипом - не флаг
    ok = row("MacBook Pro 14 M5 24/1TB", 150000, desc="Продаю M5, раньше был M4, обновился")
    assert evaluate(ok, p, MEDIANS)["flags"] == []
    # M4 Pro в заголовке и «M4» в описании - то же поколение
    pro = row("MacBook Pro 14 M4 Pro 24/1TB", 150000, desc="Чип M4, 14 ядер")
    assert evaluate(pro, p, {"M4 Pro / 24 / 1TB": (160000, 9)})["flags"] == []


def test_without_card_not_sent():
    r = row("MacBook Pro 14 M5 24/1TB", 150000, status="pending")
    assert not worth_notifying(r, evaluate(r, p, MEDIANS))


def test_message_escapes_html():
    r = row("MacBook Pro 14 M5 24/1TB <новый>", 150000)
    text = format_message(r, evaluate(r, p, MEDIANS), "MacBook Pro 14")
    assert "&lt;новый&gt;" in text and "150 000 ₽" in text and "M5 / 24 ГБ / 1 ТБ" in text
    drop = format_message(r, evaluate(r, p, MEDIANS), "MacBook Pro 14", old_price=160000)
    assert drop.startswith("📉 Цена снижена: 160 000 → 150 000 ₽")


def test_seller_identity_ignores_drifting_fields_for_shops():
    from database.research_db import _seller_id
    a = {"name": "ЕКБ Электроника", "label": "Компания", "rating": 4.9, "reviews": 9715, "since": 2014, "ads": 480}
    b = dict(a, since=None, ads=None, reviews=9716)
    assert _seller_id(a) == _seller_id(b)
    assert _seller_id(a) != _seller_id(dict(a, name="Другой магазин"))
    # безымянные «Пользователь» - разные люди, если рейтинг/отзывы не совпали
    u1 = {"name": "Пользователь", "label": "Частное лицо", "rating": 5.0, "reviews": 10, "since": None}
    assert _seller_id(u1) != _seller_id(dict(u1, reviews=3))
    assert _seller_id(u1) == _seller_id(dict(u1))
