"""Маппинг сущностей: оригинал ↔ плейсхолдер.

Спринт 6 (FR-22, FR-24):
- mode: режим анонимизации (placeholder/mask/delete)
- manual: добавлено вручную юристом
- overridden: перезаписано юристом (auto → manual)
- original_placeholder: для отката к автоматическому варианту
- color: цвет категории для UI (FR-23)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# Версия схемы маппинга (формат: "anonlex.mapping/MAJOR.MINOR")
SCHEMA_VERSION = "anonlex.mapping/1.0"

# Допустимые режимы анонимизации
VALID_MODES = frozenset({"placeholder", "mask", "delete"})

# Символ маски для режима "mask"
MASK_SYMBOL = "***"


@dataclass
class MappingEntity:
    """Сущность в маппинге: оригинал ↔ плейсхолдер.
    
    Спринт 6: добавлены поля mode, manual, overridden, original_placeholder, color.
    """
    
    category: str
    original_value: str
    placeholder: str
    occurrences: int = 1
    
    # Новые поля спринта 6
    mode: str = "placeholder"
    manual: bool = False
    overridden: bool = False
    original_placeholder: str = ""
    color: str = "#64748b"
    
    def __post_init__(self):
        if self.mode not in VALID_MODES:
            raise ValueError(f"Недопустимый режим: {self.mode}. Допустимые: {VALID_MODES}")
        if not self.original_placeholder:
            self.original_placeholder = self.placeholder
    
    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "original_value": self.original_value,
            "placeholder": self.placeholder,
            "occurrences": self.occurrences,
            "mode": self.mode,
            "manual": self.manual,
            "overridden": self.overridden,
            "original_placeholder": self.original_placeholder,
            "color": self.color,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MappingEntity":
        return cls(
            category=data["category"],
            original_value=data["original_value"],
            placeholder=data["placeholder"],
            occurrences=data.get("occurrences", 1),
            mode=data.get("mode", "placeholder"),
            manual=data.get("manual", False),
            overridden=data.get("overridden", False),
            original_placeholder=data.get("original_placeholder", data["placeholder"]),
            color=data.get("color", "#64748b"),
        )
    
    def set_mode(self, mode: str) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Недопустимый режим: {mode}. Допустимые: {VALID_MODES}")
        self.mode = mode
    
    def set_manual(self, manual: bool = True) -> None:
        if manual and not self.manual:
            self.overridden = True
        self.manual = manual
    
    def reset_to_auto(self) -> None:
        self.manual = False
        self.overridden = False
        self.placeholder = self.original_placeholder
        self.mode = "placeholder"
    
    def get_replacement_text(self) -> str:
        if self.mode == "placeholder":
            return self.placeholder
        elif self.mode == "mask":
            return MASK_SYMBOL
        elif self.mode == "delete":
            return ""
        return self.placeholder
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MappingEntity):
            return False
        return (
            self.category == other.category
            and self.original_value == other.original_value
            and self.placeholder == other.placeholder
        )
    
    def __hash__(self) -> int:
        return hash((self.category, self.original_value, self.placeholder))


@dataclass
class Mapping:
    """Маппинг всех сущностей документа.
    
    Поддерживает дедупликацию: при добавлении сущности с тем же
    (category, original_value.casefold()) увеличивается occurrences.
    """
    
    file_sha256: str
    engine_version: str
    entities: List[MappingEntity] = field(default_factory=list)
    _index: Dict[Tuple[str, str], MappingEntity] = field(default_factory=dict, repr=False)
    
    def _key(self, category: str, original_value: str) -> Tuple[str, str]:
        return (category, original_value.casefold())
    
    def add(self, entity: MappingEntity) -> None:
        """Добавить сущность (с дедупликацией по category+original_value)."""
        key = self._key(entity.category, entity.original_value)
        if key in self._index:
            existing = self._index[key]
            existing.occurrences += entity.occurrences
        else:
            self.entities.append(entity)
            self._index[key] = entity
    
    def get_by_category(self, category: str) -> List[MappingEntity]:
        return [e for e in self.entities if e.category == category]
    
    def get_by_placeholder(self, placeholder: str) -> MappingEntity | None:
        for e in self.entities:
            if e.placeholder == placeholder:
                return e
        return None
    
    def get_by_original_value(self, original_value: str) -> List[MappingEntity]:
        return [e for e in self.entities if e.original_value == original_value]
    
    def placeholder_for(self, category: str, value: str) -> str | None:
        """Регистронезависимый поиск плейсхолдера."""
        key = self._key(category, value)
        entity = self._index.get(key)
        return entity.placeholder if entity else None
    
    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "file_sha256": self.file_sha256,
            "engine_version": self.engine_version,
            "entities": [e.to_dict() for e in self.entities],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Mapping":
        schema = data.get("schema", "anonlex.mapping/1.0")
        if schema != SCHEMA_VERSION:
            raise ValueError(f"Несовместимая версия схемы: {schema} (ожидается {SCHEMA_VERSION})")
        mapping = cls(
            file_sha256=data["file_sha256"],
            engine_version=data["engine_version"],
        )
        for entity_data in data["entities"]:
            mapping.add(MappingEntity.from_dict(entity_data))
        return mapping
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_text: str) -> "Mapping":
        data = json.loads(json_text)
        return cls.from_dict(data)
    
    def to_csv(self) -> str:
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "category", "original_value", "placeholder", "occurrences",
            "mode", "manual", "overridden"
        ])
        for e in self.entities:
            writer.writerow([
                e.category, e.original_value, e.placeholder, e.occurrences,
                e.mode, e.manual, e.overridden
            ])
        return output.getvalue()
    
    @classmethod
    def from_csv(cls, csv_text: str, file_sha256: str, engine_version: str) -> "Mapping":
        import io
        import csv
        mapping = cls(file_sha256=file_sha256, engine_version=engine_version)
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            entity = MappingEntity(
                category=row["category"],
                original_value=row["original_value"],
                placeholder=row["placeholder"],
                occurrences=int(row.get("occurrences", 1)),
                mode=row.get("mode", "placeholder"),
                manual=row.get("manual", "False").lower() == "true",
                overridden=row.get("overridden", "False").lower() == "true",
                color=row.get("color", "#64748b"),
            )
            mapping.add(entity)
        return mapping
    
    def __len__(self) -> int:
        return len(self.entities)
    
    def __iter__(self):
        return iter(self.entities)