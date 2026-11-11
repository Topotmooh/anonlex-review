"""Скрипт оценки качества анонимизации (Спринт 10.0)."""
import json
import sys
from pathlib import Path

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anonlex.pipeline import anonymize_file

CORPUS_DIR = Path("benchmark/corpus")
GT_FILE = Path("benchmark/ground_truth.json")
REPORT_FILE = Path("docs/quality_report.json")

def run_benchmark():
    if not GT_FILE.exists():
        print("❌ Файл ground_truth.json не найден. Сначала запустите generate_corpus.py")
        return

    with open(GT_FILE, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    metrics = {
        "overall": {"tp": 0, "fn": 0, "fp": 0},
        "by_category": {}
    }

    print("🚀 Запуск бенчмарка...\n")

    for doc_name, expected_entities in ground_truth.items():
        doc_path = CORPUS_DIR / doc_name
        if not doc_path.exists():
            print(f"⚠️ Пропущен: {doc_name} (файл не найден)")
            continue
        
        print(f"📄 Обработка: {doc_name}")
        with open(doc_path, 'rb') as f:
            data = f.read()
        
        try:
            result = anonymize_file(data, doc_name)
            # Собираем найденные сущности: {value: category}
            found_entities = {e.original_value: e.category for e in result.mapping.entities}
            
            for ent in expected_entities:
                cat = ent["category"]
                val = ent["value"]
                
                if cat not in metrics["by_category"]:
                    metrics["by_category"][cat] = {"tp": 0, "fn": 0, "fp": 0}
                
                # True Positive: нашли именно эту сущность и правильно определили категорию
                if val in found_entities and found_entities[val] == cat:
                    metrics["overall"]["tp"] += 1
                    metrics["by_category"][cat]["tp"] += 1
                else:
                    # False Negative: ожидали найти, но не нашли (или определили неверно)
                    metrics["overall"]["fn"] += 1
                    metrics["by_category"][cat]["fn"] += 1
            
            # False Positive approximation: сущности, которые система нашла, но которых нет в GT
            # (Для упрощения считаем FP только если категория явно не совпадает с ожидаемой для этого значения)
            for val, found_cat in found_entities.items():
                expected_cats = [e["category"] for e in expected_entities if e["value"] == val]
                if found_cat not in expected_cats:
                    metrics["overall"]["fp"] += 1
                    if found_cat in metrics["by_category"]:
                        metrics["by_category"][found_cat]["fp"] += 1
                        
        except Exception as e:
            print(f"   ❌ Ошибка обработки: {e}")

    # Расчет финальных метрик
    tp = metrics["overall"]["tp"]
    fn = metrics["overall"]["fn"]
    fp = metrics["overall"]["fp"]
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    report = {
        "total_expected": tp + fn,
        "total_found_exact": tp,
        "false_positives": fp,
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "by_category": {}
    }
    
    for cat, m in metrics["by_category"].items():
        c_tp, c_fn, c_fp = m["tp"], m["fn"], m["fp"]
        c_prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 1.0
        c_rec = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 1.0
        report["by_category"][cat] = {
            "expected": c_tp + c_fn,
            "found": c_tp,
            "precision": round(c_prec * 100, 2),
            "recall": round(c_rec * 100, 2)
        }
        
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print("\n" + "="*50)
    print("✅ БЕНЧМАРК ЗАВЕРШЕН")
    print(f"📊 Общая точность (Precision): {report['precision']}%")
    print(f"📊 Общая полнота (Recall):    {report['recall']}%")
    print(f"📊 F1-Score:                   {report['f1_score']}%")
    print(f"📄 Отчет сохранен в: {REPORT_FILE}")
    print("="*50)

if __name__ == "__main__":
    run_benchmark()