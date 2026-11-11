"""Тесты метрик precision/recall и quality-gates."""

from anonlex.metrics import evaluate


def test_precision_recall_basic() -> None:
    gold = {("INN", "1"), ("INN", "2"), ("PERSON", "a")}
    pred = {("INN", "1"), ("INN", "3"), ("PERSON", "a")}
    report = evaluate(gold, pred, ["INN", "PERSON"], zero_tolerance=("INN",))
    assert report.scores["INN"].precision == 0.5
    assert report.scores["INN"].recall == 0.5
    assert report.scores["PERSON"].precision == 1.0
    assert report.zero_tolerance_violations() == ["INN"]
    assert not report.gates_passed()


def test_empty_sets_pass_gates() -> None:
    report = evaluate(set(), set(), ["EMAIL"])
    assert report.scores["EMAIL"].precision == 1.0
    assert report.scores["EMAIL"].recall == 1.0
    assert report.gates_passed()


def test_overall_aggregates() -> None:
    gold = {("INN", "1"), ("BIK", "2")}
    pred = {("INN", "1"), ("BIK", "2"), ("EMAIL", "x")}
    report = evaluate(gold, pred, ["INN", "BIK", "EMAIL"])
    overall = report.overall()
    assert overall.true_positives == 2
    assert overall.false_positives == 1
    assert overall.false_negatives == 0