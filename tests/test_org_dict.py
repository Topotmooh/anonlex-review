"""Тесты словаря организации: правила реально применяются пайплайном (B-018)."""

from __future__ import annotations

import io
import zipfile

import pytest
from anonlex import org_dict
from anonlex.pipeline import anonymize_docx
from docx import Document


def make_docx(paragraphs: list[str]) -> bytes:
    """DOCX из одного ранa на абзац."""
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def xml_of(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


@pytest.fixture(autouse=True)
def isolated_dict(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Словарь в tmp_path: тесты не пишут в рабочий server/org_dict.json."""
    monkeypatch.setattr(org_dict, "_DICT_PATH", tmp_path / "org_dict.json")
    org_dict.invalidate_cache()
    yield
    org_dict.invalidate_cache()


def test_manual_rule_is_applied_by_pipeline() -> None:
    org_dict.add_rule("Проект «Квант»", "COMPANY", r"(?<!\w)Квант(?!\w)")
    result = anonymize_docx(make_docx(["Согласовано с проектом Квант"]), enabled={"COMPANY"})
    xml = xml_of(result.docx)
    assert "Квант" not in xml
    assert "█" in xml


def test_disabled_rule_is_not_applied() -> None:
    rule = org_dict.add_rule("Проект «Квант»", "COMPANY", r"(?<!\w)Квант(?!\w)")
    assert org_dict.toggle_rule(rule["id"], False)
    xml = xml_of(
        anonymize_docx(make_docx(["Согласовано с проектом Квант"]), enabled={"COMPANY"}).docx
    )
    assert "Квант" in xml


def test_learned_rule_catches_inflected_forms() -> None:
    """Выученная правка ловит падежные формы (правило по основам слов)."""
    org_dict.learn_from_manual("PERSON", "Кузнецов Кузьма Кузьмич")
    xml = xml_of(
        anonymize_docx(make_docx(["Подпись: Кузнецова Кузьма Кузьмича"]), enabled={"PERSON"}).docx
    )
    assert "Кузнецова" not in xml


def test_builtin_address_rule_applies_when_category_enabled() -> None:
    xml = xml_of(
        anonymize_docx(
            make_docx(["Адрес: г. Екатеринбург, ул. Мира, д. 5, кв. 7"]),
            enabled={"ADDRESS"},
        ).docx
    )
    assert "Екатеринбург" not in xml


def test_corrupt_dict_does_not_break_anonymization(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Битый файл словаря не должен ронять анонимизацию."""
    broken = tmp_path / "broken.json"
    broken.write_text("{не json", encoding="utf-8")
    monkeypatch.setattr(org_dict, "_DICT_PATH", broken)
    org_dict.invalidate_cache()
    xml = xml_of(anonymize_docx(make_docx(["ИНН 7707083893"]), enabled={"INN"}).docx)
    assert "7707083893" not in xml
