"""Самодостаточная детекция ПДн. Не зависит от finder/knowledge."""
from __future__ import annotations

import re
from typing import List, Tuple

DL = r"(?<!\d)"
DR = r"(?!\d)"
WL = r"(?<![А-Яа-яЁёA-Za-z0-9_])"
WR = r"(?![А-Яа-яЁёA-Za-z0-9_])"

Found = Tuple[int, int, str, str]  # start, end, category, value


def _d(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def ok_inn(v: str) -> bool:
    d = _d(v)
    if len(d) == 10:
        w = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        return sum(int(d[i]) * w[i] for i in range(9)) % 11 % 10 == int(d[9])
    if len(d) == 12:
        w1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        w2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        return (sum(int(d[i]) * w1[i] for i in range(10)) % 11 % 10 == int(d[10])
                and sum(int(d[i]) * w2[i] for i in range(11)) % 11 % 10 == int(d[11]))
    return False


def ok_ogrn(v: str) -> bool:
    d = _d(v)
    if len(d) == 13:
        return int(d[:12]) % 11 % 10 == int(d[12])
    if len(d) == 15:
        return int(d[:14]) % 13 % 10 == int(d[14])
    return False


def ok_passport(v: str) -> bool:
    d = _d(v)
    return len(d) == 10 and d[:4] != "0000" and d[4:] != "000000"


_RE_INN = re.compile(DL + r"\d{12}" + DR + r"|" + DL + r"\d{10}" + DR)
_RE_OGRN = re.compile(DL + r"\d{15}" + DR + r"|" + DL + r"\d{13}" + DR)
_RE_BIK = re.compile(DL + r"04\d{7}" + DR)
_RE_ACC = re.compile(DL + r"\d{20}" + DR)
_RE_KPP = re.compile(DL + r"\d{9}" + DR)
_RE_SNILS = re.compile(DL + r"\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2}" + DR)
_RE_PASS = re.compile(r"(?<!\d)(?:№\s*)?(?:\d{4}[\s-]?\d{6}|\d{2}[\s-]?\d{2}[\s-]?\d{6})(?!\d)")
_RE_CARD = re.compile(DL + r"(?:\d{4}[\s-]){3}\d{4}" + DR)
_RE_EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" + WR)
_RE_PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)")
_RE_IBAN = re.compile(WL + r"[A-Z]{2}\d{2}(?:[A-Z0-9]{4}){2,7}[A-Z0-9]{0,2}" + WR)
_RE_SWIFT = re.compile(WL + r"[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?" + WR)
_RE_DATE = re.compile(DL + r"\d{2}[./-]\d{2}[./-]\d{2,4}" + DR)
_RE_AMOUNT = re.compile(r"\d[\d\s]*(?:[.,]\d+)?\s*(?:рублей|руб\.|руб|копеек|коп\.)", re.I)
_RE_ADDR = re.compile(
    r"г\.\s*[А-ЯЁ][а-яё]+(?:\s*,\s*(?:ул\.|улица|пр\.|проспект|пер\.|переулок|пл\.|площадь)\s*[А-ЯЁа-яё\-]+)"
    r"(?:\s*,?\s*(?:д\.|дом|корп\.|к\.|оф\.|кв\.)\s*\d+[А-Яа-я]?)*", re.I)

_RE_P_FULL = re.compile(WL + r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,}" + WR)
_RE_P_UPPER = re.compile(WL + r"[А-ЯЁ]{2,}(?:\s+[А-ЯЁ]{2,}){2,}" + WR)
_RE_P_SHORT = re.compile(WL + r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\." + WR)
_RE_P_INIT = re.compile(WL + r"[А-ЯЁ]\.[А-ЯЁ]\.\s+[А-ЯЁ][а-яё]+" + WR)
_RE_COMPANY = re.compile(
    WL + r"(?:ООО|ОАО|ЗАО|ПАО|АО|ИП|Общество\s+с\s+ограниченной\s+ответственностью)\s+"
    r"(?:[А-ЯЁ][А-Яа-яё-]+\s+)?[«\"][^»\"]+[»\"]", re.I)

_L_INN = re.compile(r"инн", re.I)
_L_PASS = re.compile(r"(?:паспорт|№)", re.I)
_L_IBAN = re.compile(r"iban", re.I)
_L_SWIFT = re.compile(r"swift", re.I)

_STOP = frozenset({
    "реквизиты", "сторон", "предмет", "договора", "порядок", "сроки", "проведения",
    "оценки", "стоимость", "услуг", "расчетов", "ответственность", "права",
    "обязанности", "конфиденциальная", "информация", "приложения", "настоящему",
    "договору", "подписи", "адрес", "местоположение", "банковские", "электронный",
    "сторона", "комиссия", "закон", "федеральный", "российской", "федерации",
    "деятельности", "должность", "управление", "сведения", "делам", "образования",
    "оценщиках", "оценщики", "оценщик", "исполнитель", "заказчик", "заказчика",
    "покупатель", "поставщик", "директор", "директора", "генеральный", "генерального",
    "заместитель", "председатель", "представитель", "подпись", "действующего",
})
_TITLES = frozenset({
    "директор", "директора", "директору", "директором", "генеральный", "генерального",
    "заместитель", "председатель", "представитель", "покупатель", "поставщик",
    "заказчик", "исполнитель", "оценщик", "оценщики", "подпись",
})


def person_key(value: str) -> str:
    """Ключ дедупликации: стебель фамилии + инициалы (Иванов/Иванова → один)."""
    t = [x for x in value.replace(".", " ").split() if x]
    if not t:
        return value.lower()
    if len(t[0]) == 1 and len(t) >= 3:
        surname, rest = t[-1], t[:-1]
    else:
        surname, rest = t[0], t[1:]
    stem = surname.lower()[:5]
    initials = "".join(x[0].lower() for x in rest if x)
    return f"{stem}|{initials}"


def _clean_person(raw: str, mstart: int):
    """Возвращает (start_offset, value) с отрезанными титулами/орглейблами."""
    tokens = raw.split()
    off = 0
    while tokens and tokens[0].lower().strip(":,") in _TITLES | _STOP:
        off += len(tokens[0]) + 1
        tokens.pop(0)
    val = " ".join(tokens)
    if len(tokens) < 2:
        return None
    if any(t.lower() in _STOP for t in tokens):
        return None
    return mstart + off, val


def _org_rules():
    try:
        from anonlex import org_dict as od
    except Exception:
        return []
    for name in ("rules", "get_rules", "load_rules", "all_rules", "_rules", "_RULES"):
        obj = getattr(od, name, None)
        if callable(obj):
            try:
                obj = obj()
            except Exception:
                continue
        if isinstance(obj, dict):
            return list(obj.values())
        if isinstance(obj, (list, tuple)):
            return list(obj)
    return []


def detect(text: str, enabled) -> List[Found]:
    """Все непересекающиеся ПДн-спаны. Приоритет: длинный/с меткой."""
    if not text or not text.strip():
        return []
    en = set(enabled or [])
    out: List[Tuple[int, int, str, str, int]] = []

    def add(cat, m, prio, val=None):
        if cat in en:
            out.append((m.start(), m.end(), cat, val if val is not None else m.group(0), prio))

    if "INN" in en:
        for m in _RE_INN.finditer(text):
            v = m.group(0)
            if ok_inn(v):
                lbl = bool(_L_INN.search(text[max(0, m.start() - 12):m.start()]))
                add("INN", m, 0 if lbl else 3)

    if "PASSPORT" in en:
        for m in _RE_PASS.finditer(text):
            v = m.group(0)
            if not ok_passport(v):
                continue
            sep = bool(re.search(r"\d[\s-]\d", v))
            near = bool(_L_PASS.search(text[max(0, m.start() - 25):m.start()])) or "№" in v
            if not sep and not near and _L_INN.search(text):
                continue
            add("PASSPORT", m, 0 if near else 2)

    for cat, rx, val_fn, prio in (
        ("OGRN", _RE_OGRN, ok_ogrn, 1),
        ("BIK", _RE_BIK, None, 1),
        ("ACCOUNT", _RE_ACC, None, 1),
        ("COR_ACCOUNT", _RE_ACC, None, 1),
        ("SNILS", _RE_SNILS, None, 1),
        ("CARD", _RE_CARD, None, 4),
        ("KPP", _RE_KPP, None, 5),
        ("EMAIL", _RE_EMAIL, None, 1),
        ("PHONE", _RE_PHONE, None, 1),
        ("DATE", _RE_DATE, None, 6),
        ("AMOUNT", _RE_AMOUNT, None, 6),
        ("ADDRESS", _RE_ADDR, None, 5),
    ):
        if cat not in en:
            continue
        for m in rx.finditer(text):
            if val_fn and not val_fn(m.group(0)):
                continue
            add(cat, m, prio)

    if "IBAN" in en:
        for m in _RE_IBAN.finditer(text):
            if _L_IBAN.search(text[max(0, m.start() - 20):m.start()]):
                add("IBAN", m, 1)
    if "SWIFT" in en:
        for m in _RE_SWIFT.finditer(text):
            if _L_SWIFT.search(text[max(0, m.start() - 20):m.start()]):
                add("SWIFT", m, 1)

    if "PERSON" in en:
        for rx in (_RE_P_FULL, _RE_P_UPPER, _RE_P_SHORT, _RE_P_INIT):
            for m in rx.finditer(text):
                cleaned = _clean_person(m.group(0), m.start())
                if cleaned:
                    st, val = cleaned
                    out.append((st, st + len(val), "PERSON", val, 2))

    if "COMPANY" in en:
        for m in _RE_COMPANY.finditer(text):
            add("COMPANY", m, 2)

    # ручные/выученные правила org_dict
    for r in _org_rules():
        get = r.get if isinstance(r, dict) else (lambda k, d=None: getattr(r, k, d))
        if get("disabled") is True or get("enabled") is False:
            continue
        cat = get("category") or "COMPANY"
        if cat not in en:
            continue
        pat = get("pattern") or get("regex") or get("re")
        if not pat:
            continue
        try:
            for m in re.compile(pat).finditer(text):
                out.append((m.start(), m.end(), cat, m.group(0), 0))
        except Exception:
            continue

    out.sort(key=lambda s: (s[0], -(s[1] - s[0]), s[4]))
    kept: List[Found] = []
    last = -1
    for st, en_, cat, val, _p in out:
        if st >= last:
            kept.append((st, en_, cat, val))
            last = en_
    return kept