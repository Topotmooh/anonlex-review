"""
Комплексные тесты для AnonLex.
Фокус на регрессионных багах, граничных случаях и end-to-end проверке пайплайна.
"""
import io
import zipfile
import pytest
from anonlex.finder import find_spans, _validate_inn
from anonlex.knowledge import extract_entities_full_text, _strip_titles, forms_of, KnowledgeEntity
from anonlex.pipeline import anonymize_docx
from anonlex.mapping import Mapping


# ==============================================================================
# 1. МОДУЛЬНЫЕ ТЕСТЫ: FINDERS И REGEX (Защита от ложных срабатываний)
# ==============================================================================

def test_no_false_positives_on_common_text():
    """Регрессионный тест: 'Простой текст без' не должен определяться как ФИО."""
    text = "Простой текст без персональных данных"
    spans = find_spans(text, enabled_categories={"PERSON"})
    assert len(spans) == 0, f"Ложное срабатывание на обычном тексте: {spans}"


def test_inn_validation_logic():
    """Проверка контрольных сумм ИНН."""
    # Валидный ИНН 10 знаков (например, Яндекс)
    assert _validate_inn("7707083893") is True
    # Невалидный ИНН (последняя цифра не совпадает с контрольной суммой)
    assert _validate_inn("1234567890") is False


def test_passport_with_number_sign():
    """Паспорт должен находиться с префиксом '№' и без пробелов."""
    text = "Паспорт №4500123456 и № 45 00 123456"
    spans = find_spans(text, enabled_categories={"PASSPORT"})
    assert len(spans) >= 1, "Не найдены паспорта с префиксом №"


# ==============================================================================
# 2. МОДУЛЬНЫЕ ТЕСТЫ: KNOWLEDGE BASE
# ==============================================================================

def test_strip_titles():
    """Титулы должны корректно удаляться из начала строки."""
    assert _strip_titles("директор Иванов Иван Иванович") == "Иванов Иван Иванович"
    assert _strip_titles("генеральный директор Петров П.П.") == "Петров П.П."


def test_forms_of_person():
    """Генерация форм для ФИО должна включать инициалы и фамилию."""
    entity = KnowledgeEntity(category="PERSON", value="Иванов Иван Иванович", key="иванов и.и.")
    forms = forms_of(entity)
    assert "Иванов И.И." in forms
    assert "Иванов" in forms
    assert "ИВАНОВ ИВАН ИВАНОВИЧ" in forms


# ==============================================================================
# 3. ИНТЕГРАЦИОННЫЕ ТЕСТЫ: PIPELINE (DOCX)
# ==============================================================================

def _create_minimal_docx(xml_content: str) -> bytes:
    """Хелпер для создания минимального DOCX файла в памяти."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
        zf.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        zf.writestr("word/document.xml", xml_content.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    return buffer.getvalue()


def test_empty_document_handling():
    """Пустой документ не должен вызывать ошибок и должен возвращать 0 spans."""
    empty_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body></w:body></w:document>'
    doc_bytes = _create_minimal_docx(empty_xml)
    
    result = anonymize_docx(doc_bytes, enabled={"PERSON", "INN"})
    
    assert result.spans == 0
    assert len(result.mapping.entities) == 0
    assert result.preview == ""


def test_end_to_end_placeholder_replacement():
    """ФИО должно быть полностью заменено на плейсхолдер, без остатка 'Иванович'."""
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>Иванов Иван Иванович</w:t></w:r></w:p></w:body></w:document>'
    )
    doc_bytes = _create_minimal_docx(xml_content)
    
    result = anonymize_docx(doc_bytes, enabled={"PERSON"})
    
    # Проверяем, что плейсхолдер есть
    assert "[ФИО_1]" in result.preview or "[ФИО_1]" in result.docx.decode("utf-8", errors="ignore")
    # Проверяем, что исходное имя удалено
    assert "Иванов" not in result.docx.decode("utf-8", errors="ignore")
    assert "Иванович" not in result.docx.decode("utf-8", errors="ignore")


# ==============================================================================
# 4. ТЕСТЫ ВЕРИФИКАТОРА (ЗАЩИТА ОТ УТЕЧЕК)
# ==============================================================================

def test_verifier_catches_leftover_pii():
    """Верификатор должен обнаруживать ПДн, если они остались в тексте."""
    from anonlex.verifier import verify_text
    
    # Имитируем ситуацию, когда маппинг пуст, но в тексте есть ИНН
    text = "Договор с ИНН 7707083893"
    result = verify_text(text, mapping=[])
    
    assert result["verdict"] == "SUSPICIOUS"
    assert any(f["rule"] == "INN" for f in result["findings"])


def test_verifier_passes_clean_text():
    """Верификатор должен пропускать чистый текст с плейсхолдерами."""
    from anonlex.verifier import verify_text
    
    text = "Договор с [ФИО_1] и [ИНН_1]"
    mapping = [
        {"category": "PERSON", "original_value": "Иванов И.И.", "placeholder": "[ФИО_1]"},
        {"category": "INN", "original_value": "7707083893", "placeholder": "[ИНН_1]"}
    ]
    
    result = verify_text(text, mapping=mapping)
    assert result["verdict"] == "CLEAN"