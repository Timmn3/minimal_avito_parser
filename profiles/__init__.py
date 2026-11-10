"""Профили товаров для research-задач. Новый товар = новый модуль + строка в PROFILES."""
from types import ModuleType
from typing import Optional

from profiles import macbook_pro_14

PROFILES: dict[str, ModuleType] = {
    macbook_pro_14.NAME: macbook_pro_14,
}


def get_profile(name: Optional[str]) -> Optional[ModuleType]:
    return PROFILES.get(name) if name else None
