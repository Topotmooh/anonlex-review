"""Каталог категорий сущностей AnonLex.

Единый источник правды о категориях: лейблы RU/EN, префиксы плейсхолдеров,
приоритеты пересечений, флаги включения и нулевой терпимости.
Модуль не зависит от UI, транспорта и хранилища.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Set, Tuple


class Priority(IntEnum):
    """Приоритет категории при разрешении пересечений сущностей."""

    TEXTUAL = 10    # эвристики: PERSON, COMPANY, ADDRESS
    LABELED = 20    # требуют контекстного лейбла: SWIFT, IBAN, TAXID, CONTRACT
    CHECKSUM = 30   # строгие контрольные суммы: INN, BIK, IBAN...
    MANUAL = 40     # добавлено пользователем вручную — выше всех


@dataclass(frozen=True)
class Category:
    """Описание категории сущности."""

    code: str
    label_ru: str
    label_en: str
    placeholder_prefix: str
    default_on: bool
    priority: Priority
    zero_tolerance: bool = False    # пропуск недопустим (Recall = 100%)
    needs_label: bool = False       # срабатывает только рядом с лейблом


CATALOG: Tuple[Category, ...] = (
    Category("PERSON", "ФИО", "Person name", "ФИО", True, Priority.TEXTUAL),
    Category("COMPANY", "Организация", "Company", "КОМПАНИЯ", True, Priority.TEXTUAL),
    Category("INN", "ИНН", "Taxpayer ID", "ИНН", True, Priority.CHECKSUM, zero_tolerance=True),
    Category("KPP", "КПП", "KPP", "КПП", True, Priority.CHECKSUM),
    Category("OGRN", "ОГРН", "OGRN", "ОГРН", True, Priority.CHECKSUM, zero_tolerance=True),
    Category("BIK", "БИК", "BIC", "БИК", True, Priority.CHECKSUM, zero_tolerance=True),
    Category("ACCOUNT", "Банковский счёт", "Bank account", "СЧЁТ", True, Priority.CHECKSUM, zero_tolerance=True),
    Category("PASSPORT", "Паспорт РФ", "RF passport", "ПАСПОРТ", True, Priority.CHECKSUM, zero_tolerance=True),
    Category("SSN", "SSN", "SSN", "SSN", False, Priority.CHECKSUM, zero_tolerance=True),
    Category("TAXID", "Tax ID", "Tax ID", "TAXID", False, Priority.LABELED, needs_label=True),
    Category("SWIFT", "SWIFT", "SWIFT", "SWIFT", True, Priority.LABELED, needs_label=True),
    Category("IBAN", "IBAN", "IBAN", "IBAN", True, Priority.LABELED, needs_label=True, zero_tolerance=True),
    Category("EMAIL", "E-mail", "Email", "EMAIL", True, Priority.CHECKSUM),
    Category("PHONE", "Телефон", "Phone", "ТЕЛ", True, Priority.TEXTUAL),
    Category("URL", "URL", "URL", "URL", False, Priority.TEXTUAL),
    Category("ADDRESS", "Адрес", "Address", "АДРЕС", False, Priority.TEXTUAL),
    Category("CONTRACT", "Номер договора", "Contract No.", "ДОГОВОР", False, Priority.LABELED, needs_label=True),
    Category("AMOUNT", "Денежная сумма", "Amount", "СУММА", False, Priority.LABELED, needs_label=True),
    # Опциональные (спринт 8+): включаются через пресеты/настройки
    Category("SNILS", "СНИЛС", "SNILS", "СНИЛС", False, Priority.CHECKSUM, zero_tolerance=True),
    Category("PLATE", "Номер авто", "Plate", "АВТО", False, Priority.TEXTUAL),
    Category("DIAGNOSIS", "Диагноз", "Diagnosis", "ДИАГНОЗ", False, Priority.TEXTUAL),
    Category("POLIS_OMS", "Полис ОМС", "OMS polis", "ПОЛИС", False, Priority.TEXTUAL),
    Category("BIOMETRIC", "Биометрия", "Biometric", "БИОМЕТРИЯ", False, Priority.CHECKSUM, zero_tolerance=True),
    Category("BIRTH_CERT", "Свидет. о рожд.", "Birth cert", "СВИДЕТ", False, Priority.TEXTUAL),
)


def by_code(code: str) -> Category:
    """Возвращает категорию по коду.

    Raises:
        KeyError: если код отсутствует в каталоге.
    """
    index: Dict[str, Category] = {c.code: c for c in CATALOG}
    return index[code]


def default_enabled() -> Tuple[Category, ...]:
    """Категории, включённые по умолчанию."""
    return tuple(c for c in CATALOG if c.default_on)


def default_enabled_codes() -> Set[str]:
    """Коды категорий по умолчанию — удобно движкам (DOCX/PDF/XLSX)."""
    return {c.code for c in CATALOG if c.default_on}

# --------------------------------------------------------------------------
# Цветовая схема категорий (спринт 6, FR-23)
# --------------------------------------------------------------------------

CATEGORY_COLORS: Dict[str, str] = {
    "INN": "#dc2626",        # красный (критично)
    "OGRN": "#dc2626",
    "BIK": "#dc2626",
    "ACCOUNT": "#dc2626",
    "PASSPORT": "#dc2626",
    "KPP": "#ea580c",        # оранжевый
    "PERSON": "#2563eb",     # синий (люди)
    "COMPANY": "#16a34a",    # зелёный (организации)
    "EMAIL": "#9333ea",      # фиолетовый
    "PHONE": "#ea580c",      # оранжевый
    "URL": "#64748b",        # серый
    "ADDRESS": "#0891b2",    # бирюзовый
    "AMOUNT": "#ca8a04",     # жёлтый
    "CONTRACT": "#7c3aed",   # фиолетовый
    "SWIFT": "#059669",      # изумрудный
    "IBAN": "#059669",
    "TAXID": "#059669",
    "SSN": "#059669",
    "SNILS": "#dc2626",
    "PLATE": "#64748b",
    "DIAGNOSIS": "#be185d",
    "POLIS_OMS": "#be185d",
    "BIOMETRIC": "#be185d",
    "BIRTH_CERT": "#be185d",
    "DEFAULT": "#64748b",    # серый по умолчанию
}


def get_color(category: str) -> str:
    """Возвращает цвет категории (или DEFAULT, если категория неизвестна)."""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["DEFAULT"])