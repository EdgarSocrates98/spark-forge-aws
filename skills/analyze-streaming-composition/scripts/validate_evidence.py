from __future__ import annotations


def validate(items: list[dict]) -> list[str]:
    return [f"items[{i}].fact_id" for i, item in enumerate(items) if not item.get("fact_id")]
