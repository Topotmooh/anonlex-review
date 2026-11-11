"""Сквозные тесты пайплайна: файл → файл + маппинг + метаданные."""

import io
import zipfile

from anonlex.mapping import Mapping
from anonlex.pipeline import anonymize_docx

W_DECL = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(paragraphs: list, extra: dict | None = None) -> bytes:
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
        zf.writestr("word/document.xml", document.encode("utf-8"))
        for name, payload in (extra or {}).items():
            zf.writestr(name, payload)
    return buf.getvalue()


def xml_of(result_docx: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(result_docx)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


CONTRACT = [
    ["ДОГОВОР ПОСТАВКИ № 45/2026"],
    ["Покупатель: ООО «Ромашка», ИНН 7707083893."],
    ["РЕКВИЗИТЫ СТОРОН"],
    ["ООО «Ромашка», ИНН 7707083893"],
    ["Директор Иванов Иван Иванович"],
    ["Подпись: Иванов И.И."],
]


def test_end_to_end_replaces_all_forms() -> None:
    result = anonymize_docx(make_docx(CONTRACT))
    xml = xml_of(result.docx)
    assert "7707083893" not in xml
    assert "Ромашка" not in xml
    assert "Иванов" not in xml  # включая сокращённую форму из подписи
    assert "[ИНН_1]" in xml and "[КОМПАНИЯ_1]" in xml and "[ФИО_1]" in xml


def test_uppercase_person_closed_gap() -> None:
    doc = make_docx([
        ["РЕКВИЗИТЫ СТОРОН"],
        ["ИВАНОВ ИВАН ИВАНОВИЧ"],
        ["исполнитель: Иванов И.И."],
    ])
    xml = xml_of(anonymize_docx(doc).docx)
    assert "ИВАНОВ" not in xml and "Иванов" not in xml
    assert "[ФИО_1]" in xml


def test_mapping_placeholder_consistency() -> None:
    result = anonymize_docx(make_docx(CONTRACT))
    persons = [e for e in result.mapping.entities if e.category == "PERSON"]
    assert len(persons) == 1
    assert persons[0].occurrences >= 2  # полная форма + сокращённая
    restored = Mapping.from_json(result.mapping.to_json())
    assert restored.entities == result.mapping.entities


def test_metadata_scrubbed() -> None:
    core = (
        '<?xml version="1.0"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:creator>Ivan Ivanov</dc:creator>"
        "<cp:lastModifiedBy>Petr Petrov</cp:lastModifiedBy>"
        "</cp:coreProperties>"
    )
    doc = make_docx([["текст"]], extra={"docProps/core.xml": core.encode("utf-8")})
    result = anonymize_docx(doc)
    with zipfile.ZipFile(io.BytesIO(result.docx)) as zf:
        core_out = zf.read("docProps/core.xml").decode("utf-8")
    assert "Ivan Ivanov" not in core_out and "Petr Petrov" not in core_out
    assert core_out.count("Anonymized") == 2


def test_empty_document_passthrough() -> None:
    result = anonymize_docx(make_docx([["Простой текст без персональных данных"]]))
    assert result.spans == 0
    assert result.mapping.entities == []