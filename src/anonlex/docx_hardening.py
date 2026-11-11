"""Второй проход: санитизация всех XML-частей DOCX (FR-06..FR-10)."""
from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET

from anonlex.categories import by_code, get_color
from anonlex.mapping import Mapping, MappingEntity
from anonlex.pii_core import detect, person_key

_META = {"creator", "lastModifiedBy", "Company", "Manager"}


def _local(t: str) -> str:
    return t.rsplit("}", 1)[-1]


def _counters(mapping: Mapping) -> dict:
    c: dict = {}
    for e in mapping.entities:
        c[e.category] = c.get(e.category, 0) + 1
    return c


def _ensure(mapping: Mapping, cnt: dict, cat: str, val: str) -> MappingEntity:
    for e in mapping.entities:
        if e.category != cat:
            continue
        if e.original_value == val:
            return e
        if cat == "PERSON" and person_key(e.original_value) == person_key(val):
            return e
    cnt[cat] = cnt.get(cat, 0) + 1
    ent = MappingEntity(
        category=cat,
        original_value=val,
        placeholder=f"[{by_code(cat).placeholder_prefix}_{cnt[cat]}]",
        occurrences=1,
        color=get_color(cat),
    )
    mapping.add(ent)
    return ent


def scrub(text: str, mapping: Mapping, cnt: dict, enabled, mode: str):
    if not text or not text.strip():
        return text, False
    changed = False
    for e in sorted(mapping.entities, key=lambda x: -len(x.original_value)):
        v = e.original_value
        if v and v in text:
            text = text.replace(v, e.placeholder if mode == "placeholder" else "█" * len(v))
            changed = True
    for st, en, cat, val in detect(text, enabled):
        if not val or val not in text:
            continue
        e = _ensure(mapping, cnt, cat, val)
        text = text.replace(val, e.placeholder if mode == "placeholder" else "█" * len(val))
        changed = True
    return text, changed


def harden_docx(docx_bytes: bytes, mapping: Mapping, enabled,
                redaction_mode: str = "placeholder") -> bytes:
    cnt = _counters(mapping)
    repl: dict = {}

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".xml"):
                continue
            try:
                root = ET.fromstring(zf.read(name))
            except Exception:
                continue
            changed = False
            for el in root.iter():
                tag = _local(el.tag)

                if tag == "delText":
                    if el.text:
                        el.text = ""
                        changed = True
                    continue

                if tag in ("ins", "del", "comment"):
                    for a in list(el.attrib):
                        if _local(a) in ("author", "initials") and el.attrib[a]:
                            el.set(a, "Anonymized")
                            changed = True

                if tag in ("docPr", "cNvPr"):
                    for a in ("descr", "title"):
                        v = el.get(a)
                        if v:
                            nv, ch = scrub(v, mapping, cnt, enabled, redaction_mode)
                            if ch:
                                el.set(a, nv)
                                changed = True

                if tag in ("t", "instrText") and el.text:
                    nv, ch = scrub(el.text, mapping, cnt, enabled, redaction_mode)
                    if ch:
                        el.text = nv
                        changed = True

                if tag in _META and el.text:
                    nv, ch = scrub(el.text, mapping, cnt, enabled, redaction_mode)
                    el.text = nv if ch else "Anonymized"
                    changed = True

            if changed:
                repl[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    if repl:
        from anonlex.parser import rebuild_zip
        docx_bytes = rebuild_zip(docx_bytes, repl)
    return docx_bytes