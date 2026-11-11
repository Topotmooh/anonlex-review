"""Тесты базы знаний: канонизация ФИО и фильтр OCR/органо мусора.

Регрессии:
- B-005: организационные слова («Управление», «Сведения об оценщиках»)
  не должны превращаться в ФИО;
- B-007: реквизитный мусор («Иванов Иван Иванович Паспорт») не должен
  становиться отдельной сущностью;
- канонизация «Сидоров Пётр Павлович» == «Сидоров П.П.» (docs/05_TEST_PLAN.md).
"""

from __future__ import annotations

from anonlex.knowledge import (
    extract_entities,
    extract_entities_full_text,
    forms_of,
    normalize_person,
)
from anonlex.mapping import Mapping, MappingEntity


def _persons(text: str) -> list[str]:
    return [e.value for e in extract_entities_full_text(text) if e.category == "PERSON"]


def test_normalize_person_unifies_full_and_short() -> None:
    assert normalize_person("Сидоров Пётр Павлович") == "сидоров п.п."
    assert normalize_person("Сидоров П.П.") == "сидоров п.п."
    assert normalize_person("СИДОРОВ ПЁТР ПЕТРОВИЧ") == "сидоров п.п."
    assert normalize_person("И.И. Иванов") == "иванов и.и."


def test_org_word_triple_is_not_a_person() -> None:
    """B-005: «УПРАВЛЕНИЕ ПО ДЕЛАМ ОБРАЗОВАНИЯ» — не ФИО."""
    assert _persons("УПРАВЛЕНИЕ ПО ДЕЛАМ ОБРАЗОВАНИЯ") == []


def test_heading_is_not_a_person() -> None:
    assert _persons("СВЕДЕНИЯ ОБ ОЦЕНЩИКАХ") == []


def test_requisites_tail_is_trimmed_from_person() -> None:
    """B-007: слово «Паспорт» после ФИО не входит в значение."""
    assert _persons("Иванов Иван Иванович Паспорт 45 00 123456") == ["Иванов Иван Иванович"]


def test_person_survives_ocr_label_prefix() -> None:
    """B-007: ФИО после орглейбла распознаётся, мусор отрезается."""
    assert _persons("ОЦЕНЩИКИ ИВАНОВ ИВАН ИВАНОВИЧ") == ["ИВАНОВ ИВАН ИВАНОВИЧ"]


def test_court_boilerplate_is_not_a_person() -> None:
    assert _persons("РЕШЕНИЕ ИМЕНЕМ") == []


def test_forms_of_includes_short_and_upper() -> None:
    entity = extract_entities(["Директор Иванов Иван Иванович"])[0]
    forms = forms_of(entity)
    assert "Иванов И.И." in forms
    assert "ИВАНОВ ИВАН ИВАНОВИЧ" in forms
    assert "Иванов" in forms


def test_deanon_restores_pipeline_placeholder() -> None:
    """Плейсхолдеры переживают сериализацию маппинга (обратная деанонимизация)."""
    mapping = Mapping(file_sha256="h", engine_version="1.0.0")
    mapping.add(MappingEntity("PERSON", "Иванов Иван Иванович", "[ФИО_1]"))
    restored = Mapping.from_json(mapping.to_json())
    assert restored.get_by_placeholder("[ФИО_1]").original_value == "Иванов Иван Иванович"
