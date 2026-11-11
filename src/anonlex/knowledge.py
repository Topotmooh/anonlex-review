"""База знаний сторон: ТОЧНЫЙ поиск с правильными границами для кириллицы."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple

# Строгие границы для кириллицы (заменяют \b, который не работает с кириллицей)
LB = r"(?<![А-Яа-яA-Za-z0-9_])"
RB = r"(?![А-Яа-яA-Za-z0-9_])"

_BLOCK_HEADINGS = ("реквизит", "signatures", "подписи сторон")

_COMPANY_RE = re.compile(
    LB + r"(?:ООО|АО|ЗАО|ПАО|ОАО|"
    r"Общество\s+с\s+ограниченной\s+ответственностью|"
    r"Акционерное\s+общество|"
    r"Закрытое\s+акционерное\s+общество|"
    r"Открытое\s+акционерное\s+общество|"
    r"Публичное\s+акционерное\s+общество)\s+"
    r"(?:[А-ЯЁ][А-Яа-яё-]+\s+)?"
    r"[«\"][^»\"]+[»\"]" + RB,
    re.IGNORECASE,
)
_PERSON_FULL_RE = re.compile(LB + r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,}" + RB)
_PERSON_UPPER_RE = re.compile(LB + r"[А-ЯЁ]{2,}(?:\s+[А-ЯЁ]{2,}){2,}" + RB)
_PERSON_SHORT_RE = re.compile(LB + r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\." + RB)
_PERSON_INITIALS_FIRST_RE = re.compile(LB + r"[А-ЯЁ]\.[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+" + RB)
_PERSON_CONTEXT_RE = re.compile(
    r"(?:в\s+лице|действующ(?:его|ий)|подписавш(?:его|ий))"
    r"\s+(?:[А-ЯЁа-яё]+\s+)+?"
    r"([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,})",
    re.IGNORECASE,
)

# ВАЖНО: НИКАКИХ пробелов в стоп-словах!
_PERSON_STOP_WORDS = frozenset({
    "реквизиты", "сторон", "предмет", "договора", "порядок", "сроки",
    "проведения", "оценки", "исполнитель", "оценщики", "оценщиках",
    "оценщик", "стоимость", "услуг", "расчетов", "ответственность",
    "заказчика", "права", "обязанности", "конфиденциальная", "информация",
    "приложения", "настоящему", "договору", "подписи", "адрес",
    "местоположение", "банковские", "электронный", "сторона", "заказчик",
    "комиссия", "закон", "федеральный", "российской", "федерации",
    "деятельности", "должность", "первого", "президента", "управление",
    "сведения", "делам", "образования",
})
_TITLE_WORDS = frozenset({
    "директор", "директора", "директору", "директором",
    "генеральный", "генерального", "генеральному", "генеральным",
    "заместитель", "заместителя", "заместителю", "заместителем",
    "председатель", "председателя", "председателю", "председателем",
    "представитель", "представителя", "представителю", "представителем",
    "покупатель", "покупателя", "поставщик", "поставщика",
    "заказчик", "заказчика", "исполнитель", "исполнителя",
    "действующего", "действующий", "подписавшего", "подписавший",
})
_OCR_LABELS = frozenset({
    "оценщики", "исполнитель", "заказчик", "подпись", "подписавший",
    "директор", "заместитель", "председатель", "представитель",
})


@dataclass(frozen=True)
class KnowledgeEntity:
    category: str
    value: str
    key: str


def _normalize_person(value: str) -> str:
    """Унифицирует формы: 'Иванов Иван Иванович' == 'Иванов И.И.' == 'И.И. Иванов'."""
    tokens = [t for t in value.replace(".", " ").split() if t]
    if not tokens:
        return value.lower()
    is_init = lambda t: len(t) == 1
    # Фамилия И.О.
    if len(tokens) >= 3 and not is_init(tokens[0]):
        return f"{tokens[0].lower()} {tokens[1][0].lower()}.{tokens[2][0].lower()}."
    # И.О. Фамилия
    if len(tokens) >= 2 and not is_init(tokens[-1]) and all(is_init(t) for t in tokens[:-1]):
        return f"{tokens[-1].lower()} " + "".join(f"{t[0].lower()}." for t in tokens[:-1])
    # Фамилия И.О.
    if len(tokens) >= 2 and not is_init(tokens[0]) and all(is_init(t) for t in tokens[1:]):
        return f"{tokens[0].lower()} " + "".join(f"{t[0].lower()}." for t in tokens[1:])
    return " ".join(t.lower() for t in tokens)


def _normalize_company(value: str) -> str:
    return value.lower().replace("«", "").replace("»", "").replace('"', "").replace("'", "")


def _clean_person(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    text = re.split(r"\b(?:паспорт|инн|снилс|адрес|телефон|email)\b", text, flags=re.IGNORECASE)[0].strip()
    tokens = text.split()
    # Срезаем OCR-префиксы и стоп-слова/должности слева
    while tokens and (
        tokens[0].lower() in _PERSON_STOP_WORDS
        or tokens[0].lower() in _TITLE_WORDS
        or tokens[0].lower() in _OCR_LABELS
    ):
        tokens.pop(0)
    return " ".join(tokens)


def _person_ok(value: str) -> bool:
    tokens = value.split()
    if len(tokens) < 2:
        return False
    return not any(t.lower() in _PERSON_STOP_WORDS or t.lower() in _TITLE_WORDS for t in tokens)


def _strip_titles(text: str) -> str:
    return _clean_person(text)


def _is_person_stop_word(word: str) -> bool:
    return word.lower() in _PERSON_STOP_WORDS


def _contains_title_word(value: str) -> bool:
    return any(w.lower() in _TITLE_WORDS for w in value.split())


def find_requisites_block(texts: Sequence[str]) -> Tuple[int, int]:
    for idx, text in enumerate(texts):
        if text.strip().lower().startswith(_BLOCK_HEADINGS):
            return idx, len(texts)
    return max(0, len(texts) * 3 // 4), len(texts)


def _collect(text: str, entities: List[KnowledgeEntity], seen: set) -> None:
    for regex in (_PERSON_FULL_RE, _PERSON_UPPER_RE, _PERSON_SHORT_RE, _PERSON_INITIALS_FIRST_RE):
        for match in regex.finditer(text):
            value = _clean_person(match.group(0))
            if not _person_ok(value):
                continue
            key = _normalize_person(value)
            if ("PERSON", key) not in seen:
                seen.add(("PERSON", key))
                entities.append(KnowledgeEntity(category="PERSON", value=value, key=key))
    for match in _COMPANY_RE.finditer(text):
        raw = re.sub(r"\s+", " ", match.group(0)).strip()
        key = _normalize_company(raw)
        if ("COMPANY", key) not in seen:
            seen.add(("COMPANY", key))
            entities.append(KnowledgeEntity(category="COMPANY", value=raw, key=key))


def extract_entities(block_texts: Sequence[str]) -> List[KnowledgeEntity]:
    entities: List[KnowledgeEntity] = []
    seen: set = set()
    for text in block_texts:
        _collect(text, entities, seen)
    return entities


def extract_entities_full_text(full_text: str) -> List[KnowledgeEntity]:
    entities: List[KnowledgeEntity] = []
    seen: set = set()
    for match in _PERSON_CONTEXT_RE.finditer(full_text):
        value = _clean_person(match.group(1))
        if _person_ok(value):
            key = _normalize_person(value)
            if ("PERSON", key) not in seen:
                seen.add(("PERSON", key))
                entities.append(KnowledgeEntity(category="PERSON", value=value, key=key))
    _collect(full_text, entities, seen)
    return entities


def forms_of(entity: KnowledgeEntity) -> List[str]:
    forms = [entity.value]
    if entity.category == "PERSON":
        tokens = entity.value.replace(".", " ").split()
        if len(tokens) >= 3:
            s, n, p = tokens[0], tokens[1], tokens[2]
            forms += [f"{s} {n[0]}.{p[0]}.", s, f"{s} {n} {p}", entity.value.upper()]
        elif len(tokens) == 2:
            forms += [entity.value, tokens[0], entity.value.upper()]
    elif entity.category == "COMPANY":
        quoted = re.search(r'[«"]([^»"]+)[»"]', entity.value)
        qp = quoted.group(1) if quoted else ""
        up = entity.value.upper()
        opf = None
        if "ООО" in up or "ОБЩЕСТВО С ОГРАНИЧЕННОЙ" in up:
            opf = ("ООО", "Общество с ограниченной ответственностью")
        elif "ПАО" in up:
            opf = ("ПАО", "Публичное акционерное общество")
        elif "ЗАО" in up:
            opf = ("ЗАО", "Закрытое акционерное общество")
        elif "ОАО" in up:
            opf = ("ОАО", "Открытое акционерное общество")
        elif "АО" in up:
            opf = ("АО", "Акционерное общество")
        forms.append(entity.value.upper())
        if opf and qp:
            forms += [f"{opf[0]} «{qp}»", f"{opf[1]} «{qp}»"]
        if qp:
            forms.append(f"«{qp}»")
    return [f for f in dict.fromkeys(forms) if len(f) >= 2]


normalize_company = _normalize_company
normalize_person = _normalize_person