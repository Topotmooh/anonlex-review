"""Синтетический корпус договоров с известными сущностями (серебряный стандарт).

Gold-разметка известна по построению: генератор сам знает, что вставил.
Корпус проверяет механику пайплайна; честные метрики на реальных договорах
с двумя разметчиками — отдельный этап (08_TASKS.md, спринт 4).
Ограничение: ФИО вставляются только в именительном падеже и сокращённой
форме; падежные формы — бэклог (09_MEMORY.md).
"""

from __future__ import annotations

import random
from typing import List, Tuple

from anonlex.knowledge import normalize_company, normalize_person
from anonlex.validators import validate_bik, validate_iban, validate_inn

COMPANIES = ("ООО «Ромашка»", "АО «Вектор»", "ООО «Гранит»", "ПАО «Заря»", "ООО «Технопарк»")
PERSONS = (
    "Иванов Иван Иванович",
    "Петрова Анна Сергеевна",
    "Сидоров Пётр Павлович",
    "Кузнецова Мария Олеговна",
    "Смирнов Алексей Викторович",
)


def _digits(rng: random.Random, count: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(count))


def random_inn(rng, length: int = 10) -> str:
    """Валидный ИНН без перебора: контрольная цифра = sum % 11 % 10."""
    w10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    w11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    w12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

    def ctrl(digits: str, weights) -> str:
        return str(sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10)

    if length == 12:
        base = "".join(str(rng.randint(0, 9)) for _ in range(10))
        d11 = ctrl(base, w11)
        d12 = ctrl(base + d11, w12)
        return base + d11 + d12

    base = "".join(str(rng.randint(0, 9)) for _ in range(9))
    return base + ctrl(base, w10)


def random_iban(rng: random.Random) -> str:
    """IBAN с валидной контрольной суммой по модулю 97 (ISO 13616)."""
    bban = _digits(rng, 20)
    digits = "".join(str(int(ch, 36)) for ch in bban + "RU00")
    check = 98 - int(digits) % 97
    return f"RU{check:02d}{bban}"


def random_bik(rng: random.Random) -> str:
    while True:
        candidate = "04" + _digits(rng, 7)
        if validate_bik(candidate):
            return candidate


def random_account(rng: random.Random) -> str:
    return rng.choice(("40702", "40810", "30101")) + _digits(rng, 15)


def random_swift(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    bank = "".join(rng.choice(letters) for _ in range(4))
    loc = "".join(rng.choice(letters) for _ in range(2))
    return f"{bank}RU{loc}"


def random_phone(rng: random.Random) -> str:
    return f"+7 {_digits(rng, 3)} {_digits(rng, 3)}-{_digits(rng, 2)}-{_digits(rng, 2)}"


def random_passport(rng: random.Random) -> str:
    return f"{_digits(rng, 4)} {_digits(rng, 6)}"


def _short(full: str) -> str:
    tokens = full.split()
    return f"{tokens[0]} {tokens[1][0]}.{tokens[2][0]}."


def build_document(rng: random.Random, index: int) -> Tuple[List[List[str]], List[Tuple[str, str]]]:
    """Собирает параграфы договора и gold-разметку как список (category, key)."""
    company1, company2 = rng.sample(COMPANIES, 2)
    person1, person2 = rng.sample(PERSONS, 2)
    inn1, inn2 = random_inn(rng), random_inn(rng)
    kpp = "77" + _digits(rng, 7)
    account, bik = random_account(rng), random_bik(rng)
    swift, iban = random_swift(rng), random_iban(rng)
    email = f"supply{index}@company.ru"
    phone, passport = random_phone(rng), random_passport(rng)

    paragraphs = [
        [f"ДОГОВОР ПОСТАВКИ № {index}/2026"],
        ["г. Краснодар, 08 октября 2026 г."],
        [f"{company1}, ИНН {inn1}, КПП {kpp}, далее «Поставщик»,"],
        [f"и {company2}, ИНН {inn2}, далее «Покупатель», заключили договор:"],
        ["1. Поставщик передаёт товар по спецификации."],
        [f"2. Оплата: р/с {account}, БИК {bik}, SWIFT: {swift}, IBAN: {iban}."],
        [f"3. Контакты: {email}, тел {phone}."],
        ["РЕКВИЗИТЫ СТОРОН"],
        [f"Поставщик: {company1}, ИНН {inn1}"],
        [f"Директор {person1}"],
        [f"Покупатель: {company2}, ИНН {inn2}"],
        [f"Генеральный директор {person2}"],
        [f"Паспорт директора: {passport}"],
        [f"Подписи сторон: {_short(person1)}, {_short(person2)}"],
    ]
    gold = [
        ("COMPANY", normalize_company(company1)),
        ("COMPANY", normalize_company(company2)),
        ("PERSON", normalize_person(person1)),
        ("PERSON", normalize_person(person2)),
        ("INN", inn1),
        ("INN", inn2),
        ("KPP", kpp),
        ("ACCOUNT", account),
        ("BIK", bik),
        ("SWIFT", swift.casefold()),
        ("IBAN", iban.casefold()),
        ("EMAIL", email.casefold()),
        ("PHONE", phone),
        ("PASSPORT", passport),
    ]
    return paragraphs, gold