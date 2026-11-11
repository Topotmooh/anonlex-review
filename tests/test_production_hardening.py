"""Продакшен-приёмка по ТЗ FR-06…FR-10: дыры приватности закрыты."""

from __future__ import annotations

import io
import zipfile

from anonlex.pipeline import anonymize_docx

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _docx(document: str, header: str | None = None, app: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {W}><w:body>{document}</w:body></w:document>')
        if header:
            zf.writestr("word/header1.xml", f'<?xml version="1.0"?><w:hdr {W}>{header}</w:hdr>')
        if app:
            zf.writestr("docProps/app.xml", app)
    return buf.getvalue()


def test_header_part_anonymized() -> None:
    """ТЗ FR-06: реквизиты в колонтитулах не утекают."""
    data = _docx(
        "<w:p><w:r><w:t>Договор поставки</w:t></w:r></w:p>",
        header="<w:p><w:r><w:t>ИНН 7707083893</w:t></w:r></w:p>",
    )
    result = anonymize_docx(data)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        header_xml = zf.read("word/header1.xml").decode("utf-8")
    assert "7707083893" not in header_xml
    assert "[ИНН_1]" in header_xml


def test_deltext_removed() -> None:
    """ТЗ FR-07: удалённый текст рецензирования не остаётся в файле."""
    data = _docx(
        "<w:p><w:r><w:t>Текст</w:t></w:r><w:r><w:delText>секретная правка 7707083893</w:delText></w:r></w:p>"
    )
    result = anonymize_docx(data)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
    assert "секретная правка" not in doc_xml


def test_author_anonymized() -> None:
    """ТЗ FR-10: автор правок не раскрывается."""
    data = _docx(
        '<w:p><w:ins w:author="Иванов Иван Иванович"><w:r><w:t>правка</w:t></w:r></w:ins></w:p>'
    )
    result = anonymize_docx(data)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
    assert "Иванов Иван Иванович" not in doc_xml
    assert 'w:author="Anonymized"' in doc_xml


def test_alttext_anonymized() -> None:
    """ТЗ FR-09: alt-text изображений проходит пайплайн."""
    data = _docx(
        '<w:p><w:r><w:t>См. рисунок</w:t></w:r></w:p>'
        '<w:p><w:r><w:object><w:docPr descr="Контакт: ivanov@company.ru"/></w:object></w:r></w:p>'
    )
    result = anonymize_docx(data)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        doc_xml = zf.read("word/document.xml").decode("utf-8")
    assert "ivanov@company.ru" not in doc_xml
    assert "[EMAIL_1]" in doc_xml


def test_app_company_scrubbed() -> None:
    """ТЗ FR-08: компания из метаданных app.xml не утекает."""
    data = _docx(
        "<w:p><w:r><w:t>Текст</w:t></w:r></w:p>",
        app='<?xml version="1.0"?><Properties><Company>ООО Ромашка</Company></Properties>',
    )
    result = anonymize_docx(data)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        app_xml = zf.read("docProps/app.xml").decode("utf-8")
    assert "ООО Ромашка" not in app_xml
    assert "<Company>Anonymized</Company>" in app_xml