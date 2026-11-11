"""Тесты анонимизации PDF."""

import fitz
from anonlex.pdf_anonymizer import anonymize_pdf


def make_pdf(text: str) -> bytes:
    """Создает тестовый PDF с текстом."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    output = doc.tobytes()
    doc.close()
    return output


def test_pdf_inn_replacement() -> None:
    pdf = make_pdf("ИНН 7707083893")
    result_pdf, mapping, spans, _preview, _img = anonymize_pdf(pdf)
    assert spans > 0
    assert len(mapping.entities) > 0


def test_pdf_empty() -> None:
    pdf = make_pdf("Простой текст без данных")
    result_pdf, mapping, spans, _preview, _img = anonymize_pdf(pdf)
    assert spans == 0
    assert len(mapping.entities) == 0