"""Deterministic serialized-byte packing for Gateway envelopes."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

REDUCTION_ORDER = (
    "auxiliary_prose",
    "duplicate_context",
    "verbose_provenance",
    "examples",
    "knowledge",
    "low_relevance_items",
    "pagination",
)
CRITICAL_KEYS = frozenset(
    {"error", "errors", "risks", "fact_id", "rule_id", "evidence_refs", "unresolved"}
)
CRITICAL_KINDS = frozenset({"fact", "finding", "rule", "error", "risk", "unresolved"})


class BudgetRefusal(ValueError):
    """Raised when critical content cannot fit the requested hard budget."""

    def __init__(self, message: str, *, required_bytes: int, max_bytes: int) -> None:
        super().__init__(message)
        self.required_bytes = required_bytes
        self.max_bytes = max_bytes


@dataclass(frozen=True, slots=True)
class PackedPayload:
    payload: dict[str, Any]
    payload_bytes: int
    reductions: tuple[str, ...]
    paginated: bool


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def serialized_bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def content_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _deduplicate(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = content_digest(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _critical(item: Any) -> bool:
    if not isinstance(item, Mapping):
        return False
    if bool(item.get("critical")) or str(item.get("kind", "")) in CRITICAL_KINDS:
        return True
    return any(key in item for key in CRITICAL_KEYS)


def _compact_provenance(payload: dict[str, Any]) -> None:
    provenance: dict[str, Any] = dict(payload.get("provenance", {}))
    for collection_name in ("context", "refs"):
        collection = payload.get(collection_name)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict) or "provenance" not in item:
                continue
            value = item.pop("provenance")
            ref = content_digest(value)[:16]
            provenance.setdefault(ref, value)
            item["provenance_ref"] = ref
    if provenance:
        payload["provenance"] = dict(sorted(provenance.items()))


def _reduce(payload: dict[str, Any], step: str) -> None:
    if step == "auxiliary_prose":
        for key in ("description", "summary", "explanation", "examples"):
            payload.pop(key, None)
        for item in payload.get("capabilities", []):
            if isinstance(item, dict):
                item["description"] = ""
    elif step == "duplicate_context":
        for key in ("context", "capabilities", "refs"):
            if isinstance(payload.get(key), list):
                payload[key] = _deduplicate(payload[key])
    elif step == "verbose_provenance":
        _compact_provenance(payload)
    elif step == "examples":
        payload.pop("examples", None)
        for item in payload.get("context", []):
            if isinstance(item, dict):
                item.pop("example", None)
    elif step == "knowledge":
        payload["context"] = [
            item for item in payload.get("context", [])
            if _critical(item) or str(item.get("kind", "")) != "knowledge"
        ]
    elif step == "low_relevance_items":
        context = payload.get("context", [])
        payload["context"] = [
            item for item in context if _critical(item) or int(item.get("relevance", 0)) >= 50
        ]
    elif step == "pagination":
        context = payload.get("context", [])
        payload["context"] = [item for item in context if _critical(item)]
        payload["pagination"] = {
            "omitted_context_items": max(0, len(context) - len(payload["context"]))
        }


def pack_payload(payload: Mapping[str, Any], max_bytes: int) -> PackedPayload:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    candidate = copy.deepcopy(dict(payload))
    current = serialized_bytes(candidate)
    if current <= max_bytes:
        return PackedPayload(candidate, current, (), False)
    applied: list[str] = []
    for step in REDUCTION_ORDER:
        _reduce(candidate, step)
        applied.append(step)
        current = serialized_bytes(candidate)
        if current <= max_bytes:
            return PackedPayload(candidate, current, tuple(applied), step == "pagination")
    critical_only = {
        key: value
        for key, value in candidate.items()
        if key in CRITICAL_KEYS
        or key in {"schema_version", "status", "phase", "request_id", "profile", "budget"}
    }
    current = serialized_bytes(critical_only)
    if current <= max_bytes:
        return PackedPayload(critical_only, current, tuple(applied), True)
    raise BudgetRefusal(
        "critical gateway content exceeds max_bytes; increase budget or request expansion",
        required_bytes=current,
        max_bytes=max_bytes,
    )
