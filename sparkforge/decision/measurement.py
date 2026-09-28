"""Local measurement helpers with explicit provider-token separation."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from time import perf_counter_ns
from typing import Any, TypeVar

from sparkforge.decision.models import LocalMeasurement

T = TypeVar("T")


def payload_bytes(value: Any) -> int:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return len(encoded)


def measure_call(raw_state: Mapping[str, Any], call: Callable[[], T]) -> tuple[T, LocalMeasurement]:
    started = perf_counter_ns()
    result = call()
    return result, LocalMeasurement(
        latency_ns=perf_counter_ns() - started,
        payload_bytes=payload_bytes(raw_state),
    )


__all__ = ["measure_call", "payload_bytes"]
