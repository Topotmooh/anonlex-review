"""Тесты парсера .docx: virtualText, правки, экранирование, ZIP-целостность."""

import io
import zipfile

import pytest

from anonlex.parser import (
    MAIN_PART,
    Edit,
    apply_edits,
    iter_paragraphs,
    read_part,
    rebuild_zip,
    serialize_part,
)

W_DECL = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(paragraphs: list, extra: dict | None = None) -> bytes:
    """Собирает минимальный валидный .docx из списков run-ов каждого параграфа."""
    body = "".join(
        "<w:p>"
        + "".join(f'<w:r><w:t xml:space="preserve">{run}</w:t></w:r>' for run in runs)
        + "</w:p>"
        for runs in paragraphs
    )
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {W_DECL}><w:body>{body}</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr(MAIN_PART, document.encode("utf-8"))
        for name, payload in (extra or {}).items():
            zf.writestr(name, payload)
    return buf.getvalue()


def roundtrip(original: bytes, root) -> bytes:
    return rebuild_zip(original, {MAIN_PART: serialize_part(root)})


def test_virtual_text_multirun() -> None:
    doc = make_docx([["ИНН ", "7707", "083893"]])
    paragraphs = iter_paragraphs(read_part(doc))
    assert paragraphs[0].virtual_text == "ИНН 7707083893"
    assert [n.text for n in paragraphs[0].nodes] == ["ИНН ", "7707", "083893"]


def test_apply_edit_spans_runs() -> None:
    doc = make_docx([["ИНН ", "7707", "083893"]])
    root = read_part(doc)
    paragraph = iter_paragraphs(root)[0]
    apply_edits(paragraph, [Edit(start=4, end=14, new_text="[ИНН_1]")])
    result = roundtrip(doc, root)
    text = iter_paragraphs(read_part(result))[0].virtual_text
    assert text == "ИНН [ИНН_1]"


def test_original_absent_placeholder_present() -> None:
    """Quality-gate G4: в выходе нет оригинала, есть плейсхолдер."""
    doc = make_docx([["ИНН ", "7707", "083893"]])
    root = read_part(doc)
    apply_edits(iter_paragraphs(root)[0], [Edit(4, 14, "[ИНН_1]")])
    with zipfile.ZipFile(io.BytesIO(roundtrip(doc, root))) as zf:
        xml = zf.read(MAIN_PART).decode("utf-8")
    assert "7707083893" not in xml
    assert "[ИНН_1]" in xml


def test_escaping_roundtrip() -> None:
    doc = make_docx([["ООО Ромашка"]])
    root = read_part(doc)
    apply_edits(iter_paragraphs(root)[0], [Edit(0, 11, 'ООО «Ромашка» & Ко <test>')])
    text = iter_paragraphs(read_part(roundtrip(doc, root)))[0].virtual_text
    assert text == 'ООО «Ромашка» & Ко <test>'


def test_zip_preserves_other_parts() -> None:
    doc = make_docx([["текст"]], extra={"word/styles.xml": b"<w:styles/>"})
    root = read_part(doc)
    apply_edits(iter_paragraphs(root)[0], [Edit(0, 5, "[ТЕКСТ_1]")])
    with zipfile.ZipFile(io.BytesIO(roundtrip(doc, root))) as zf:
        assert zf.read("word/styles.xml") == b"<w:styles/>"
        assert zf.read("[Content_Types].xml") == b"<Types/>"


def test_xml_space_preserve_on_padded_replacement() -> None:
    doc = make_docx([["Иванов"]])
    root = read_part(doc)
    paragraph = iter_paragraphs(root)[0]
    apply_edits(paragraph, [Edit(0, 6, " [ФИО_1] ")])
    assert paragraph.nodes[0].element.get(
        "{http://www.w3.org/XML/1998/namespace}space"
    ) == "preserve"


def test_overlapping_edits_rejected() -> None:
    doc = make_docx([["abcdef"]])
    paragraph = iter_paragraphs(read_part(doc))
    with pytest.raises(ValueError):
        apply_edits(paragraph, [Edit(0, 4, "x"), Edit(3, 6, "y")])