"""Тесты для модуля act.py — генератор Акта экспертной обработки."""
import pytest
from anonlex.act import build_act_data, build_act_html, build_act_json


@pytest.fixture
def sample_meta():
    return {
        "operator": "admin",
        "timestamp": 1793895580.763329,
        "filename": "test_dogovor.docx",
        "sha256_source": "abc123def456",
        "sha256_result": "def456abc123",
        "engine_version": "1.0.0",
        "scope": "текст документа (DOCX)",
        "file_size": 1024,
    }


@pytest.fixture
def sample_mapping():
    return [
        {
            "category": "PERSON",
            "original_value": "Иванов Иван Иванович",
            "placeholder": "[ФИО_1]",
            "occurrences": 3,
        },
        {
            "category": "INN",
            "original_value": "7707083893",
            "placeholder": "[ИНН_1]",
            "occurrences": 1,
        },
        {
            "category": "COMPANY",
            "original_value": 'ООО "Ромашка"',
            "placeholder": "[КОМПАНИЯ_1]",
            "occurrences": 2,
        },
    ]


@pytest.fixture
def sample_verification_clean():
    return {"verdict": "CLEAN", "rules_checked": 19, "findings": []}


@pytest.fixture
def sample_verification_review():
    return {
        "verdict": "REVIEW",
        "rules_checked": 19,
        "findings": [{"rule": "COSVEN", "snippet": "косвенный идентификатор", "severity": "low"}],
    }


@pytest.fixture
def sample_verification_suspicious():
    return {
        "verdict": "SUSPICIOUS",
        "rules_checked": 19,
        "findings": [{"rule": "PASSPORT", "snippet": "4510 123456", "severity": "critical"}],
    }


class TestBuildActData:
    def test_act_data_structure(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        
        assert "act_id" in data
        assert "timestamp" in data
        assert "location" in data
        assert "original_filename" in data
        assert "original_hash" in data
        assert "processed_filename" in data
        assert "processed_hash" in data
        assert "categories_count" in data
        assert "entities_count" in data
        assert "verification_rules" in data
        assert "verdict" in data
        assert "risk_level" in data
        assert "entities_table" in data

    def test_act_id_format(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        assert data["act_id"].startswith("admin_")
        assert "1793895580" in data["act_id"]

    def test_entities_count(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        assert data["entities_count"] == 3

    def test_verdict_clean(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        assert data["verdict"] == "CLEAN"
        assert "Отсутствует" in data["risk_level"]

    def test_verdict_review(self, sample_meta, sample_mapping, sample_verification_review):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_review)
        assert data["verdict"] == "REVIEW"
        assert "Минимальный" in data["risk_level"]

    def test_verdict_suspicious(self, sample_meta, sample_mapping, sample_verification_suspicious):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_suspicious)
        assert data["verdict"] == "SUSPICIOUS"
        assert "Повышенный" in data["risk_level"]

    def test_entities_table_structure(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        assert len(data["entities_table"]) == 3
        
        first_entity = data["entities_table"][0]
        assert "category" in first_entity
        assert "original_value" in first_entity
        assert "placeholder" in first_entity
        assert "occurrences" in first_entity


class TestBuildActHtml:
    def test_html_contains_title(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "АКТ АВТОМАТИЗИРОВАННОЙ ЭКСПЕРТНОЙ ОБРАБОТКИ ДАННЫХ" in html
        assert "ЛАСТИК" in html

    def test_html_contains_gost_reference(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "ГОСТ Р 56939-2024" in html
        assert "Приказ ФСТЭК России от 01.12.2023 № 240" in html

    def test_html_contains_hashes(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "abc123def456" in html  # sha256_source
        assert "def456abc123" in html  # sha256_result

    def test_html_contains_entities_table(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "Иванов Иван Иванович" in html
        assert "[ФИО_1]" in html
        assert "7707083893" in html
        assert "[ИНН_1]" in html

    def test_html_contains_signature_block(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "ПОДПИСЬ ОТВЕТСТВЕННОГО ОПЕРАТОРА" in html
        assert "Должность:" in html
        assert "ФИО:" in html
        assert "Подпись:" in html

    def test_html_contains_legal_references(self, sample_meta, sample_mapping, sample_verification_clean):
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        html = build_act_html(data)
        
        assert "ст. 84-87 ГПК РФ" in html
        assert "ст. 82-86 АПК РФ" in html


class TestBuildActJson:
    def test_json_is_valid(self, sample_meta, sample_mapping, sample_verification_clean):
        import json
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        json_str = build_act_json(data)
        
        parsed = json.loads(json_str)
        assert parsed["verdict"] == "CLEAN"
        assert parsed["entities_count"] == 3

    def test_json_contains_all_fields(self, sample_meta, sample_mapping, sample_verification_clean):
        import json
        data = build_act_data(sample_meta, sample_mapping, sample_verification_clean)
        json_str = build_act_json(data)
        
        parsed = json.loads(json_str)
        assert "act_id" in parsed
        assert "timestamp" in parsed
        assert "entities_table" in parsed