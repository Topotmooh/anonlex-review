"""Валидаторы ПДн."""
from __future__ import annotations
import re

def validate_inn(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        weights = (2, 4, 10, 3, 5, 9, 4, 6, 8, 0)
        s = sum(int(digits[i]) * weights[i] for i in range(10))
        return s % 11 % 10 == 0
    if len(digits) == 12:
        w11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0, 0)
        w12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0)
        s11 = sum(int(digits[i]) * w11[i] for i in range(12))
        s12 = sum(int(digits[i]) * w12[i] for i in range(12))
        return int(digits[10]) == s11 % 11 % 10 and int(digits[11]) == s12 % 11 % 10
    return False

def validate_bik(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) == 9 and digits.startswith("04")

def validate_account(value: str) -> bool:
    return len(re.sub(r"\D", "", value)) == 20

def validate_passport(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) == 10 and digits[:4] != "0000" and digits[4:] != "000000"

def validate_ogrn(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 13:
        return int(digits[:-1]) % 11 % 10 == int(digits[-1])
    if len(digits) == 15:
        return int(digits[:-1]) % 13 % 10 == int(digits[-1])
    return False

def validate_kpp(value: str) -> bool:
    return len(re.sub(r"\D", "", value)) == 9

def validate_snils(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11:
        return False
    base = digits[:9]
    control = int(digits[9:])
    weights = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    s = sum(int(base[i]) * weights[i] for i in range(9))
    if s < 100:
        return s == control
    if s in (100, 101):
        return control == 0
    return (s % 101) % 100 == control or ((s % 101) == 100 and control == 0)

def validate_iban(value: str) -> bool:
    """Простая валидация IBAN: 2 буквы + 2 цифры + 10-30 алфавитно-цифровых."""
    cleaned = re.sub(r"\s+", "", value).upper()
    if len(cleaned) < 14 or len(cleaned) > 34:
        return False
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", cleaned):
        return False
    return True

# Алиасы для совместимости
_validate_inn = validate_inn
_validate_bik = validate_bik
_validate_account = validate_account