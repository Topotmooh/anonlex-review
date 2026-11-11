"""Словарь организации: кастомные правила + встроенные правила + обучение (спринт 7.4.3)."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_DICT_PATH = Path(os.getenv("ORG_DICT_PATH", str(Path(__file__).parent.parent.parent / "server" / "org_dict.json")))
# RLock: кэш правил читает _load(), который может вызвать _save() (посев builtin-правил).
_LOCK = threading.RLock()
_RULES_CACHE: Optional[Tuple[Optional[Tuple[int, int]], List[Tuple[str, "re.Pattern[str]"]]]] = None


# Встроенные правила: закрывают типовые пропуски движка (спринт 7.4.3).
# Если в regex есть группа 1 — в спан попадает только она (без метки «ИНН» и т.п.).
BUILTIN_RULES: List[Dict] = [
    {
        "id": "builtin-fio-initials",
        "name": "ФИО в формате «Фамилия И.О.»",
        "category": "PERSON",
        "regex": r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.)\b",
    },
    {
        "id": "builtin-addr-city-street",
        "name": "Адрес: город + улица + дом",
        "category": "ADDRESS",
        "regex": r"\b((?:г|город)\.?\s+[А-ЯЁ][а-яё-]+,\s?(?:ул|улица|пр-т|проспект|тракт|пер|переулок|б-р|бульвар|мкр|стр|строение)\.?\s?[А-ЯЁа-яё0-9«»-]+,\s?(?:д|дом|стр|строение|корп|к)\.?\s?\d+(?:,\s?(?:кв|квартира)\.?\s?\d+)?)",
    },
    {
        "id": "builtin-addr-street",
        "name": "Адрес: улица + дом",
        "category": "ADDRESS",
        "regex": r"\b((?:ул|улица|тракт|пр-т|проспект|пер|переулок|б-р|бульвар|мкр)\.?\s+[А-ЯЁ][а-яё0-9«»-]+,\s?д\.?\s?\d+(?:,\s?кв\.?\s?\d+)?)",
    },
    {
        "id": "builtin-inn-ocr",
        "name": "ИНН (устойчив к пробелам OCR)",
        "category": "INN",
        "regex": r"\bИНН[:\s]*(\d(?:\s?\d){9,11})\b",
    },
    {
        "id": "builtin-ogrn-ocr",
        "name": "ОГРН/ОГРНИП (устойчив к пробелам OCR)",
        "category": "OGRN",
        "regex": r"\bОГРН(?:ИП)?[:\s]*(\d(?:\s?\d){12,14})\b",
    },
    {
        "id": "builtin-kpp-ocr",
        "name": "КПП (устойчив к пробелам OCR)",
        "category": "KPP",
        "regex": r"\bКПП[:\s]*(\d(?:\s?\d){8})\b",
    },
    {
        "id": "builtin-bik-ocr",
        "name": "БИК (устойчив к пробелам OCR)",
        "category": "BIK",
        "regex": r"\bБИК[:\s]*(\d(?:\s?\d){8})\b",
    },
    {
        "id": "builtin-account-long",
        "name": "Длинный номер счёта (20–25 цифр)",
        "category": "ACCOUNT",
        "regex": r"\b(\d{20,25})\b",
    },
    {
        "id": "builtin-account-labeled",
        "name": "р/с или к/с с номером",
        "category": "ACCOUNT",
        "regex": r"\b(?:р/с|к/с|расчётный счёт|расчетный счет)[:\s]*(\d(?:\s?\d){17,25})\b",
    },
]


def _load() -> Dict:
    data = None
    if _DICT_PATH.exists():
        try:
            data = json.loads(_DICT_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if data is None:
        data = {"rules": []}
    # Однократное добавление встроенных правил
    if not data.get("seeded"):
        existing = {r.get("id") for r in data.get("rules", [])}
        for rule in BUILTIN_RULES:
            if rule["id"] not in existing:
                data.setdefault("rules", []).append(dict(rule, enabled=True, source="builtin", created_at=0.0))
        data["seeded"] = True
        _save(data)
    return data


def _save(data: Dict) -> None:
    with _LOCK:
        _DICT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DICT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_rules() -> List[Dict]:
    return _load().get("rules", [])


def get_enabled_rules() -> List[Dict]:
    return [r for r in list_rules() if r.get("enabled", True)]


def _file_key() -> Optional[Tuple[int, int]]:
    try:
        stat = _DICT_PATH.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def invalidate_cache() -> None:
    """Сбрасывает кэш скомпилированных правил (после изменения словаря)."""
    global _RULES_CACHE
    with _LOCK:
        _RULES_CACHE = None


def compiled_rules() -> List[Tuple[str, "re.Pattern[str]"]]:
    """Включённые правила словаря с готовыми regex.

    Кэш держит скомпилированные patterns и сбрасывается по изменению файла или
    явно — пайплайн обращается к слою на каждый абзац, читать JSON каждый раз нельзя.
    """
    global _RULES_CACHE
    key = _file_key()
    with _LOCK:
        if _RULES_CACHE is not None and _RULES_CACHE[0] == key:
            return _RULES_CACHE[1]
        try:
            rules = [r for r in _load().get("rules", []) if r.get("enabled", True)]
        except Exception:
            # Словарь — дополнительный слой: он не должен ронять анонимизацию.
            rules = []
        compiled: List[Tuple[str, "re.Pattern[str]"]] = []
        for rule in rules:
            try:
                compiled.append((str(rule.get("category", "")), re.compile(rule.get("regex", ""))))
            except re.error:
                continue
        _RULES_CACHE = (key, compiled)
        return compiled



def add_rule(name: str, category: str, regex: str, source: str = "manual") -> Dict:
    re.compile(regex)
    rule = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "category": category,
        "regex": regex,
        "enabled": True,
        "source": source,
        "created_at": time.time(),
    }
    data = _load()
    data.setdefault("rules", []).append(rule)
    _save(data)
    invalidate_cache()
    return rule


def delete_rule(rule_id: str) -> bool:
    data = _load()
    before = len(data.get("rules", []))
    data["rules"] = [r for r in data.get("rules", []) if r.get("id") != rule_id]
    _save(data)
    invalidate_cache()
    return len(data["rules"]) < before


def toggle_rule(rule_id: str, enabled: bool) -> bool:
    data = _load()
    for r in data.get("rules", []):
        if r.get("id") == rule_id:
            r["enabled"] = enabled
            _save(data)
            invalidate_cache()
            return True
    return False


def learn_from_manual(category: str, value: str) -> Dict:
    """Запоминает ручную правку. Для ФИО — правилом по основам слов (ловит все падежи)."""
    data = _load()
    for r in data.get("rules", []):
        if r.get("source") == "learned" and r.get("category") == category and r.get("value") == value:
            return r

    if category == "PERSON":
        words = value.split()
        if 2 <= len(words) <= 3:
            parts = []
            for w in words:
                stem = w[:-2] if len(w) > 5 else w
                parts.append(re.escape(stem) + r"[а-яё]{0,4}")
            regex = r"\b" + r"\s+".join(parts) + r"\b"
        else:
            regex = r"(?<!\w)" + re.escape(value) + r"(?!\w)"
    else:
        regex = r"(?<!\w)" + re.escape(value) + r"(?!\w)"

    rule = {
        "id": uuid.uuid4().hex[:8],
        "name": f"Выучено: {value[:40]}",
        "category": category,
        "regex": regex,
        "value": value,
        "enabled": True,
        "source": "learned",
        "created_at": time.time(),
    }
    data.setdefault("rules", []).append(rule)
    _save(data)
    invalidate_cache()
    return rule


def find_org_spans(text: str, enabled_categories: set) -> List:
    """Применяет включённые правила словаря к тексту. Спан = группа 1, если она есть."""
    from anonlex.finder import Span

    out = []
    if not text:
        return out
    for category, rx in compiled_rules():
        if category not in enabled_categories:
            continue
        for m in rx.finditer(text):
            if m.groups():
                s, e, val = m.start(1), m.end(1), m.group(1)
            else:
                s, e, val = m.start(), m.end(), m.group(0)
            if val:
                out.append(Span(s, e, category, val))
    return out