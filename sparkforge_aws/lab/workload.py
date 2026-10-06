"""Deterministic workload plans, kept separate from dataset generation."""

from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

from .contract import LabContractError


def compile_workload(spec: Mapping[str, Any], *, seed: int) -> tuple[dict[str, Any], ...]:
    rate = spec.get("rate", 1)
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise LabContractError("workload.rate must be positive")
    partition = spec.get("partition_key", {})
    if not isinstance(partition, Mapping):
        raise LabContractError("workload.partition_key must be an object")
    strategy = str(partition.get("strategy", "entity_id"))
    burst = spec.get("burst", {})
    if burst and not isinstance(burst, Mapping):
        raise LabContractError("workload.burst must be an object")
    late_events = spec.get("late_events", {})
    if late_events and not isinstance(late_events, Mapping):
        raise LabContractError("workload.late_events must be an object")
    rng = random.Random(seed)  # noqa: S311 - gerador deterministico de dados sinteticos, nao cripto
    steps = int(spec.get("steps", 3))
    if steps <= 0 or steps > 1000:
        raise LabContractError("workload.steps must be between 1 and 1000")
    result = []
    for step in range(steps):
        multiplier = 1
        if burst and int(burst.get("every", 0)) and step and step % int(burst["every"]) == 0:
            multiplier = int(burst.get("multiplier", 1))
        result.append(
            {
                "step": step,
                "seed": rng.randrange(2**31),
                "rate": rate * multiplier,
                "partition_key_strategy": strategy,
                "late_event_percent": float(late_events.get("percent", 0)),
            }
        )
    return tuple(result)


__all__ = ["compile_workload"]
