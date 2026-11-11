"""Тесты модуля finder: поиск сущностей по регулярным выражениям и валидаторам.

Проверяет:
- Нахождение валидных сущностей (ИНН, БИК, счёт, email, телефон)
- Отсев невалидных (ИНН с неправильной контрольной суммой)
- Требование лейбла для SWIFT/IBAN
- Разрешение пересечений спанов
"""

from __future__ import annotations

from anonlex.finder import find_spans, Span


# Набор категорий, включённых в тестах (имитация default_enabled + PASSPORT)
ENABLED = frozenset({
    "INN", "KPP", "OGRN", "BIK", "ACCOUNT", "PASSPORT",
    "EMAIL", "PHONE", "SWIFT", "IBAN", "PERSON", "COMPANY",
})


# --------------------------------------------------------------------------
# ИНН
# --------------------------------------------------------------------------

def test_inn_found_and_invalid_skipped() -> None:
    """Валидный ИНН находится, невалидный — нет.

    Текст подобран так, чтобы '1234567890' не матчился как паспорт
    (добавлены буквы вокруг — паттерн паспорта требует разделитель или границы слова).
    """
    spans = find_spans("ИНН 7707083893 и мусор abc1234567890xyz", ENABLED)
    values = [(s.category, s.value) for s in spans]
    assert ("INN", "7707083893") in values
    assert all(v != "1234567890" for _, v in values)


def test_inn_12_digits() -> None:
    """ИНН физлица (12 цифр) находится."""
    spans = find_spans("ИНН 500100732259", ENABLED)
    values = [(s.category, s.value) for s in spans]
    # 500100732259 — валидный ИНН физлица
    assert ("INN", "500100732259") in values


# --------------------------------------------------------------------------
# БИК
# --------------------------------------------------------------------------

def test_bik_found() -> None:
    """БИК находится."""
    spans = find_spans("БИК 044525225", ENABLED)
    assert any(s.category == "BIK" and s.value == "044525225" for s in spans)


def test_bik_invalid_prefix() -> None:
    """БИК должен начинаться с 04."""
    spans = find_spans("БИК 123456789", ENABLED)
    assert not any(s.category == "BIK" for s in spans)


# --------------------------------------------------------------------------
# Банковский счёт
# --------------------------------------------------------------------------

def test_account_found() -> None:
    """Банковский счёт (20 цифр) находится."""
    spans = find_spans("Счёт 40702810400000000000", ENABLED)
    assert any(s.category == "ACCOUNT" and s.value == "40702810400000000000" for s in spans)


# --------------------------------------------------------------------------
# Паспорт
# --------------------------------------------------------------------------

def test_passport_found_without_label() -> None:
    """Паспорт находится без лейбла (needs_label=False).

    Паттерн: 4 цифры + разделитель + 6 цифр.
    """
    spans = find_spans("Паспорт 1234 567890", ENABLED)
    assert any(s.category == "PASSPORT" and s.value == "1234 567890" for s in spans)


def test_passport_10_digits_without_separator() -> None:
    """10 цифр подряд без разделителя — это паспорт (паттерн \b\d{4}[\s\-]?\d{6}\b)."""
    spans = find_spans("Паспорт 1234567890", ENABLED)
    # Паттерн допускает отсутствие разделителя
    assert any(s.category == "PASSPORT" for s in spans)


# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------

def test_email_found() -> None:
    """Email находится."""
    spans = find_spans("Свяжитесь с ivanov@company.ru", ENABLED)
    assert any(s.category == "EMAIL" and s.value == "ivanov@company.ru" for s in spans)


# --------------------------------------------------------------------------
# Телефон
# --------------------------------------------------------------------------

def test_phone_found() -> None:
    """Телефон находится."""
    spans = find_spans("Телефон +7 (916) 123-45-67", ENABLED)
    assert any(s.category == "PHONE" for s in spans)


def test_phone_not_inside_long_numbers() -> None:
    """Телефон не должен матчиться внутри длинных чисел (счетов).

    Паттерн использует lookbehind/lookahead (?<!\d)...(?!\d).
    """
    # 20-значный счёт — телефон внутри не должен найтись
    spans = find_spans("Счёт 40702810400000000000", {"PHONE"})
    assert not any(s.category == "PHONE" for s in spans)


# --------------------------------------------------------------------------
# SWIFT / IBAN (требуют лейбла)
# --------------------------------------------------------------------------

def test_swift_requires_label() -> None:
    """SWIFT без лейбла не находится."""
    spans = find_spans("Код SABRRUMM", ENABLED)
    assert not any(s.category == "SWIFT" for s in spans)


def test_swift_with_label() -> None:
    """SWIFT с лейблом находится."""
    spans = find_spans("SWIFT: SABRRUMM", ENABLED)
    assert any(s.category == "SWIFT" and s.value == "SABRRUMM" for s in spans)


def test_iban_requires_label() -> None:
    """IBAN без лейбла не находится."""
    spans = find_spans("Номер DE89370400440532013000", ENABLED)
    assert not any(s.category == "IBAN" for s in spans)


def test_iban_with_label() -> None:
    """IBAN с лейблом находится."""
    spans = find_spans("IBAN: DE89370400440532013000", ENABLED)
    assert any(s.category == "IBAN" for s in spans)


# --------------------------------------------------------------------------
# Разрешение пересечений
# --------------------------------------------------------------------------

def test_spans_sorted_and_disjoint() -> None:
    """Найденные спаны не пересекаются после разрешения."""
    text = "ИНН 7707083893, БИК 044525225, счёт 40702810400000000000"
    spans = find_spans(text, {"INN", "BIK", "ACCOUNT"})
    sorted_spans = sorted(spans, key=lambda s: s.start)
    for i in range(len(sorted_spans) - 1):
        assert sorted_spans[i].end <= sorted_spans[i + 1].start


def test_overlapping_spans_resolve_by_start() -> None:
    """При пересечении спанов оставляется тот, что начался раньше."""
    # ИНН 10 цифр и паспорт 10 цифр могут пересечься
    text = "1234567890"
    spans = find_spans(text, {"INN", "PASSPORT"})
    # Должен остаться только один спан (они полностью перекрываются)
    assert len(spans) == 1