"""Пресеты отраслевых compliance-профилей (спринт 8.5).

Пресет = curated-набор категорий, включённых по умолчанию для конкретной отрасли.
"""

from __future__ import annotations

from typing import Dict, List, Set


PRESETS: Dict[str, Dict] = {
    "court": {
        "name": "Судебный акт",
        "description": "Приказ Суддепартамента ВС РФ №190 — обезличивание публикуемых судебных актов",
        "categories": [
            "PERSON", "ADDRESS", "PASSPORT", "SNILS", "PLATE",
            "PHONE", "EMAIL", "INN", "OGRN", "ACCOUNT", "BIK",
        ],
    },
    "tender": {
        "name": "Госзакупки (44/223-ФЗ)",
        "description": "Обезличивание тендерной документации для публикации",
        "categories": [
            "PERSON", "COMPANY", "INN", "KPP", "OGRN", "BIK", "ACCOUNT",
            "ADDRESS", "PHONE", "EMAIL", "CONTRACT", "AMOUNT",
        ],
    },
    "medical": {
        "name": "Медицина (ФЗ-323)",
        "description": "Обезличивание медицинских данных (особая категория по ст. 10 152-ФЗ)",
        "categories": [
            "PERSON", "POLIS_OMS", "DIAGNOSIS", "BIOMETRIC", "BIRTH_CERT",
            "PASSPORT", "SNILS", "ADDRESS", "PHONE", "EMAIL",
        ],
    },
}


def get_preset(preset_code: str) -> Set[str] | None:
    """Возвращает набор категорий пресета или None, если пресет неизвестен."""
    preset = PRESETS.get(preset_code)
    if preset is None:
        return None
    return set(preset["categories"])


def list_presets() -> List[Dict]:
    """Список всех пресетов для UI."""
    return [
        {"code": code, "name": p["name"], "description": p["description"]}
        for code, p in PRESETS.items()
    ]