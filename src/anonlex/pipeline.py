"""Основной пайплайн анонимизации документов."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from anonlex.categories import by_code, default_enabled, get_color
from anonlex.finder import find_spans
from anonlex.mapping import Mapping, MappingEntity
from anonlex.parser import (
    MAIN_PART,
    Edit,
    apply_edits,
    iter_paragraphs,
    read_part,
    rebuild_zip,
    serialize_part,
)

_VALID_MODES = ("placeholder", "mask", "black_blocks")
_BL = r"(?<![А-Яа-яЁёA-Za-z0-9_])"
_BR = r"(?![А-Яа-яЁёA-Za-z0-9_])"


@dataclass
class AnonymizeResult:
    docx: bytes
    mapping: Mapping
    spans: int
    preview: str = ""
    page_image: str = ""


def _bounded_find(text: str, form: str):
    if not form or len(form) < 3:
        return
    pat = re.compile(_BL + re.escape(form) + _BR)
    for m in pat.finditer(text):
        yield m.start(), m.end()


def _resolve_overlaps(spans: List[Tuple[int, int, str, str]]):
    ordered = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    kept: List[Tuple[int, int, str, str]] = []
    last_end = -1
    for s in ordered:
        if s[0] >= last_end:
            kept.append(s)
            last_end = s[1]
    return kept


def _person_key(value: str) -> str:
    try:
        from anonlex.knowledge import normalize_person
        return normalize_person(value)
    except Exception:
        return " ".join(value.lower().split())


def _ensure_entity(mapping: Mapping, counters: dict, category: str, value: str) -> MappingEntity:
    for e in mapping.entities:
        if e.category != category:
            continue
        if e.original_value == value:
            return e
        if category == "PERSON" and _person_key(e.original_value) == _person_key(value):
            return e
    counters[category] = counters.get(category, 0) + 1
    cat = by_code(category)
    ent = MappingEntity(
        category=category,
        original_value=value,
        placeholder=f"[{cat.placeholder_prefix}_{counters[category]}]",
        occurrences=1,
        color=get_color(category),
    )
    mapping.add(ent)
    return ent


def _org_spans(full_text: str, enabled: Set[str]):
    out = []
    try:
        from anonlex import org_dict as _org
    except Exception:
        return out
    for fn_name in ("find_spans", "find_in_text", "search"):
        fn = getattr(_org, fn_name, None)
        if not callable(fn):
            continue
        try:
            items = fn(full_text, enabled_categories=enabled)
        except TypeError:
            try:
                items = fn(full_text, enabled)
            except Exception:
                continue
        except Exception:
            continue
        for it in items:
            cat = getattr(it, "category", None)
            val = getattr(it, "value", None) or getattr(it, "text", None)
            st = getattr(it, "start", None)
            en = getattr(it, "end", None)
            if cat and val and st is not None and en is not None:
                out.append((int(st), int(en), cat, val))
            elif cat and val:
                for a, b in _bounded_find(full_text, val):
                    out.append((a, b, cat, val))
        break
    return out


def anonymize_docx(
    docx_bytes: bytes,
    enabled: Optional[Set[str]] = None,
    redaction_mode: str = "placeholder",
) -> AnonymizeResult:
    if redaction_mode not in _VALID_MODES:
        raise ValueError(f"Неизвестный режим redaction: {redaction_mode}")
    if enabled is None:
        enabled = default_enabled()
    enabled = set(enabled)

    from anonlex.docx_hardening import harden_docx

    doc_hash = hashlib.sha256(docx_bytes).hexdigest()
    mapping = Mapping(file_sha256=doc_hash, engine_version="1.0.0")

    root = read_part(docx_bytes)
    paragraphs = iter_paragraphs(root)
    full_text = "\n".join(p.virtual_text for p in paragraphs)

    # Пустой документ — чистим только метаданные/скрытые части
    if not full_text or not full_text.strip():
        cleaned = harden_docx(docx_bytes, mapping, enabled, redaction_mode)
        return AnonymizeResult(docx=cleaned, mapping=mapping, spans=0, preview="")

    raw: List[Tuple[int, int, str, str]] = []
    for s in find_spans(full_text, enabled_categories=enabled):
        raw.append((s.start, s.end, s.category, s.value))

    try:
        from anonlex.knowledge import extract_entities_full_text, forms_of
        for ent in extract_entities_full_text(full_text):
            if ent.category not in enabled:
                continue
            for form in forms_of(ent):
                for a, b in _bounded_find(full_text, form):
                    raw.append((a, b, ent.category, ent.value))
    except Exception:
        pass

    raw.extend(_org_spans(full_text, enabled))
    spans = _resolve_overlaps(raw)

    counters: dict = {}
    lookup: dict = {}
    for (_st, _en, cat, val) in spans:
        lookup[(cat, val)] = _ensure_entity(mapping, counters, cat, val)

    for ent in mapping.entities:
        ent.occurrences = sum(
            1 for (_a, _b, c, v) in spans if (c, v) == (ent.category, ent.original_value)
        ) or 1

    if not spans:
        cleaned = harden_docx(docx_bytes, mapping, enabled, redaction_mode)
        return AnonymizeResult(docx=cleaned, mapping=mapping, spans=0, preview=full_text)

    offsets = []
    cur = 0
    for p in paragraphs:
        offsets.append((cur, cur + len(p.virtual_text)))
        cur += len(p.virtual_text) + 1

    total = 0
    for idx, paragraph in enumerate(paragraphs):
        p_start, p_end = offsets[idx]
        edits = []
        for (st, en, cat, val) in spans:
            if st >= p_start and en <= p_end:
                ent = lookup.get((cat, val))
                if redaction_mode == "placeholder":
                    repl = ent.placeholder if ent else f"[{cat}_?]"
                else:
                    repl = "█" * (en - st)
                edits.append(Edit(start=st - p_start, end=en - p_start, new_text=repl))
                total += 1
        if edits:
            apply_edits(paragraph, edits)

    result_bytes = rebuild_zip(docx_bytes, {MAIN_PART: serialize_part(root)})
    result_bytes = harden_docx(result_bytes, mapping, enabled, redaction_mode)

    preview = full_text
    for ent in sorted(mapping.entities, key=lambda e: -len(e.original_value)):
        preview = preview.replace(ent.original_value, ent.placeholder)

    return AnonymizeResult(
        docx=result_bytes,
        mapping=mapping,
        spans=total,
        preview=preview,
    )


def anonymize_file(
    content: bytes,
    filename: str,
    enabled: Optional[Set[str]] = None,
    redaction_mode: str = "placeholder",
) -> AnonymizeResult:
    lower = filename.lower()

    if lower.endswith(".docx"):
        return anonymize_docx(content, enabled=enabled, redaction_mode=redaction_mode)

    if lower.endswith(".doc"):
        from anonlex.doc_converter import doc_to_docx
        return anonymize_docx(
            doc_to_docx(content), enabled=enabled, redaction_mode=redaction_mode
        )

    if lower.endswith(".pdf"):
        from anonlex.pdf_anonymizer import anonymize_pdf
        out, m, sp, prev, img = anonymize_pdf(content, enabled=enabled)
        return AnonymizeResult(docx=out, mapping=m, spans=sp, preview=prev, page_image=img)

    if lower.endswith(".xlsx"):
        from anonlex.xlsx_anonymizer import anonymize_xlsx
        r = anonymize_xlsx(content, enabled=enabled)
        return AnonymizeResult(docx=r.docx, mapping=r.mapping, spans=r.spans, preview=r.preview)

    raise ValueError(f"Неподдерживаемый формат: {filename}")