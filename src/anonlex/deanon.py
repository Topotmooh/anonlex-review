"""Обратная деанонимизация: возврат реальных значений по маппингу (спринт 5)."""

from __future__ import annotations

from anonlex.mapping import Mapping


def restore_text(mapping: Mapping, text: str) -> str:
    """Заменяет плейсхолдеры на оригиналы.

    Длинные плейсхолдеры обрабатываются раньше коротких, чтобы [ФИО_1]
    не матчился внутри [ФИО_10].
    """
    pairs = sorted(
        ((e.placeholder, e.original_value) for e in mapping.entities),
        key=lambda p: len(p[0]),
        reverse=True,
    )
    for placeholder, original in pairs:
        text = text.replace(placeholder, original)
    return text