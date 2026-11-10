"""Разбор описаний по правилам: торг, срочность, документы, ремонт, наценка за безнал."""
from profiles.description import analyze

SHOP = ("МacBооk Pro 14 2024 М4 24Gb/1Тb (Sраcе Blасk) Baши выгoды: Tрeйд‑ин: cпeциaльнaя цена при oбмeне. "
        "Крeдит до 3 лeт бeз пеpвoнaчaльнoго взносa. 100 % oригинал: новый, зaпечатанный, официальная гарантия — 12 месяцев. "
        "Оплата: Наличные (самовывоз/доставка) — без процентов. Перевод по СБП/QR — +13 % к цене. "
        "Картой через терминал — +15 % к цене.")


def test_shop_description_surcharge_and_warranty():
    a = analyze(SHOP)
    assert a["surcharge_pct"] == 13
    assert a["warranty"] and a["warranty_official"] and a["sealed"]


def test_bargain_yes_with_snippet():
    a = analyze("Состояние идеальное. Торг уместен при осмотре. Самовывоз.")
    assert a["bargain"] == "yes" and "торг уместен" in a["bargain_note"]
    assert analyze("Возможен торг, уступлю 5000")["bargain"] == "yes"
    assert analyze("Сброшу при быстрой сделке")["bargain"] == "yes"


def test_bargain_no():
    for text in ("Цена окончательная, торга нет", "Торг не уместен", "Без торга, не торгуюсь"):
        assert analyze(text)["bargain"] == "no", text


def test_trade_center_is_not_bargain():
    assert analyze("Самовывоз: ТЦ, торговый павильон 12")["bargain"] is None


def test_urgent_and_reason():
    a = analyze("Продаю срочно, так как перешел на 16 про. Состояние нового.")
    assert a["urgent"] and a["reason"] and "16" in a["reason"]


def test_not_opened_is_plus_not_repair():
    a = analyze("Не вскрывался, без ремонта, ни разу не падал, коробка и чек есть")
    assert a["repair"] == [] and a["sealed"] and a["docs"]


def test_repair_and_broken_flagged_with_snippets():
    a = analyze("Менял батарею в сервисе, после ремонта работает. Есть залитый угол, на запчасти не отдаю")
    assert a["repair"], a
    b = analyze("Ноутбук заблокирован, не включается")
    assert len(b["broken"]) == 2
    assert analyze("Все работает, ничего не залито, без вскрытия")["repair"] == []


def test_empty_text():
    a = analyze(None)
    assert a["bargain"] is None and a["repair"] == [] and a["surcharge_pct"] is None


def test_wear_detected_and_negations_respected():
    assert analyze("Есть мелкие царапины и потертости на углах")["wear"]
    for text in ("Без царапин и потертостей", "Царапин нет, состояние идеальное", "Ни одной царапины"):
        assert analyze(text)["wear"] == [], text
