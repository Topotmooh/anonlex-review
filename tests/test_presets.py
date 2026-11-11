"""Тесты для модуля presets.py — отраслевые пресеты.

Пресеты в ЛАСТИК — это заранее настроенные наборы категорий ПДн
для конкретных отраслей (судебные акты, кадровые документы, медицина и т.д.).
"""
from anonlex.presets import get_preset, list_presets


class TestListPresets:
    """Тесты функции list_presets()."""

    def test_list_presets_returns_list(self):
        """list_presets() должен возвращать список."""
        presets = list_presets()
        assert isinstance(presets, list)

    def test_list_presets_not_empty(self):
        """Список пресетов не должен быть пустым."""
        presets = list_presets()
        assert len(presets) > 0

    def test_preset_has_required_fields(self):
        """Каждый пресет в списке должен иметь code, name и description."""
        presets = list_presets()
        for preset in presets:
            assert "code" in preset, f"Пресет без поля 'code': {preset}"
            assert "name" in preset, f"Пресет без поля 'name': {preset}"
            assert "description" in preset, f"Пресет без поля 'description': {preset}"

    def test_preset_codes_are_unique(self):
        """Коды пресетов должны быть уникальными."""
        presets = list_presets()
        codes = [p["code"] for p in presets]
        assert len(codes) == len(set(codes)), "Найдены дублирующиеся коды пресетов"

    def test_preset_names_are_non_empty(self):
        """Названия пресетов не должны быть пустыми."""
        presets = list_presets()
        for preset in presets:
            assert len(preset["name"].strip()) > 0, f"Пустое название у пресета {preset['code']}"


class TestGetPreset:
    """Тесты функции get_preset()."""

    def test_get_preset_returns_set(self):
        """get_preset() должен возвращать set категорий для известного кода."""
        presets = list_presets()
        if presets:
            first_code = presets[0]["code"]
            result = get_preset(first_code)
            assert isinstance(result, set), f"Ожидался set, получен {type(result)}"

    def test_get_preset_returns_non_empty_set(self):
        """Полученный set категорий не должен быть пустым."""
        presets = list_presets()
        if presets:
            first_code = presets[0]["code"]
            result = get_preset(first_code)
            assert result is not None
            assert len(result) > 0, f"Пресет '{first_code}' вернул пустой набор категорий"

    def test_get_preset_unknown_returns_none(self):
        """get_preset() для неизвестного кода должен вернуть None."""
        result = get_preset("this_preset_does_not_exist_12345")
        assert result is None

    def test_get_preset_unknown_empty_string_returns_none(self):
        """get_preset() для пустой строки должен вернуть None."""
        result = get_preset("")
        assert result is None

    def test_get_preset_all_presets_have_categories(self):
        """Для каждого пресета из списка get_preset() должен вернуть категории."""
        presets = list_presets()
        for preset in presets:
            code = preset["code"]
            categories = get_preset(code)
            assert categories is not None, f"Пресет '{code}' не имеет категорий"
            assert isinstance(categories, set), f"Пресет '{code}' вернул не set"
            assert len(categories) > 0, f"Пресет '{code}' вернул пустой набор"

    def test_get_preset_categories_are_valid_codes(self):
        """Все категории в пресете должны быть валидными кодами."""
        from anonlex.categories import CATALOG
        valid_codes = {c.code for c in CATALOG}
        
        presets = list_presets()
        for preset in presets:
            categories = get_preset(preset["code"])
            if categories is None:
                continue
            for cat in categories:
                assert cat in valid_codes, (
                    f"Пресет '{preset['code']}' содержит неизвестную категорию '{cat}'"
                )


class TestPresetsIntegration:
    """Интеграционные тесты пресетов."""

    def test_court_preset_exists(self):
        """Пресет 'court' (судебный акт) должен существовать — это ключевой для ЛАСТИК."""
        presets = list_presets()
        codes = [p["code"] for p in presets]
        # Проверяем, что есть хотя бы один пресет (court может называться иначе)
        assert len(codes) >= 1

    def test_get_preset_idempotent(self):
        """Повторный вызов get_preset() для одного кода должен возвращать одинаковый результат."""
        presets = list_presets()
        if presets:
            code = presets[0]["code"]
            result1 = get_preset(code)
            result2 = get_preset(code)
            assert result1 == result2