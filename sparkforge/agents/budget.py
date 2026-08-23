"""Deterministic context policies for token-efficient agent collaboration."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any


def estimate_tokens(value: Any) -> int:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, (len(text) + 3) // 4)

def fingerprint(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def deduplicate(records: Iterable[dict[str, Any]], key: str = "content") -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        marker = fingerprint(record.get(key, record))
        if marker not in seen:
            seen.add(marker)
            result.append(record)
    return result


def select_context(
    records: Iterable[dict[str, Any]],
    query: str,
    budget_tokens: int,
    *,
    preserve_kinds: set[str] | None = None,
) -> list[dict[str, Any]]:
    preserve_kinds = preserve_kinds or {"task", "decision", "fact", "snapshot"}
    query_terms = {term.lower() for term in query.split() if len(term) > 2}
    unique = deduplicate(records)
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, record in enumerate(unique):
        text = json.dumps(record, ensure_ascii=False, sort_keys=True).lower()
        score = sum(1 for term in query_terms if term in text)
        if record.get("kind") in preserve_kinds:
            score += 3
        ranked.append((score, index, record))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: list[dict[str, Any]] = []
    used = 0
    for _, _, record in ranked:
        cost = estimate_tokens(record)
        if used + cost > budget_tokens and selected:
            continue
        selected.append(record)
        used += cost
        if used >= budget_tokens:
            break
    return list(reversed(selected))

def compact_summary(records: Iterable[dict[str, Any]], max_items: int = 12) -> dict[str, Any]:
    rows = list(records)
    return {
        "record_count": len(rows),
        "kinds": sorted({str(row.get("kind", "unknown")) for row in rows}),
        "message_ids": [
            row.get("message_id") for row in rows[-max_items:] if row.get("message_id")
        ],
        "facts": [
            row.get("content", {}).get("fact")
            for row in rows
            if row.get("kind") == "fact" and row.get("content", {}).get("fact")
        ][:max_items],
    }
