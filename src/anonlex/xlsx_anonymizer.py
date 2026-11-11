"""Анонимизация XLSX-файлов (Excel).

ИСПРАВЛЕНИЕ: обработка числовых ячеек, которые ранее пропускались 
из-за строгой проверки isinstance(cell.value, str).
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import openpyxl

from anonlex import __version__
from anonlex.categories import by_code, default_enabled_codes, get_color
from anonlex.finder import Span, find_spans
from anonlex.knowledge import KnowledgeEntity, extract_entities_full_text, forms_of
from anonlex.mapping import Mapping, MappingEntity
from anonlex.org_dict import find_org_spans

_KNOWLEDGE_CATEGORIES = frozenset({"PERSON", "COMPANY"})
REDACTION_BLOCK = "█"

# Свойства книги (docProps/core.xml) открывают автора и тему файла —
# это те же ПДн, что и текст ячеек (аналог FR-08 для DOCX).
_SCRUB_TO_ANONYMIZED = ("creator", "lastModifiedBy")
_SCRUB_TO_EMPTY = ("title", "subject", "description", "keywords", "category", "comments", "contentStatus")


def _scrub_properties(wb: openpyxl.Workbook) -> None:
    """Обезличивает свойства книги: автор, последний редактор, заголовок."""
    props = wb.properties
    for field_name in _SCRUB_TO_ANONYMIZED:
        if getattr(props, field_name, None):
            setattr(props, field_name, "Anonymized")
    for field_name in _SCRUB_TO_EMPTY:
        if hasattr(props, field_name):
            setattr(props, field_name, "")



@dataclass
class XlsxAnonymizeResult:
    """Результат анонимизации XLSX."""
    docx: bytes
    mapping: Mapping
    spans: int
    preview: str = ""


def _collect_text(wb: openpyxl.Workbook) -> List[str]:
    """Собирает текст из всех ячеек всех листов для поиска."""
    texts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    texts.append(str(cell.value))
    return texts


def _resolve(spans: List[Span]) -> List[Span]:
    """Оставляет непересекающиеся спаны: раньше начавшийся, затем длинный."""
    ordered = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    kept: List[Span] = []
    last_end = -1
    for span in ordered:
        if span.start >= last_end:
            kept.append(span)
            last_end = span.end
    return kept


def _needles(entity: MappingEntity) -> List[str]:
    """Все формы сущности для поиска в ячейках."""
    if entity.category in _KNOWLEDGE_CATEGORIES:
        return [
            form
            for form in forms_of(
                KnowledgeEntity(
                    category=entity.category,
                    value=entity.original_value,
                    key=entity.original_value.casefold(),
                )
            )
            if form
        ]
    return [entity.original_value] if entity.original_value else []


def _find_knowledge_spans(
    text: str,
    knowledge: List[KnowledgeEntity],
    enabled_set: Set[str],
) -> List[Span]:
    """Ищет известные формы ФИО/компаний в тексте ячейки."""
    spans: List[Span] = []
    for entity in knowledge:
        if entity.category not in enabled_set:
            continue
        for form in forms_of(entity):
            pattern = r"(?<!\w)" + re.escape(form) + r"(?!\w)"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                spans.append(Span(match.start(), match.end(), entity.category, match.group(0)))
    return spans


def _collect_spans(
    text: str,
    knowledge: List[KnowledgeEntity],
    enabled_set: Set[str],
) -> List[Span]:
    """Все спаны текста: regex-движок + knowledge-слой + словарь организации."""
    return (
        list(find_spans(text, enabled_set))
        + _find_knowledge_spans(text, knowledge, enabled_set)
        + find_org_spans(text, enabled_set)
    )


def anonymize_xlsx(
    xlsx_bytes: bytes,
    enabled: Optional[Set[str]] = None,
    redaction_mode: str = "block",
) -> XlsxAnonymizeResult:
    """Анонимизирует XLSX-файл, включая числовые ячейки и ФИО/компании."""
    if redaction_mode not in {"block", "placeholder"}:
        raise ValueError(f"Недопустимый режим redaction: {redaction_mode}")
    enabled_set = set(enabled) if enabled is not None else default_enabled_codes()

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    full_text = "\n".join(_collect_text(wb))

    knowledge = extract_entities_full_text(full_text)
    lookup: Dict[Tuple[str, str], str] = {}
    for entity in knowledge:
        for form in forms_of(entity):
            lookup[(entity.category, form.casefold())] = entity.key

    spans = _resolve(_collect_spans(full_text, knowledge, enabled_set))

    registry: Dict[Tuple[str, str], List] = {}
    for span in spans:
        if span.category in _KNOWLEDGE_CATEGORIES:
            key = lookup.get((span.category, span.value.casefold()), span.value.casefold())
            canonical = span.value
            for entity in knowledge:
                if entity.category == span.category and entity.key == key:
                    canonical = entity.value
                    break
        else:
            key = span.value.casefold()
            canonical = span.value

        token = (span.category, key)
        if token not in registry:
            index = sum(1 for cat, _ in registry if cat == span.category) + 1
            placeholder = f"[{by_code(span.category).placeholder_prefix}_{index}]"
            registry[token] = [placeholder, canonical, 0]
        registry[token][2] += 1

    mapping = Mapping(
        file_sha256=hashlib.sha256(xlsx_bytes).hexdigest(),
        engine_version=__version__,
    )
    for (category, _key), (placeholder, canonical, occurrences) in registry.items():
        mapping.add(
            MappingEntity(
                category=category,
                original_value=canonical,
                placeholder=placeholder,
                occurrences=occurrences,
                color=get_color(category),
            )
        )

    total_spans = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue

                cell_value = str(cell.value).strip()
                if not cell_value:
                    continue

                cell_spans = _resolve(_collect_spans(cell_value, knowledge, enabled_set))
                if not cell_spans:
                    continue

                new_value = cell_value
                for span in sorted(cell_spans, key=lambda s: s.start, reverse=True):
                    if span.category in _KNOWLEDGE_CATEGORIES:
                        key = lookup.get(
                            (span.category, span.value.casefold()), span.value.casefold()
                        )
                    else:
                        key = span.value.casefold()
                    placeholder = registry.get((span.category, key), [None])[0]
                    replacement = (
                        REDACTION_BLOCK
                        if redaction_mode == "block" or not placeholder
                        else placeholder
                    )
                    new_value = new_value[: span.start] + replacement + new_value[span.end :]
                cell.value = new_value
                total_spans += len(cell_spans)

    _scrub_properties(wb)
    output_buf = io.BytesIO()
    wb.save(output_buf)

    wb.close()
    output_bytes = output_buf.getvalue()

    preview = full_text
    for entity in mapping.entities:
        for needle in _needles(entity):
            preview = re.sub(re.escape(needle), entity.placeholder, preview, flags=re.IGNORECASE)

    return XlsxAnonymizeResult(
        docx=output_bytes,
        mapping=mapping,
        spans=total_spans,
        preview=preview,
    )