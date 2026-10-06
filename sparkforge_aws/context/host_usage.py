"""Transcript-derived host token state for the provider-independent Gateway."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

TokenStatus = Literal["resolved", "unresolved"]


@dataclass(frozen=True, slots=True)
class HostTokenState:
    """Independent provider-token measurement and its provenance state."""

    status: TokenStatus
    source: str | None
    usage: dict[str, int] | None
    reason: str | None = None

    @classmethod
    def unresolved(cls, reason: str = "usage_field_absent") -> HostTokenState:
        return cls(status="unresolved", source=None, usage=None, reason=reason)

    @classmethod
    def from_transcript(
        cls, usage: Mapping[str, Any] | None, source: str | None
    ) -> HostTokenState:
        if not isinstance(usage, Mapping) or not source:
            return cls.unresolved("transcript_unavailable")
        values: dict[str, int] = {}
        for key, value in usage.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                continue
            values[str(key)] = value
        if not values:
            return cls.unresolved("usage_value_malformed")
        return cls(status="resolved", source=source, usage=values)

    @classmethod
    def from_facts(cls, facts: Iterable[Any]) -> HostTokenState:
        for fact in facts:
            kind = getattr(fact, "kind", None)
            if kind != "host.usage":
                continue
            measures = getattr(fact, "measures", None)
            provenance = getattr(fact, "provenance", None)
            source = None
            if isinstance(provenance, Mapping):
                source = provenance.get("artifact") or provenance.get("source")
            return cls.from_transcript(measures, str(source) if source else None)
        return cls.unresolved("usage_fact_absent")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "tokens_unresolved": self.status != "resolved",
        }
        if self.source is not None:
            result["source"] = self.source
        if self.usage is not None:
            result["provider_tokens"] = dict(self.usage)
        if self.reason is not None:
            result["reason"] = self.reason
        return result


__all__ = ["HostTokenState", "TokenStatus"]
