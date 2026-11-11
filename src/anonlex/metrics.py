"""Метрики качества распознавания: precision / recall по категориям.

Сравнение идёт на уровне ключей сущностей (category, key): для PERSON и
COMPANY ключ нормализован базой знаний, для остальных категорий это
значение в нижнем регистре. Серебряный стандарт: gold известен генератору
корпуса по построению (см. corpus.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple

Label = Tuple[str, str]


@dataclass
class CategoryScore:
    """Счётчики и метрики одной категории."""

    category: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        """Доля найденного, что реально является сущностью."""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        """Доля реальных сущностей, которые мы нашли."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0


@dataclass
class MetricsReport:
    """Отчёт по всем категориям с проверкой quality-gates."""

    zero_tolerance: Tuple[str, ...] = ()
    scores: Dict[str, CategoryScore] = field(default_factory=dict)

    def overall(self) -> CategoryScore:
        total = CategoryScore(category="ALL")
        for score in self.scores.values():
            total.true_positives += score.true_positives
            total.false_positives += score.false_positives
            total.false_negatives += score.false_negatives
        return total

    def zero_tolerance_violations(self) -> List[str]:
        """Категории нулевой терпимости с recall < 1.0."""
        return [
            cat
            for cat in self.zero_tolerance
            if cat in self.scores and self.scores[cat].recall < 1.0
        ]

    def gates_passed(self, precision_floor: float = 0.95, recall_floor: float = 0.90) -> bool:
        """Quality-gates G1/G2 из docs/02_ARCHITECTURE.md."""
        overall = self.overall()
        return (
            overall.precision >= precision_floor
            and overall.recall >= recall_floor
            and not self.zero_tolerance_violations()
        )

    def to_text(self) -> str:
        lines = [
            f"{s.category:9} TP={s.true_positives:3} FP={s.false_positives:3} "
            f"FN={s.false_negatives:3} P={s.precision:.2f} R={s.recall:.2f}"
            for s in sorted(self.scores.values(), key=lambda x: x.category)
        ]
        overall = self.overall()
        lines.append(
            f"{'ALL':9} TP={overall.true_positives:3} FP={overall.false_positives:3} "
            f"FN={overall.false_negatives:3} P={overall.precision:.2f} R={overall.recall:.2f}"
        )
        violations = self.zero_tolerance_violations()
        lines.append("Zero-tolerance: " + ("OK" if not violations else f"VIOLATIONS {violations}"))
        return "\n".join(lines)


def evaluate(
    gold: Set[Label],
    predicted: Set[Label],
    categories: Iterable[str],
    zero_tolerance: Iterable[str] = (),
) -> MetricsReport:
    """Считает TP/FP/FN по категориям между gold- и predicted-наборами."""
    report = MetricsReport(zero_tolerance=tuple(zero_tolerance))
    for category in categories:
        g = {key for cat, key in gold if cat == category}
        p = {key for cat, key in predicted if cat == category}
        report.scores[category] = CategoryScore(
            category=category,
            true_positives=len(g & p),
            false_positives=len(p - g),
            false_negatives=len(g - p),
        )
    return report