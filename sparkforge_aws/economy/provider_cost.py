"""Observed provider-token cost with an operator-supplied pricing basis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge_aws.collect.host_usage import read_host_usage

TOKEN_FIELDS = {
    "input_tokens": "input_tokens",
    "output_tokens": "output_tokens",
    "cache_read_tokens": "cached_tokens",
    "cache_creation_tokens": "cache_creation_tokens",
}


def provider_cost(transcript: Path | str, pricing: Path | str) -> dict[str, Any]:
    """Calculate cost only from measured transcript usage and explicit pricing."""
    usage = read_host_usage(transcript)
    raw = _read_pricing(pricing)
    tokens = {name: int(usage.get(source, 0)) for name, source in TOKEN_FIELDS.items()}
    unresolved = [dict(item) for item in usage.get("unresolved", [])]
    unresolved.extend(raw["unresolved"])
    rates = raw.get("rates", {})
    if not isinstance(rates, dict):
        unresolved.append({"reason": "pricing_rates_malformed", "count": 1})
        rates = {}
    components: dict[str, float | None] = {}
    for name, value in tokens.items():
        rate = rates.get(name)
        if isinstance(rate, dict) and isinstance(rate.get("per_million"), (int, float)):
            components[name] = value / 1_000_000 * float(rate["per_million"])
        else:
            components[name] = None
            unresolved.append({"reason": "pricing_rate_missing", "field": name, "count": 1})
    complete = not unresolved and bool(tokens or usage.get("message_count"))
    total = round(sum(value for value in components.values() if value is not None), 12)
    result = {
        "schema_version": 1,
        "transcript": Path(transcript).name,
        "source": usage.get("source", ""),
        "tokens": tokens,
        "token_units": {
            "input_tokens": "tokens",
            "output_tokens": "tokens",
            "cache_read_tokens": "tokens",
            "cache_creation_tokens": "tokens",
        },
        "currency": raw.get("currency"),
        "cost_basis": raw.get("cost_basis"),
        "pricing_source": raw.get("source"),
        "components": components,
        "cost_total": total if complete else None,
        "cost_usd": total if complete and raw.get("currency") == "USD" else None,
        "unresolved": unresolved,
    }
    return result


def _read_pricing(path: Path | str) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"unresolved": [{"reason": "pricing_unreadable", "count": 1}]}
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        return {"unresolved": [{"reason": "pricing_schema_invalid", "count": 1}]}
    missing = []
    for field in ("currency", "cost_basis", "source"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            missing.append({"reason": "pricing_field_missing", "field": field, "count": 1})
    return {**raw, "unresolved": missing}


__all__ = ["provider_cost"]
