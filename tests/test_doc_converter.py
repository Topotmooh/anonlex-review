"""Тесты конвертера .doc: детерминированные, бэкенды управляются monkeypatch.

Реальные бэкенды (LibreOffice/Word) всеядны к текстовым данным, поэтому
«мусорные байты» не гарантируют ошибку. Вместо этого мы явно отключаем
бэкенды или подменяем их заглушками — тесты не зависят от окружения.
"""

import pytest

from anonlex.doc_converter import DocConversionError, doc_to_docx
from anonlex.pipeline import anonymize_file


def _no_backends(monkeypatch) -> None:
    """Отключает оба бэкенда конвертации."""
    import anonlex.doc_converter as dc

    monkeypatch.setattr(dc, "_convert_libreoffice", lambda data, workdir: None)
    monkeypatch.setattr(dc, "_convert_word_com", lambda data, workdir: None)


def test_doc_without_backends_raises(monkeypatch) -> None:
    _no_backends(monkeypatch)
    with pytest.raises(DocConversionError):
        doc_to_docx(b"not a real doc file at all")


def test_pipeline_doc_without_backends_raises(monkeypatch) -> None:
    _no_backends(monkeypatch)
    with pytest.raises(DocConversionError):
        anonymize_file(b"not a real doc file at all", "legacy.doc")


def test_doc_uses_first_available_backend(monkeypatch) -> None:
    """Если первый бэкенд succeeded, второй не вызывается."""
    import anonlex.doc_converter as dc

    monkeypatch.setattr(dc, "_convert_libreoffice", lambda data, workdir: b"DOCXBYTES")

    def _should_not_run(data: bytes, workdir) -> bytes:
        raise AssertionError("второй бэкенд не должен вызываться")

    monkeypatch.setattr(dc, "_convert_word_com", _should_not_run)
    assert doc_to_docx(b"any bytes") == b"DOCXBYTES"