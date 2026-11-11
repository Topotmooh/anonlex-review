"""Тесты обратной деанонимизации."""

from anonlex.deanon import restore_text
from anonlex.mapping import Mapping, MappingEntity


def _mapping() -> Mapping:
    return Mapping(file_sha256="h", engine_version="0.1.0")


def test_restore_placeholders() -> None:
    mapping = _mapping()
    mapping.entities.append(MappingEntity("PERSON", "Иванов Иван Иванович", "[ФИО_1]"))
    mapping.entities.append(MappingEntity("INN", "7707083893", "[ИНН_1]"))
    out = restore_text(mapping, "Для [ФИО_1] ИНН [ИНН_1] риск минимален.")
    assert out == "Для Иванов Иван Иванович ИНН 7707083893 риск минимален."


def test_long_placeholder_first() -> None:
    mapping = _mapping()
    mapping.entities.append(MappingEntity("PERSON", "Иванов", "[ФИО_1]"))
    mapping.entities.append(MappingEntity("PERSON", "Петрова", "[ФИО_10]"))
    assert restore_text(mapping, "[ФИО_10] и [ФИО_1]") == "Петрова и Иванов"


def test_unknown_placeholder_untouched() -> None:
    assert restore_text(_mapping(), "[ФИО_99] остаётся") == "[ФИО_99] остаётся"