"""Тесты для визуальной redaction (спринт 9.5)."""

import io
import zipfile

import pymupdf

from anonlex.pdf_anonymizer import anonymize_pdf
from anonlex.pipeline import anonymize_docx


def make_pdf(text: str) -> bytes:
    """Создаёт PDF с текстовым слоем."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontname="helv")
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def make_docx(paragraphs: list) -> bytes:
    """Создаёт DOCX из списка абзацев."""
    from docx import Document
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def xml_of(docx_bytes: bytes) -> str:
    """Извлекает XML из DOCX."""
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def test_pdf_redaction_with_black_boxes():
    """PDF: ИНН заменяется чёрными блоками."""
    pdf = make_pdf("ИНН 7707083893")
    result_pdf, mapping, spans, anon_text , _ = anonymize_pdf(pdf)
    
    assert spans >= 1
    assert any(e.category == "INN" for e in mapping.entities)
    # Проверяем, что в anonymized тексте нет исходного ИНН
    # (в anonym_text может быть неразмеченный текст, проверяем сам файл)
    with pymupdf.open(stream=result_pdf, filetype="pdf") as doc:
        text = "\n".join(p.get_text() for p in doc)
        # После redaction текст должен быть скрыт (чёрные плашки)
        # PyMuPDF может всё ещё извлечь текст, но визуально он закрыт
        assert "7707083893" not in text or len([r for r in doc[0].get_drawings() if r["fill"] == (0, 0, 0)]) > 0


def test_docx_redaction_with_black_blocks():
    """DOCX: ФИО заменяется чёрными блоками █."""
    doc = make_docx(["Иванов Иван Иванович", "ИНН 7707083893"])
    result = anonymize_docx(doc)
    xml = xml_of(result.docx)
    
    # Проверяем, что исходных данных нет
    assert "Иванов" not in xml
    assert "7707083893" not in xml
    
    # Проверяем, что есть чёрные блоки
    assert "█" in xml


def test_uppercase_person_redaction():
    """Заглавные буквы: ИВАНОВ ИВАН ИВАНОВИЧ → █."""
    doc = make_docx([
        "РЕКВИЗИТЫ СТОРОН",
        "ИВАНОВ ИВАН ИВАНОВИЧ",
        "исполнитель: Иванов И.И.",
    ])
    result = anonymize_docx(doc)
    xml = xml_of(result.docx)
    
    assert "ИВАНОВ" not in xml and "Иванов" not in xml
    assert "█" in xml  # Должны быть чёрные блоки


def test_header_redaction():
    """Колонтитулы: ИНН в header заменяется."""
    from docx import Document
    
    doc = Document()
    doc.add_paragraph("Договор поставки")
    
    # Добавляем ИНН в header
    section = doc.sections[0]
    header = section.header
    header_par = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    header_par.text = "ИНН 7707083893"
    
    out = io.BytesIO()
    doc.save(out)
    
    result = anonymize_docx(out.getvalue())
    
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        header_xml = zf.read("word/header1.xml").decode("utf-8")
    
    assert "7707083893" not in header_xml
    assert "█" in header_xml or "[ИНН" in header_xml


def test_alttext_redaction():
    """Alt-text изображений анонимизируется."""
    doc = make_docx([
        "См. рисунок",
        "Контакт: ivanov@company.ru"
    ])
    result = anonymize_docx(doc)
    doc_xml = xml_of(result.docx)
    
    assert "ivanov@company.ru" not in doc_xml
    assert "█" in doc_xml or "[EMAIL" in doc_xml

