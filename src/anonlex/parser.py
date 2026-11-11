"""Разбор и сборка .docx средствами стандартной библиотеки (ADR-008).

Подход: ZIP-контейнер + xml.etree.ElementTree. Для каждого параграфа
строится virtualText (склейка текстов узлов <w:t>) и карта узлов,
позволяющая применять правки в координатах virtualText без потери
форматирования (<w:rPr> не затрагивается).

Ограничения спринта 2 (ADR-009):
- в virtualText не включаются <w:tab>/<w:br>;
- обрабатывается только word/document.xml (остальные part — спринт 3).
"""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MAIN_PART = "word/document.xml"

_XMLNS_RE = re.compile(rb'xmlns:(\w+)="([^"]+)"')


@dataclass
class Edit:
    """Правка в координатах virtualText: интервал [start, end) заменить на new_text."""

    start: int
    end: int
    new_text: str


@dataclass
class TextNode:
    """Узел <w:t> и его диапазон в virtualText параграфа."""

    element: ET.Element
    start: int
    text: str

    @property
    def end(self) -> int:
        return self.start + len(self.text)


@dataclass
class Paragraph:
    """Параграф <w:p>: virtualText и карта текстовых узлов."""

    virtual_text: str
    nodes: List[TextNode] = field(default_factory=list)


def register_namespaces(raw: bytes) -> None:
    """Регистрирует префиксы xmlns из исходного part.

    Без этого ElementTree переименовал бы префиксы в ns0/ns1
    при сериализации, и Word мог бы отказаться читать файл.
    """
    for prefix, uri in _XMLNS_RE.findall(raw):
        ET.register_namespace(prefix.decode(), uri.decode())


def read_part(data: bytes, name: str = MAIN_PART) -> ET.Element:
    """Читает XML-part из ZIP-контейнера .docx."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        raw = zf.read(name)
    register_namespaces(raw)
    return ET.fromstring(raw)


def iter_paragraphs(root: ET.Element) -> List[Paragraph]:
    """Строит список параграфов с virtualText и картой узлов <w:t>."""
    paragraphs: List[Paragraph] = []
    for p in root.iter(f"{W}p"):
        nodes: List[TextNode] = []
        offset = 0
        for t in p.iter(f"{W}t"):
            text = t.text or ""
            nodes.append(TextNode(element=t, start=offset, text=text))
            offset += len(text)
        paragraphs.append(
            Paragraph(virtual_text="".join(n.text for n in nodes), nodes=nodes)
        )
    return paragraphs


def apply_edits(paragraph: Paragraph, edits: Sequence[Edit]) -> None:
    """Применяет непересекающиеся правки к текстовым узлам параграфа.

    Текст замены кладётся в первый затронутый узел, из остальных
    затронутых узлов перекрытый фрагмент вырезается. Меняются только
    текстовые узлы, поэтому форматирование (<w:rPr>) сохраняется.
    """
    ordered = sorted(edits, key=lambda e: e.start)
    for left, right in zip(ordered, ordered[1:]):
        if right.start < left.end:
            raise ValueError("Пересекающиеся правки недопустимы")

    starts = [n.start for n in paragraph.nodes]
    ops: Dict[int, List[Tuple[int, int, str]]] = {}

    for edit in ordered:
        first_idx = max(bisect_right(starts, edit.start) - 1, 0)
        inserted = False
        for idx in range(first_idx, len(paragraph.nodes)):
            node = paragraph.nodes[idx]
            if node.end <= edit.start:
                continue
            if node.start >= edit.end:
                break
            lo = max(edit.start - node.start, 0)
            hi = min(edit.end - node.start, len(node.text))
            repl = "" if inserted else edit.new_text
            inserted = True
            ops.setdefault(idx, []).append((lo, hi, repl))

    for idx, node_ops in ops.items():
        node = paragraph.nodes[idx]
        text = node.text
        for lo, hi, repl in sorted(node_ops, key=lambda op: op[0], reverse=True):
            text = text[:lo] + repl + text[hi:]
        node.element.text = text
        if text and text != text.strip():
            node.element.set(XML_SPACE, "preserve")


def serialize_part(root: ET.Element) -> bytes:
    """Сериализует part с XML-декларацией в формате исходного .docx."""
    body = ET.tostring(root, encoding="unicode")
    header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    return (header + body).encode("utf-8")


def rebuild_zip(original: bytes, replaced: Dict[str, bytes]) -> bytes:
    """Собирает новый .docx: указанные part заменяются, остальные байты сохраняются."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(
        out, "w", zipfile.ZIP_DEFLATED
    ) as dst:
        for item in src.infolist():
            payload = replaced.get(item.filename, src.read(item.filename))
            dst.writestr(item, payload)
    return out.getvalue()