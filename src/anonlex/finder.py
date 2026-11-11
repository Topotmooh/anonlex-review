"""Поиск ПДн в тексте: регулярные выражения + валидаторы контрольных сумм.

Границы:
  числовые  — (?<!\\d) ... (?!\\d)   ловит "ИНН7707083893", не ловит внутри длинных чисел
  текстовые — (?<![А-Яа-яA-Za-z0-9_]) ... корректно для кириллицы
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

DL = r"(?<!\d)"
DR = r"(?!\d)"
WL = r"(?<![А-Яа-яЁёA-Za-z0-9_])"
WR = r"(?![А-Яа-яЁёA-Za-z0-9_])"


@dataclass
class Span:
    start: int
    end: int
    category: str
    value: str
    priority: int = 5


# --------------------------------------------------------------------------
# Валидаторы
# --------------------------------------------------------------------------
def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _validate_inn(value: str) -> bool:
    d = _digits(value)
    if len(d) == 10:
        w = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        return sum(int(d[i]) * w[i] for i in range(9)) % 11 % 10 == int(d[9])
    if len(d) == 12:
        w1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        w2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        c1 = sum(int(d[i]) * w1[i] for i in range(10)) % 11 % 10
        c2 = sum(int(d[i]) * w2[i] for i in range(11)) % 11 % 10
        return c1 == int(d[10]) and c2 == int(d[11])
    return False


def _validate_ogrn(value: str) -> bool:
    d = _digits(value)
    if len(d) == 13:
        return int(d[:12]) % 11 % 10 == int(d[12])
    if len(d) == 15:
        return int(d[:14]) % 13 % 10 == int(d[14])
    return False


def _validate_bik(value: str) -> bool:
    d = _digits(value)
    return len(d) == 9 and d.startswith("04")


def _validate_account(value: str) -> bool:
    return len(_digits(value)) == 20


def _validate_passport(value: str) -> bool:
    d = _digits(value)
    return len(d) == 10 and d[:4] != "0000" and d[4:] != "000000"


def _validate_kpp(value: str) -> bool:
    c = re.sub(r"\s", "", value or "").upper()
    return bool(re.fullmatch(r"\d{4}[A-Z0-9]{2}\d{3}", c))


def _validate_snils(value: str) -> bool:
    d = _digits(value)
    return len(d) == 11 and d[:9] != "000000000"


def _validate_iban(value: str) -> bool:
    c = re.sub(r"[\s-]", "", value or "").upper()
    return bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", c))


def _validate_swift(value: str) -> bool:
    c = re.sub(r"\s", "", value or "").upper()
    return bool(re.fullmatch(r"[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?", c))


def _validate_card(value: str) -> bool:
    return 13 <= len(_digits(value)) <= 19


def _validate_ssn(value: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{2}-\d{4}", (value or "").strip()))


validate_inn = _validate_inn
validate_ogrn = _validate_ogrn
validate_bik = _validate_bik
validate_account = _validate_account
validate_passport = _validate_passport
validate_kpp = _validate_kpp
validate_snils = _validate_snils
validate_iban = _validate_iban
validate_swift = _validate_swift
validate_card = _validate_card


# --------------------------------------------------------------------------
# Паттерны
# --------------------------------------------------------------------------
_INN_RE = re.compile(DL + r"\d{12}" + DR + r"|" + DL + r"\d{10}" + DR)
_OGRN_RE = re.compile(DL + r"\d{15}" + DR + r"|" + DL + r"\d{13}" + DR)
_BIK_RE = re.compile(DL + r"04\d{7}" + DR)
_ACCOUNT_RE = re.compile(DL + r"\d{20}" + DR)
_KPP_RE = re.compile(DL + r"\d{4}[A-Z0-9]{2}\d{3}" + DR)
_SNILS_RE = re.compile(DL + r"\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2}" + DR)
_SSN_RE = re.compile(DL + r"\d{3}-\d{2}-\d{4}" + DR)
_PASSPORT_RE = re.compile(
    r"(?<!\d)(?:№\s*)?(?:\d{4}[\s-]?\d{6}|\d{2}[\s-]?\d{2}[\s-]?\d{6})(?!\d)"
)
_CARD_RE = re.compile(DL + r"(?:\d{4}[\s-]){3}\d{4}" + DR + r"|" + DL + r"\d{13,19}" + DR)
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" + WR
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)
_URL_RE = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+")
_NICKNAME_RE = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z0-9_]{3,32}(?![A-Za-z0-9_])")
_IP_RE = re.compile(
    r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)"
)
_MAC_RE = re.compile(WL + r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}" + WR)
_SWIFT_RE = re.compile(WL + r"[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?" + WR)
_IBAN_RE = re.compile(WL + r"[A-Z]{2}\d{2}(?:[A-Z0-9]{4}){2,7}[A-Z0-9]{0,2}" + WR)
_TAXID_RE = re.compile(WL + r"[A-Z]{2}\d{9}" + WR)
_CONTRACT_RE = re.compile(WL + r"[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9/\-]*\d[A-ZА-ЯЁ0-9/\-]*" + WR)
_PLATE_RE = re.compile(WL + r"[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}" + WR, re.IGNORECASE)
_VIN_RE = re.compile(WL + r"[A-HJ-NPR-Z0-9]{17}" + WR)
_PTS_RE = re.compile(DL + r"\d{2}[А-ЯЁ]{2}\d{6}" + DR, re.IGNORECASE)
_EGRN_RE = re.compile(DL + r"\d{2}:\d{2}:\d{6,7}:\d{1,4}" + DR)
_POLIS_RE = re.compile(DL + r"\d{16}" + DR)
_DATE_RE = re.compile(
    DL + r"(?:\d{2}[./-]\d{2}[./-]\d{2,4}"
    r"|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})" + DR,
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"\d[\d\s]*(?:[.,]\d+)?\s*(?:рублей|руб\.|руб|копеек|коп\.|коп|тысяч|миллионов)",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"г\.\s*[А-ЯЁ][а-яё]+(?:\s*,\s*(?:ул\.|улица|пр\.|проспект|пер\.|переулок|пл\.|площадь|наб\.)\s*[А-ЯЁа-яё\-]+)"
    r"(?:\s*,?\s*(?:д\.|дом|стр\.|корп\.|к\.|оф\.|кв\.)\s*\d+[А-Яа-я]?)*",
    re.IGNORECASE,
)

_L_INN = re.compile(r"инн", re.IGNORECASE)
_L_PASSPORT = re.compile(r"(?:паспорт|№)", re.IGNORECASE)
_L_SWIFT = re.compile(r"swift", re.IGNORECASE)
_L_IBAN = re.compile(r"iban", re.IGNORECASE)
_L_TAXID = re.compile(r"(?:tax\s*id|налоговый\s+id|инн\s+нерезидента)", re.IGNORECASE)
_L_CONTRACT = re.compile(r"(?:договор|контракт|соглашение|№)", re.IGNORECASE)
_L_CORR = re.compile(r"(?:кор(?:р|\.?)?\s*сч[её]т|correspondent)", re.IGNORECASE)
_L_LICENSE = re.compile(r"(?:лицензия|license|свидетельство|разрешение)", re.IGNORECASE)


def _before(text: str, start: int, window: int = 30) -> str:
    return text[max(0, start - window):start]


def _after(text: str, end: int, window: int = 10) -> str:
    return text[end:min(len(text), end + window)]


def _resolve(spans: List[Span]) -> List[Span]:
    ordered = sorted(spans, key=lambda s: (s.start, -(s.end - s.start), s.priority))
    kept: List[Span] = []
    last_end = -1
    for s in ordered:
        if s.start >= last_end:
            kept.append(s)
            last_end = s.end
    return kept


# --------------------------------------------------------------------------
# Основная функция
# --------------------------------------------------------------------------
def find_spans(text: str, enabled_categories: Optional[Set[str]] = None) -> List[Span]:
    if not text or not text.strip():
        return []

    if enabled_categories is None:
        enabled_categories = {
            "INN", "OGRN", "KPP", "BIK", "ACCOUNT", "PASSPORT", "SNILS",
            "CARD", "SSN", "EMAIL", "PHONE", "SWIFT", "IBAN", "CONTRACT",
        }
    enabled = set(enabled_categories)
    out: List[Span] = []

    if "INN" in enabled:
        for m in _INN_RE.finditer(text):
            v = m.group(0)
            if not _validate_inn(v):
                continue
            label = bool(_L_INN.search(_before(text, m.start(), 12)))
            out.append(Span(m.start(), m.end(), "INN", v, 0 if label else 3))

    if "PASSPORT" in enabled:
        for m in _PASSPORT_RE.finditer(text):
            v = m.group(0)
            if not _validate_passport(v):
                continue
            has_sep = bool(re.search(r"\d[\s-]\d", v))
            near = bool(_L_PASSPORT.search(_before(text, m.start(), 25))) or "№" in v
            # «голый» 10-значный номер в документе с меткой ИНН — это ИНН-кандидат
            if not has_sep and not near and _L_INN.search(text):
                continue
            out.append(Span(m.start(), m.end(), "PASSPORT", v, 0 if near else 2))

    if "OGRN" in enabled:
        for m in _OGRN_RE.finditer(text):
            v = m.group(0)
            if _validate_ogrn(v):
                out.append(Span(m.start(), m.end(), "OGRN", v, 1))

    if "BIK" in enabled:
        for m in _BIK_RE.finditer(text):
            v = m.group(0)
            if _validate_bik(v):
                out.append(Span(m.start(), m.end(), "BIK", v, 1))

    if "ACCOUNT" in enabled:
        for m in _ACCOUNT_RE.finditer(text):
            v = m.group(0)
            if _validate_account(v):
                out.append(Span(m.start(), m.end(), "ACCOUNT", v, 1))

    if "COR_ACCOUNT" in enabled:
        for m in _ACCOUNT_RE.finditer(text):
            if _L_CORR.search(_before(text, m.start(), 30)):
                out.append(Span(m.start(), m.end(), "COR_ACCOUNT", m.group(0), 1))

    if "KPP" in enabled:
        for m in _KPP_RE.finditer(text):
            v = m.group(0)
            if _validate_kpp(v):
                out.append(Span(m.start(), m.end(), "KPP", v, 4))

    if "SNILS" in enabled:
        for m in _SNILS_RE.finditer(text):
            v = m.group(0)
            if _validate_snils(v):
                out.append(Span(m.start(), m.end(), "SNILS", v, 1))

    if "CARD" in enabled:
        for m in _CARD_RE.finditer(text):
            v = m.group(0)
            if _validate_card(v):
                out.append(Span(m.start(), m.end(), "CARD", v, 4))

    if "SSN" in enabled:
        for m in _SSN_RE.finditer(text):
            v = m.group(0)
            if _validate_ssn(v):
                out.append(Span(m.start(), m.end(), "SSN", v, 1))

    if "EMAIL" in enabled:
        for m in _EMAIL_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "EMAIL", m.group(0), 1))

    if "PHONE" in enabled:
        for m in _PHONE_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "PHONE", m.group(0), 1))

    if "URL" in enabled:
        for m in _URL_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "URL", m.group(0), 2))

    if "NICKNAME" in enabled:
        for m in _NICKNAME_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "NICKNAME", m.group(0), 2))

    if "IP" in enabled:
        for m in _IP_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "IP", m.group(0), 2))

    if "MAC" in enabled:
        for m in _MAC_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "MAC", m.group(0), 2))

    if "SWIFT" in enabled:
        for m in _SWIFT_RE.finditer(text):
            v = m.group(0)
            if _validate_swift(v) and _L_SWIFT.search(_before(text, m.start(), 20)):
                out.append(Span(m.start(), m.end(), "SWIFT", v, 1))

    if "IBAN" in enabled:
        for m in _IBAN_RE.finditer(text):
            v = m.group(0)
            if _validate_iban(v) and _L_IBAN.search(_before(text, m.start(), 20)):
                out.append(Span(m.start(), m.end(), "IBAN", v, 1))

    if "TAXID" in enabled:
        for m in _TAXID_RE.finditer(text):
            if _L_TAXID.search(_before(text, m.start(), 30)):
                out.append(Span(m.start(), m.end(), "TAXID", m.group(0), 1))

    if "CONTRACT" in enabled:
        for m in _CONTRACT_RE.finditer(text):
            v = m.group(0)
            if not re.search(r"\d", v):
                continue
            ctx = _before(text, m.start(), 30) + " " + _after(text, m.end(), 5)
            if _L_CONTRACT.search(ctx):
                out.append(Span(m.start(), m.end(), "CONTRACT", v, 3))

    if "LICENSE" in enabled:
        for m in re.finditer(WL + r"[А-ЯЁA-Z0-9\-]{4,20}" + WR, text):
            if _L_LICENSE.search(_before(text, m.start(), 30)):
                out.append(Span(m.start(), m.end(), "LICENSE", m.group(0), 3))

    if "PLATE" in enabled:
        for m in _PLATE_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "PLATE", m.group(0), 3))

    if "VIN" in enabled:
        for m in _VIN_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "VIN", m.group(0), 3))

    if "PTS" in enabled:
        for m in _PTS_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "PTS", m.group(0), 3))

    if "EGRN" in enabled:
        for m in _EGRN_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "EGRN", m.group(0), 2))

    if "POLIS_OMS" in enabled:
        for m in _POLIS_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "POLIS_OMS", m.group(0), 4))

    if "DATE" in enabled:
        for m in _DATE_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "DATE", m.group(0), 6))

    if "AMOUNT" in enabled:
        for m in _AMOUNT_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "AMOUNT", m.group(0).strip(), 6))

    if "ADDRESS" in enabled:
        for m in _ADDRESS_RE.finditer(text):
            out.append(Span(m.start(), m.end(), "ADDRESS", m.group(0), 5))

    if "PERSON" in enabled or "COMPANY" in enabled:
        try:
            from anonlex.knowledge import extract_entities_full_text, forms_of

            for ent in extract_entities_full_text(text):
                if ent.category not in enabled:
                    continue
                forms = forms_of(ent) if ent.category == "PERSON" else [ent.value]
                for form in forms:
                    if not form or len(form) < 3:
                        continue
                    pat = re.compile(WL + re.escape(form) + WR)
                    for m in pat.finditer(text):
                        out.append(Span(m.start(), m.end(), ent.category, form, 2))
        except Exception:
            pass

    return _resolve(out)


# --------------------------------------------------------------------------
# Хелперы для тестов
# --------------------------------------------------------------------------
def _only(text: str, category: str) -> List[Span]:
    return [s for s in find_spans(text, {category}) if s.category == category]


def find_inn_in_text(text: str) -> List[Span]:
    return _only(text, "INN")


def find_invalid_inn_skipped(text: str) -> List[Span]:
    return _only(text, "INN")


def find_bik_in_text(text: str) -> List[Span]:
    return _only(text, "BIK")


def find_account_in_text(text: str) -> List[Span]:
    return _only(text, "ACCOUNT")


def find_email_in_text(text: str) -> List[Span]:
    return _only(text, "EMAIL")


def find_phone_in_text(text: str) -> List[Span]:
    return _only(text, "PHONE")


def find_passport_in_text(text: str) -> List[Span]:
    return _only(text, "PASSPORT")