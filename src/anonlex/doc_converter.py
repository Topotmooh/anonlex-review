"""Конвертация legacy .doc (Word 97-2003) в .docx для пайплайна (спринт 5e).

Два бэкенда, первый доступный побеждает:
1. LibreOffice headless (рекомендуется для on-premise, Linux/Windows).
2. Microsoft Word через COM (только Windows, если Word установлен).

Конвертация выполняется ВНЕШНЕЙ программой: наш код не линкуется с её
библиотеками, поэтому лицензионная чистота ядра сохраняется (ADR-006).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class DocConversionError(RuntimeError):
    """Не удалось конвертировать .doc: нет доступного бэкенда."""


def _convert_libreoffice(data: bytes, workdir: Path) -> Optional[bytes]:
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return None
    src = workdir / "input.doc"
    src.write_bytes(data)
    proc = subprocess.run(
        [exe, "--headless", "--convert-to", "docx", "--outdir", str(workdir), str(src)],
        capture_output=True,
        timeout=120,
    )
    out = workdir / "input.docx"
    if proc.returncode != 0 or not out.exists():
        return None
    return out.read_bytes()


def _convert_word_com(data: bytes, workdir: Path) -> Optional[bytes]:
    try:
        import win32com.client  # type: ignore  # pywin32, опционально
    except Exception:
        return None
    src = workdir / "input.doc"
    src.write_bytes(data)
    dst = workdir / "input.docx"
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(src))
        doc.SaveAs(str(dst), FileFormat=12)  # wdFormatXMLDocument = .docx
        doc.Close(False)
        word.Quit()
    except Exception:
        return None
    if not dst.exists():
        return None
    return dst.read_bytes()


def doc_to_docx(data: bytes) -> bytes:
    """Конвертирует .doc в .docx первым доступным бэкендом."""
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for backend in (_convert_libreoffice, _convert_word_com):
            result = backend(data, workdir)
            if result:
                return result
    raise DocConversionError(
        "Не удалось конвертировать .doc: установите LibreOffice (рекомендуется) "
        "или Microsoft Word на сервере."
    )