"""Deterministic context and token accounting tree."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sparkforge.context.gateway_budget import serialized_bytes
from sparkforge.context.host_usage import HostTokenState


@dataclass(frozen=True, slots=True)
class ContextTreeEntry:
    name: str
    payload_bytes: int
    item_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "payload_bytes": self.payload_bytes,
            "item_count": self.item_count,
        }


def _entry(name: str, value: Any) -> ContextTreeEntry:
    count = len(value) if isinstance(value, (list, tuple, dict)) else 1
    return ContextTreeEntry(name, serialized_bytes(value), count)


def build_context_tree(
    payload: Mapping[str, Any],
    *,
    host_tokens: HostTokenState | None = None,
) -> dict[str, Any]:
    """Return bytes by envelope component without mixing token units."""
    components = [
        _entry(name, payload.get(name, []))
        for name in ("capabilities", "context", "refs", "budget", "unresolved", "reductions")
        if name in payload
    ]
    state = host_tokens or HostTokenState.unresolved("transcript_unavailable")
    critical_items = sum(
        1
        for item in payload.get("context", [])
        if isinstance(item, Mapping)
        and (
            item.get("critical")
            or item.get("kind") in {"fact", "finding", "rule", "risk"}
        )
    )
    return {
        "schema_version": 1,
        "unit": "serialized_utf8_json_bytes",
        "payload_bytes": serialized_bytes(payload),
        "components": [item.to_dict() for item in components],
        "critical_items": critical_items,
        "unresolved_count": len(payload.get("unresolved", []))
        if isinstance(payload.get("unresolved", []), list)
        else 0,
        "tokens": state.to_dict(),
    }


__all__ = ["ContextTreeEntry", "build_context_tree"]
