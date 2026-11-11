"""Тесты схемы маппинга anonlex.mapping/1.0."""

import json

import pytest

from anonlex.mapping import SCHEMA_VERSION, Mapping, MappingEntity


def test_roundtrip() -> None:
    mapping = Mapping(file_sha256="abc123", engine_version="0.1.0")
    mapping.add(MappingEntity("INN", "7707083893", "[ИНН_1]"))
    mapping.add(MappingEntity("INN", "7707083893", "[ИНН_1]"))
    restored = Mapping.from_json(mapping.to_json())
    assert restored.file_sha256 == "abc123"
    assert len(restored.entities) == 1
    assert restored.entities[0].occurrences == 2


def test_foreign_schema_rejected() -> None:
    payload = json.dumps({"schema": "2.0", "file_sha256": "x", "engine_version": "0", "entities": []})
    with pytest.raises(ValueError):
        Mapping.from_json(payload)
    assert SCHEMA_VERSION == "anonlex.mapping/1.0"


def test_placeholder_for_case_insensitive() -> None:
    mapping = Mapping(file_sha256="h", engine_version="0.1.0")
    mapping.add(MappingEntity("COMPANY", "ООО Ромашка", "[КОМПАНИЯ_1]"))
    assert mapping.placeholder_for("COMPANY", "ооо ромашка") == "[КОМПАНИЯ_1]"
    assert mapping.placeholder_for("COMPANY", "ООО Василёк") is None