"""Тесты валидаторов контрольных сумм и логики категорий.

Проверяет:
- Валидаторы ИНН, ОГРН, БИК, банковского счёта, паспорта РФ
- Категории по умолчанию (default_enabled)
- Флаги needs_label и zero_tolerance
- Разрешение пересечений сущностей
"""

from __future__ import annotations

from anonlex.categories import by_code, default_enabled, CATALOG, Priority
from anonlex.finder import (
    Span,
    find_spans,
    _validate_inn,
    _validate_ogrn,
    _validate_bik,
    _validate_account,
    _validate_passport,
)


# --------------------------------------------------------------------------
# Валидатор ИНН
# --------------------------------------------------------------------------

def test_inn_10_valid() -> None:
    """Валидный ИНН юрлица (10 цифр): Сбербанк."""
    assert _validate_inn("7707083893") is True


def test_inn_10_invalid_checksum() -> None:
    """Невалидный ИНН: контрольная сумма не сходится."""
    assert _validate_inn("1234567890") is False


def test_inn_12_valid() -> None:
    """Валидный ИНН физлица (12 цифр)."""
    # ИНН 500100732259 — валидный (пример из ФНС)
    assert _validate_inn("500100732259") is True


def test_inn_wrong_length() -> None:
    """ИНН неправильной длины не валидируется."""
    assert _validate_inn("12345") is False
    assert _validate_inn("12345678901") is False


# --------------------------------------------------------------------------
# Валидатор ОГРН
# --------------------------------------------------------------------------

def test_ogrn_13_valid() -> None:
    """Валидный ОГРН (13 цифр)."""
    # ОГРН 1027700132195 — валидный
    assert _validate_ogrn("1027700132195") is True


def test_ogrn_13_invalid() -> None:
    """Невалидный ОГРН."""
    assert _validate_ogrn("1234567890123") is False


def test_ogrn_15_valid() -> None:
    """Валидный ОГРН ИП (15 цифр)."""
    # ОГРН ИП 304500112000121: (30450011200012 % 13) % 10 = 1
    assert _validate_ogrn("304500112000121") is True


def test_ogrn_15_invalid() -> None:
    """Невалидный ОГРН ИП."""
    assert _validate_ogrn("304500112000123") is False


def test_ogrn_wrong_length() -> None:
    """ОГРН неправильной длины."""
    assert _validate_ogrn("12345") is False


# --------------------------------------------------------------------------
# Валидатор БИК
# --------------------------------------------------------------------------

def test_bik_valid() -> None:
    """Валидный БИК (9 цифр, начинается с 04)."""
    assert _validate_bik("044525225") is True


def test_bik_invalid_prefix() -> None:
    """БИК должен начинаться с 04."""
    assert _validate_bik("123456789") is False


def test_bik_wrong_length() -> None:
    """БИК должен быть 9 цифр."""
    assert _validate_bik("044525") is False


# --------------------------------------------------------------------------
# Валидатор банковского счёта
# --------------------------------------------------------------------------

def test_account_valid() -> None:
    """Валидный банковский счёт (20 цифр)."""
    assert _validate_account("40702810400000000000") is True


def test_account_wrong_length() -> None:
    """Счёт должен быть ровно 20 цифр."""
    assert _validate_account("4070281040000000000") is False
    assert _validate_account("407028104000000000001") is False


# --------------------------------------------------------------------------
# Валидатор паспорта РФ
# --------------------------------------------------------------------------

def test_passport_valid() -> None:
    """Валидный паспорт РФ (4+6 цифр)."""
    assert _validate_passport("1234567890") is True
    assert _validate_passport("1234 567890") is True
    assert _validate_passport("1234-567890") is True


def test_passport_invalid() -> None:
    """Невалидный паспорт."""
    assert _validate_passport("12345") is False
    assert _validate_passport("abcdefghij") is False


# --------------------------------------------------------------------------
# Категории по умолчанию
# --------------------------------------------------------------------------

def test_default_enabled_includes_core() -> None:
    """Ключевые категории включены по умолчанию."""
    enabled = {c.code for c in default_enabled()}
    assert "INN" in enabled
    assert "KPP" in enabled
    assert "OGRN" in enabled
    assert "BIK" in enabled
    assert "ACCOUNT" in enabled
    assert "PASSPORT" in enabled
    assert "EMAIL" in enabled
    assert "PHONE" in enabled
    assert "PERSON" in enabled
    assert "COMPANY" in enabled
    assert "SWIFT" in enabled
    assert "IBAN" in enabled


def test_default_enabled_excludes_opt_in() -> None:
    """Категории с default_on=False не включены по умолчанию.

    ADDRESS и AMOUNT отключены до спринта 6 (требуют калибровки паттернов).
    """
    enabled = {c.code for c in default_enabled()}
    assert "SSN" not in enabled
    assert "TAXID" not in enabled
    assert "URL" not in enabled
    assert "CONTRACT" not in enabled
    assert "ADDRESS" not in enabled  # отключено до спринта 6
    assert "AMOUNT" not in enabled   # отключено до спринта 6


def test_default_enabled_count() -> None:
    """Проверка количества категорий по умолчанию (может меняться)."""
    enabled = default_enabled()
    # Должно быть не менее 12 категорий
    assert len(enabled) >= 12


# --------------------------------------------------------------------------
# Флаги категорий
# --------------------------------------------------------------------------

def test_zero_tolerance_categories() -> None:
    """Категории с zero_tolerance=True."""
    zero_tol = {c.code for c in CATALOG if c.zero_tolerance}
    assert "INN" in zero_tol
    assert "OGRN" in zero_tol
    assert "BIK" in zero_tol
    assert "ACCOUNT" in zero_tol
    assert "PASSPORT" in zero_tol
    assert "SSN" in zero_tol
    assert "IBAN" in zero_tol


def test_needs_label_categories() -> None:
    """Категории, требующие контекстного лейбла."""
    needs_label = {c.code for c in CATALOG if c.needs_label}
    assert "SWIFT" in needs_label
    assert "IBAN" in needs_label
    assert "TAXID" in needs_label
    assert "CONTRACT" in needs_label


def test_priority_ordering() -> None:
    """Приоритеты категорий упорядочены корректно."""
    assert Priority.CHECKSUM > Priority.LABELED
    assert Priority.LABELED > Priority.TEXTUAL
    assert Priority.MANUAL > Priority.CHECKSUM


# --------------------------------------------------------------------------
# Поиск сущностей (finder)
# --------------------------------------------------------------------------

def test_find_inn_in_text() -> None:
    """Поиск валидного ИНН в тексте."""
    text = "ИНН организации 7707083893"
    spans = find_spans(text, {"INN"})
    assert len(spans) == 1
    assert spans[0].category == "INN"
    assert spans[0].value == "7707083893"


def test_find_invalid_inn_skipped() -> None:
    """Невалидный ИНН игнорируется."""
    text = "ИНН 1234567890"
    spans = find_spans(text, {"INN"})
    assert len(spans) == 0


def test_find_bik_in_text() -> None:
    """Поиск БИК в тексте."""
    text = "БИК банка 044525225"
    spans = find_spans(text, {"BIK"})
    assert len(spans) == 1
    assert spans[0].value == "044525225"


def test_find_account_in_text() -> None:
    """Поиск банковского счёта."""
    text = "Счёт 40702810400000000000"
    spans = find_spans(text, {"ACCOUNT"})
    assert len(spans) == 1
    assert spans[0].value == "40702810400000000000"


def test_find_email_in_text() -> None:
    """Поиск email."""
    text = "Свяжитесь с ivanov@company.ru"
    spans = find_spans(text, {"EMAIL"})
    assert len(spans) == 1
    assert spans[0].value == "ivanov@company.ru"


def test_find_phone_in_text() -> None:
    """Поиск телефона."""
    text = "Телефон +7 (916) 123-45-67"
    spans = find_spans(text, {"PHONE"})
    assert len(spans) == 1
    assert "+7" in spans[0].value


def test_swift_requires_label() -> None:
    """SWIFT без лейбла не находится."""
    text = "Код SABRRUMM"
    spans = find_spans(text, {"SWIFT"})
    assert len(spans) == 0


def test_swift_with_label() -> None:
    """SWIFT с лейблом находится."""
    text = "SWIFT: SABRRUMM"
    spans = find_spans(text, {"SWIFT"})
    assert len(spans) == 1
    assert spans[0].value == "SABRRUMM"


def test_iban_requires_label() -> None:
    """IBAN без лейбла не находится."""
    text = "Номер DE89370400440532013000"
    spans = find_spans(text, {"IBAN"})
    assert len(spans) == 0


def test_iban_with_label() -> None:
    """IBAN с лейблом находится."""
    text = "IBAN: DE89370400440532013000"
    spans = find_spans(text, {"IBAN"})
    assert len(spans) == 1


def test_passport_found_without_label() -> None:
    """Паспорт находится по паттерну 4+6 цифр без лейбла (needs_label=False)."""
    text = "Паспорт 1234 567890"
    spans = find_spans(text, {"PASSPORT"})
    assert len(spans) == 1
    assert spans[0].value == "1234 567890"


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


# --------------------------------------------------------------------------
# By_code
# --------------------------------------------------------------------------

def test_by_code_valid() -> None:
    """by_code возвращает категорию по коду."""
    cat = by_code("INN")
    assert cat.code == "INN"
    assert cat.label_ru == "ИНН"


def test_by_code_invalid() -> None:
    """by_code raises KeyError для неизвестного кода."""
    try:
        by_code("UNKNOWN")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass