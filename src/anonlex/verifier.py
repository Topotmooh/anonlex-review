"""Верификатор «Чистый лист» для проверки текста на остаточные ПДн."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

VERIFIER_RULES = [
    {
        "name": "PASSPORT",
        "pattern": re.compile(r"(?i)(?<!\d)(?:№\s*|N\.?\s*|#\s*)?\d{2}[\s\-]?\d{2}[\s\-]?\d{6}(?!\d)"),
        "severity": "critical"
    },
    {
        "name": "INN",
        "pattern": re.compile(r"(?i)(?:инн|inn)?\s*:?\s*(?<!\d)\d{10}(?!\d)|(?<!\d)\d{12}(?!\d)"),
        "severity": "critical"
    },
    {
        "name": "SNILS",
        "pattern": re.compile(r"(?i)(?:снилс)?\s*:?\s*\b\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2}\b"),
        "severity": "critical"
    },
    {
        "name": "PHONE",
        "pattern": re.compile(r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"),
        "severity": "critical"
    },
    {
        "name": "EMAIL",
        "pattern": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "severity": "critical"
    },
    {
        "name": "ACCOUNT",
        "pattern": re.compile(r"(?i)(?:счет|account|р\/с)?\s*:?\s*\b\d{20}\b"),
        "severity": "critical"
    },
    {
        "name": "BIK",
        "pattern": re.compile(r"(?i)(?:бик|bik)?\s*:?\s*\b04\d{7}\b"),
        "severity": "critical"
    }
]

_PLACEHOLDER_PATTERN = re.compile(r"^\[.*_\d+\]$")


def verify_text(text: str, mapping: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            "verdict": "CLEAN",
            "rules_checked": len(VERIFIER_RULES),
            "findings": []
        }

    findings = []
    rules_checked = len(VERIFIER_RULES)
    
    # 1. Проверяем, не остались ли в тексте оригинальные значения из маппинга
    if mapping:
        for entity in mapping:
            if not isinstance(entity, dict):
                continue
            
            original_value = entity.get("original_value", "")
            
            if not original_value:
                continue
                
            if original_value in text:
                start = text.find(original_value)
                end = start + len(original_value)
                snippet_start = max(0, start - 30)
                snippet_end = min(len(text), end + 30)
                # 🔥 ИСПРАВЛЕНИЕ: корректная замена переносов строк в сниппете
                snippet = text[snippet_start:snippet_end].replace("\n", " ").replace("\r", " ")
                
                findings.append({
                    "rule": "LEFTOVER",
                    "severity": "critical",
                    "value": original_value,
                    "snippet": f"...{snippet}..."
                })

    # 2. Проверяем текст по регулярным выражениям
    for rule in VERIFIER_RULES:
        for match in rule["pattern"].finditer(text):
            matched_text = match.group(0).strip()
            
            if _PLACEHOLDER_PATTERN.match(matched_text):
                continue
            
            if any(f["value"] == matched_text for f in findings):
                continue

            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            snippet = text[start:end].replace("\n", " ").replace("\r", " ")

            findings.append({
                "rule": rule["name"],
                "severity": rule["severity"],
                "value": matched_text,
                "snippet": f"...{snippet}..."
            })

    # Определение итогового вердикта
    verdict = "CLEAN"
    if any(f["severity"] == "critical" for f in findings):
        verdict = "SUSPICIOUS"
    elif any(f["severity"] == "warning" for f in findings):
        verdict = "REVIEW"

    return {
        "verdict": verdict,
        "rules_checked": rules_checked,
        "findings": findings
    }