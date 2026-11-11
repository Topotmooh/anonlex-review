"""Смоук-тест корпуса: пайплайн на синтетике без пропусков и ложных срабатываний."""

import io
import random
import zipfile

from anonlex.categories import CATALOG
from anonlex.corpus import build_document
from anonlex.knowledge import normalize_company, normalize_person
from anonlex.metrics import evaluate
from anonlex.pipeline import anonymize_docx

W_DECL = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
_NORMALIZERS = {"PERSON": normalize_person, "COMPANY": normalize_company}


def make_docx(paragraphs: list) -> bytes:
    body = "".join(
        "<w:p>"
        + "".join(f'<w:r><w:t xml:space="preserve">{run}</w:t></w:r>' for run in runs)
        + "</w:p>"
        for runs in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        f"<w:document {W_DECL}><w:body>{body}</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("word/document.xml", document.encode("utf-8"))
    return buf.getvalue()


def test_synthetic_corpus_gates_pass() -> None:
    rng = random.Random(7)
    gold = set()
    pred = set()
    for index in range(1, 6):
        paragraphs, doc_gold = build_document(rng, index)
        gold |= set(doc_gold)
        mapping = anonymize_docx(make_docx(paragraphs)).mapping
        for entity in mapping.entities:
            norm = _NORMALIZERS.get(entity.category)
            key = norm(entity.original_value) if norm else entity.original_value.casefold()
            pred.add((entity.category, key))

    categories = sorted({cat for cat, _ in gold} | {cat for cat, _ in pred})
    zero = tuple(c.code for c in CATALOG if c.zero_tolerance)
    report = evaluate(gold, pred, categories, zero)
    assert report.zero_tolerance_violations() == []
    assert report.overall().precision == 1.0
    assert report.overall().recall == 1.0