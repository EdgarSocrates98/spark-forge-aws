"""Unified, evidence-preserving token and cost ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    run_id: str
    actor_id: str
    kind: str
    estimated_tokens: int = 0
    observed_tokens: int | None = None
    estimated_tool_calls: int = 0
    observed_tool_calls: int | None = None
    estimated_time_ms: float = 0.0
    observed_time_ms: float | None = None
    estimated_cost_usd: float | None = None
    observed_cost_usd: float | None = None
    provider: str = ""
    model: str = ""
    cost_basis: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.actor_id.strip() or not self.kind.strip():
            raise ValueError("LedgerEvent exige run_id, actor_id e kind")
        if self.estimated_cost_usd is not None and not self.cost_basis:
            raise ValueError("estimated_cost_usd exige cost_basis")
        if self.observed_cost_usd is not None and not self.cost_basis:
            raise ValueError("observed_cost_usd exige cost_basis")

    def to_dict(self) -> dict[str, Any]:
        result = {
            "run_id": self.run_id,
            "actor_id": self.actor_id,
            "kind": self.kind,
            "estimated_tokens": self.estimated_tokens,
            "observed_tokens": self.observed_tokens,
            "estimated_tool_calls": self.estimated_tool_calls,
            "observed_tool_calls": self.observed_tool_calls,
            "estimated_time_ms": self.estimated_time_ms,
            "observed_time_ms": self.observed_time_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "observed_cost_usd": self.observed_cost_usd,
            "provider": self.provider,
            "model": self.model,
            "cost_basis": self.cost_basis,
            "timestamp": self.timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "metadata": dict(self.metadata),
        }
        return result


@dataclass(frozen=True, slots=True)
class Reconciliation:
    metric: str
    estimated: int | float | None
    observed: int | float | None
    delta: int | float | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "estimated": self.estimated, "observed": self.observed, "delta": self.delta, "status": self.status}


class TokenLedger:
    """One in-memory ledger that can be flushed by the caller at a boundary."""

    def __init__(self, events: Iterable[LedgerEvent] = ()) -> None:
        self._events = list(events)

    def append(self, event: LedgerEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def for_run(self, run_id: str) -> "TokenLedger":
        return TokenLedger(event for event in self._events if event.run_id == run_id)

    def reconcile(self) -> dict[str, Any]:
        fields = (
            ("tokens", "estimated_tokens", "observed_tokens"),
            ("tool_calls", "estimated_tool_calls", "observed_tool_calls"),
            ("time_ms", "estimated_time_ms", "observed_time_ms"),
            ("cost_usd", "estimated_cost_usd", "observed_cost_usd"),
        )
        output: dict[str, Any] = {"events": len(self._events), "metrics": {}}
        for name, estimate_field, observed_field in fields:
            estimated_values = [getattr(event, estimate_field) for event in self._events if getattr(event, estimate_field) is not None]
            observed_values = [getattr(event, observed_field) for event in self._events if getattr(event, observed_field) is not None]
            estimated = sum(estimated_values) if estimated_values else None
            observed = sum(observed_values) if observed_values else None
            if observed is None:
                status = "tokens_unresolved" if name == "tokens" else "observed_unresolved"
                delta = None
            else:
                delta = observed - (estimated or 0)
                status = "measured"
            if name == "cost_usd" and observed is not None and any(not event.cost_basis for event in self._events):
                status = "cost_basis_unresolved"
            output["metrics"][name] = Reconciliation(name, estimated, observed, delta, status).to_dict()
        output["provider_tokens"] = output["metrics"]["tokens"]["observed"] if output["metrics"]["tokens"]["status"] == "measured" else "tokens_unresolved"
        return output

    def to_jsonl(self) -> str:
        return "".join(json.dumps(event.to_dict(), ensure_ascii=True, sort_keys=True) + "\n" for event in self._events)


@dataclass(frozen=True, slots=True)
class ProviderPriceProfile:
    provider: str
    model: str
    effective_date: str
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None
    cached_input_usd_per_million: float | None = None
    cache_creation_usd_per_million: float | None = None
    reasoning_usd_per_million: float | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("ProviderPriceProfile exige source")

    def cost(self, *, input_tokens: int = 0, output_tokens: int = 0, cached_input_tokens: int = 0, cache_creation_tokens: int = 0, reasoning_tokens: int = 0) -> float | None:
        rates = (
            (input_tokens, self.input_usd_per_million),
            (output_tokens, self.output_usd_per_million),
            (cached_input_tokens, self.cached_input_usd_per_million),
            (cache_creation_tokens, self.cache_creation_usd_per_million),
            (reasoning_tokens, self.reasoning_usd_per_million),
        )
        if any(tokens and rate is None for tokens, rate in rates):
            return None
        return round(sum(tokens * rate / 1_000_000 for tokens, rate in rates if rate is not None), 8)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "effective_date": self.effective_date,
            "input_usd_per_million": self.input_usd_per_million,
            "output_usd_per_million": self.output_usd_per_million,
            "cached_input_usd_per_million": self.cached_input_usd_per_million,
            "cache_creation_usd_per_million": self.cache_creation_usd_per_million,
            "reasoning_usd_per_million": self.reasoning_usd_per_million,
            "source": self.source,
        }


__all__ = ["LedgerEvent", "ProviderPriceProfile", "Reconciliation", "TokenLedger"]
