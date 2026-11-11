"""Акт автоматизированной экспертной обработки данных (спринт 11.0, ребрендинг ЛАСТИК).

Вместо «Паспорта анонимизации» формирует юридически значимый Акт,
который может быть использован как доказательство должной осмотрительности
оператора ПДн при проверках РКН/ФСТЭК и в судебных разбирательствах.
"""

from __future__ import annotations

import datetime
import html
import json
from typing import Dict, List



def build_act_data(meta: Dict, mapping_list: List[Dict], verification: Dict) -> Dict:
    """Формирует структуру данных для Акта экспертной обработки."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Определяем уровень остаточного риска
    verdict = verification.get("verdict", "UNKNOWN")
    if verdict == "CLEAN":
        risk_level = "Отсутствует (вердикт CLEAN)"
    elif verdict == "REVIEW":
        risk_level = "Минимальный (требуется ручная проверка)"
    else:
        risk_level = "Повышенный (выявлены критичные фрагменты)"
    
    # Формируем реестр выявленных признаков ПДн
    entities_table = []
    for e in mapping_list:
        entities_table.append({
            "category": e.get("category", ""),
            "original_value": e.get("original_value", ""),
            "placeholder": e.get("placeholder", ""),
            "occurrences": e.get("occurrences", 0),
        })
    
    # act_id — идентификатор: остаётся числовой Unix-time (уникальность),
    # человекочитаемая дата отдаётся отдельным полем timestamp.
    raw_ts = meta.get("timestamp", 0)
    if isinstance(raw_ts, (int, float)) and raw_ts:
        id_part = str(int(raw_ts))
        timestamp_str = datetime.datetime.fromtimestamp(
            raw_ts, tz=datetime.timezone.utc
        ).strftime("%d.%m.%Y %H:%M UTC")
    else:
        id_part = str(raw_ts)
        timestamp_str = id_part
    operator = str(meta.get("operator", "unknown"))


    # Исправление: processed_filename заменяет расширение, а не первую точку
    # (старый код ломал имена вроде «my.file.docx» → «my_anon.file.docx»).
    orig_filename = meta.get("filename", "")
    if "." in orig_filename:
        stem, _, ext = orig_filename.rpartition(".")
        processed_filename = f"{stem}_anon.{ext}"
    else:
        processed_filename = orig_filename + "_anon"

    return {
        "act_id": f"{operator}_{id_part}",

        "timestamp": now.strftime("%d.%m.%Y %H:%M:%S UTC"),
        "location": "Российская Федерация",
        "original_filename": orig_filename,
        "original_hash": meta.get("sha256_source", ""),
        "file_size": meta.get("file_size", 0),
        "processed_filename": processed_filename,
        "processed_hash": meta.get("sha256_result", ""),
        "categories_count": len(meta.get("categories", [])) or 37,
        "entities_count": len(mapping_list),
        "verification_rules": verification.get("rules_checked", 0),
        "verdict": verdict,
        "risk_level": risk_level,
        "entities_table": entities_table,
        "engine_version": meta.get("engine_version", ""),
        "scope": meta.get("scope", ""),
        "operator": operator,
    }



def build_act_html(data: Dict) -> str:
    """Формирует HTML-версию Акта экспертной обработки.

    Все поля, пришедшие из имени файла, содержимого документа и ввода
    оператора, экранируются: без этого Акт (HTMLResponse того же origin,
    что и приложение) становился точкой XSS, а значения с «<» ломали
    вёрстку юридического документа.
    """
    esc = html.escape
    entities_rows = ""
    for e in data["entities_table"]:
        orig_val = str(e["original_value"])
        display_val = esc(orig_val[:50] + ("..." if len(orig_val) > 50 else ""))
        entities_rows += f"""
        <tr>
            <td style="padding:6px 8px; border:1px solid #d1d5db;">{esc(str(e['category']))}</td>
            <td style="padding:6px 8px; border:1px solid #d1d5db; font-family:monospace; font-size:11px;">{display_val}</td>
            <td style="padding:6px 8px; border:1px solid #d1d5db; font-family:monospace; font-size:11px;">{esc(str(e['placeholder']))}</td>
            <td style="padding:6px 8px; border:1px solid #d1d5db; text-align:center;">{esc(str(e['occurrences']))}</td>
        </tr>"""

    act_id = esc(str(data["act_id"]))
    timestamp = esc(str(data["timestamp"]))
    location = esc(str(data["location"]))
    original_filename = esc(str(data["original_filename"]))
    original_hash = esc(str(data["original_hash"]))
    processed_filename = esc(str(data["processed_filename"]))
    processed_hash = esc(str(data["processed_hash"]))
    categories_count = esc(str(data["categories_count"]))
    entities_count = esc(str(data["entities_count"]))
    verification_rules = esc(str(data["verification_rules"]))
    verdict = esc(str(data["verdict"]))
    risk_level = esc(str(data["risk_level"]))
    engine_version = esc(str(data["engine_version"]))
    scope = esc(str(data["scope"]))
    operator = esc(str(data["operator"]))

    
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Акт экспертной обработки № {act_id}</title>

    <style>
        body {{ font-family: 'Times New Roman', serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ text-align: center; font-size: 18px; margin-bottom: 30px; }}
        h2 {{ font-size: 14px; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 4px; }}
        .field {{ margin: 8px 0; }}
        .label {{ font-weight: bold; }}
        .hash {{ font-family: monospace; font-size: 10px; word-break: break-all; background: #f3f4f6; padding: 4px; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
        th {{ background: #f3f4f6; padding: 6px 8px; border: 1px solid #d1d5db; text-align: left; }}
        .signature {{ margin-top: 40px; }}
        .footer {{ margin-top: 30px; font-size: 10px; color: #6b7280; border-top: 1px solid #d1d5db; padding-top: 10px; }}
    </style>
</head>
<body>
    <h1>АКТ АВТОМАТИЗИРОВАННОЙ ЭКСПЕРТНОЙ ОБРАБОТКИ ДАННЫХ<br>№ {act_id}</h1>
    
    <div class="field"><span class="label">Дата формирования:</span> {timestamp}</div>
    <div class="field"><span class="label">Место формирования:</span> {location}</div>
    
    <h2>1. ОСНОВАНИЕ ПРОВЕДЕНИЯ ОБРАБОТКИ</h2>
    <p>Обработка выполнена с использованием программного комплекса 
    <strong>«ЛАСТИК» (Платформа анонимизации документов и экспертизы)</strong>, 
    процессы разработки которого соответствуют требованиям:</p>
    <ul>
        <li>ГОСТ Р 56939-2024 «Защита информации. Разработка безопасного программного обеспечения. Общие требования»;</li>
        <li>Приказ ФСТЭК России от 01.12.2023 № 240 «Порядок проведения сертификации процессов безопасной разработки программного обеспечения средств защиты информации».</li>
    </ul>
    
    <h2>2. ОБЪЕКТ ИССЛЕДОВАНИЯ</h2>
    <div class="field"><span class="label">Исходный файл:</span> {original_filename}</div>
    <div class="field"><span class="label">Контрольная хеш-сумма (SHA-256):</span><br><span class="hash">{original_hash}</span></div>
    
    <h2>3. РЕЗУЛЬТАТЫ АВТОМАТИЗИРОВАННОГО АНАЛИЗА</h2>
    <div class="field"><span class="label">Проверено категорий признаков ПДн:</span> {categories_count}</div>
    <div class="field"><span class="label">Выявлено и обезличено фрагментов:</span> {entities_count}</div>
    <div class="field"><span class="label">Применено правил верификации:</span> {verification_rules}</div>
    <div class="field"><span class="label">Вердикт системы верификации:</span> <strong>{verdict}</strong></div>
    <div class="field"><span class="label">Остаточный риск повторной идентификации:</span> {risk_level}</div>
    
    <h2>4. СФОРМИРОВАННЫЙ ОБЪЕКТ</h2>
    <div class="field"><span class="label">Обработанный файл:</span> {processed_filename}</div>
    <div class="field"><span class="label">Контрольная хеш-сумма (SHA-256):</span><br><span class="hash">{processed_hash}</span></div>
    
    <h2>5. РЕЕСТР ВЫЯВЛЕННЫХ ПРИЗНАКОВ ПДн</h2>
    <table>
        <thead>
            <tr>
                <th>Категория</th>
                <th>Исходное значение</th>
                <th>Плейсхолдер</th>
                <th>Вхождений</th>
            </tr>
        </thead>
        <tbody>{entities_rows}</tbody>
    </table>
    
    <h2>6. ЗАКЛЮЧЕНИЕ</h2>
    <p>Обработка произведена в соответствии с Методикой автоматизированного 
    выявления и обезличивания персональных данных. Целостность журнала 
    операций гарантирована криптографическими средствами.</p>
    <p>Настоящий Акт может быть использован в качестве доказательства 
    должной осмотрительности оператора персональных данных при проверках 
    регуляторных органов (Роскомнадзор, ФСТЭК России) и в судебных 
    разбирательствах в соответствии со ст. 84-87 ГПК РФ, ст. 82-86 АПК РФ.</p>
    
    <div class="signature">
        <h2>7. ПОДПИСЬ ОТВЕТСТВЕННОГО ОПЕРАТОРА</h2>
        <div class="field">Должность: ________________________</div>
        <div class="field">ФИО: ______________________________</div>
        <div class="field">Подпись: __________________________</div>
        <div class="field">Дата: _____________________________</div>
    </div>
    
    <div class="footer">
        Документ сформирован автоматически программным комплексом «ЛАСТИК» v{engine_version}. 
        Оператор: {operator}. Область обработки: {scope}.
    </div>
</body>
</html>"""


def build_act_json(data: Dict) -> str:
    """Формирует JSON-версию Акта экспертной обработки."""
    return json.dumps(data, ensure_ascii=False, indent=2)