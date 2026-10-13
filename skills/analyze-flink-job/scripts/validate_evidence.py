from __future__ import annotations


def validate(items: list[dict]) -> list[str]:
    errors = []
    for index, item in enumerate(items):
        if not item.get("fact_id") and item.get("kind") != "unresolved":
            errors.append(f"items[{index}].fact_id")
    return errors
