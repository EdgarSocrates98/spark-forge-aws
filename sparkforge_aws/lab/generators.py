"""Small deterministic synthetic datasets for Forge Lab scenarios."""

from __future__ import annotations

import json
import random
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from .contract import LabContractError

CANONICAL_SCHEMAS = frozenset(
    {
        "customer",
        "order",
        "payment",
        "clickstream",
        "iot_sensor",
        "transaction",
        "cdc_customer",
        "fraud_event",
    }
)


def generate_records(
    schema: str,
    *,
    seed: int,
    record_count: int,
    key_cardinality: int = 100,
    skew: float = 0.0,
    late_event_ratio: float = 0.0,
    duplicate_ratio: float = 0.0,
) -> Iterator[dict[str, Any]]:
    """Yield bounded, deterministic records without reading enterprise data."""
    if schema not in CANONICAL_SCHEMAS:
        raise LabContractError(f"unsupported canonical schema: {schema}")
    if record_count <= 0 or key_cardinality <= 0:
        raise LabContractError("record_count and key_cardinality must be positive")
    for field, value in (
        ("skew", skew),
        ("late_event_ratio", late_event_ratio),
        ("duplicate_ratio", duplicate_ratio),
    ):
        if not 0 <= value <= 1:
            raise LabContractError(f"{field} must be between 0 and 1")
    rng = random.Random(seed)  # noqa: S311 - gerador deterministico de dados sinteticos, nao cripto
    previous: dict[str, Any] | None = None
    for index in range(record_count):
        if previous is not None and rng.random() < duplicate_ratio:
            yield dict(previous, duplicate_of=previous["event_id"])
            continue
        key = _key(rng, key_cardinality, skew)
        timestamp = index if rng.random() >= late_event_ratio else max(0, index - rng.randint(1, 5))
        record = {
            "event_id": f"{schema}-{seed}-{index}",
            "entity_id": f"entity-{key}",
            "event_time": timestamp,
            "schema": schema,
            "value": round(rng.random() * 100, 6),
        }
        previous = record
        yield record


def write_jsonl(path: str | Path, records: Iterator[Mapping[str, Any]]) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    return count


def _key(rng: random.Random, cardinality: int, skew: float) -> int:
    if skew <= 0:
        return rng.randrange(cardinality)
    hot = max(1, int(cardinality * 0.05))
    return rng.randrange(hot) if rng.random() < skew else rng.randrange(cardinality)


__all__ = ["CANONICAL_SCHEMAS", "generate_records", "write_jsonl"]
