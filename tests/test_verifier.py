"""Тесты для модуля verifier.py — верификатор «Чистый лист»."""
import pytest
from anonlex.verifier import verify_text


@pytest.fixture
def clean_text():
    return "Договор заключен между [КОМПАНИЯ_1] и [ФИО_1] на сумму [СУММА_1] рублей."


@pytest.fixture
def text_with_residual_pdn():
    return "Договор заключен между ООО Ромашка и Иванов Иван Иванович на сумму 100000 рублей."


@pytest.fixture
def sample_mapping():
    return [
        {"category": "COMPANY", "original_value": "ООО Ромашка", "placeholder": "[КОМПАНИЯ_1]"},
        {"category": "PERSON", "original_value": "Иванов Иван Иванович", "placeholder": "[ФИО_1]"},
        {"category": "AMOUNT", "original_value": "100000", "placeholder": "[СУММА_1]"},
    ]


class TestVerifyText:
    def test_clean_text_returns_clean_verdict(self, clean_text, sample_mapping):
        result = verify_text(clean_text, sample_mapping)
        assert result["verdict"] == "CLEAN"
        assert len(result["findings"]) == 0

    def test_text_with_residual_pdn_returns_suspicious(self, text_with_residual_pdn, sample_mapping):
        result = verify_text(text_with_residual_pdn, sample_mapping)
        assert result["verdict"] in ["REVIEW", "SUSPICIOUS"]
        assert len(result["findings"]) > 0

    def test_verification_checks_rules(self, clean_text, sample_mapping):
        result = verify_text(clean_text, sample_mapping)
        assert "rules_checked" in result
        assert result["rules_checked"] > 0

    def test_empty_text_returns_clean(self, sample_mapping):
        result = verify_text("", sample_mapping)
        assert result["verdict"] == "CLEAN"

    def test_empty_mapping_returns_clean(self, clean_text):
        result = verify_text(clean_text, [])
        assert result["verdict"] == "CLEAN"

    def test_ocr_glued_inn_is_suspicious(self):
        """Регресс B-004: ИНН, склеенный с лейблом «ИНН6654010142», поднимается."""
        result = verify_text("Реквизиты: ИНН6654010142", [])
        assert result["verdict"] == "SUSPICIOUS"
        assert any(f["rule"] == "INN" for f in result["findings"])

    def test_leftover_original_value_is_suspicious(self, sample_mapping):
        """Оригинал из маппинга не должен оставаться в обезличенном тексте."""
        result = verify_text("Подпись: Иванов Иван Иванович", sample_mapping)
        assert result["verdict"] == "SUSPICIOUS"
        assert any(f["rule"] == "LEFTOVER" for f in result["findings"])