"""Анонимизация PDF: настоящая redaction через PyMuPDF."""
from __future__ import annotations

import base64
import hashlib
from typing import List, Optional, Set, Tuple

import fitz

from anonlex.categories import by_code, default_enabled, get_color
from anonlex.mapping import Mapping, MappingEntity
from anonlex.pii_core import detect, person_key

PROCESS_LOG: List[str] = []


def anonymize_pdf(
    pdf_bytes: bytes,
    mapping: Optional[Mapping] = None,
    enabled: Optional[Set[str]] = None,
) -> Tuple[bytes, Mapping, int, str, str]:
    PROCESS_LOG.clear()
    if enabled is None:
        enabled = default_enabled()
    enabled = set(enabled)
    doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

    try:
        probe = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = "\n".join(p.get_text() for p in probe)
        probe.close()
    except Exception as e:
        PROCESS_LOG.append(f"open failed: {e}")
        return pdf_bytes, Mapping(file_sha256=doc_hash, engine_version="1.0.0"), 0, "", ""

    if mapping is None:
        mapping = Mapping(file_sha256=doc_hash, engine_version="1.0.0")

    cnt: dict = {}
    for e in mapping.entities:
        cnt[e.category] = cnt.get(e.category, 0) + 1

    for _st, _en, cat, val in detect(full_text, enabled):
        hit = None
        for e in mapping.entities:
            if e.category != cat:
                continue
            if e.original_value == val or (
                cat == "PERSON" and person_key(e.original_value) == person_key(val)
            ):
                hit = e
                break
        if hit:
            hit.occurrences += 1
        else:
            cnt[cat] = cnt.get(cat, 0) + 1
            mapping.add(MappingEntity(
                category=cat,
                original_value=val,
                placeholder=f"[{by_code(cat).placeholder_prefix}_{cnt[cat]}]",
                occurrences=1,
                color=get_color(cat),
            ))

    if not full_text.strip():
        return pdf_bytes, mapping, 0, "", ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = 0
    for page in doc:
        for ent in mapping.entities:
            if ent.category not in enabled:
                continue
            needle = ent.original_value
            if not needle or not needle.strip():
                continue
            try:
                rects = page.search_for(needle)
            except Exception as e:
                PROCESS_LOG.append(f"search_for({needle!r}): {e}")
                continue
            for r in rects:
                page.add_redact_annot(r, text=ent.placeholder,
                                      fill=(0, 0, 0), text_color=(1, 1, 1), fontsize=9)
                total += 1
        try:
            page.apply_redactions()
        except Exception as e:
            PROCESS_LOG.append(f"apply_redactions: {e}")

    out = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    try:
        pd = fitz.open(stream=out, filetype="pdf")
        preview = "\n".join(p.get_text() for p in pd)
        img = ""
        if len(pd) > 0:
            pix = pd[0].get_pixmap(dpi=120)
            img = "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii")
        pd.close()
    except Exception:
        preview, img = full_text, ""

    return out, mapping, total, preview, img


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        d = fitz.open(stream=pdf_bytes, filetype="pdf")
        t = "\n".join(p.get_text() for p in d)
        d.close()
        return t
    except Exception:
        return ""