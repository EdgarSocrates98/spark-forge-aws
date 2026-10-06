"""Typed contracts for the provider-independent Context Gateway."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

AnswerStatus = Literal["resolved", "partial", "unavailable"]


class GatewayProfile(str, Enum):
    ECONOMY = "economy"
    BALANCED = "balanced"
    DEEP = "deep"


class GatewayPhase(str, Enum):
    REQUESTED = "requested"
    DISCOVERED = "discovered"
    SELECTED = "selected"
    REDUCED = "reduced"
    MATERIALIZED = "materialized"
    EXPANDED = "expanded"


@dataclass(frozen=True, slots=True)
class AnswerState:
    status: AnswerStatus
    reasons: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "triggers": list(self.triggers),
        }


@dataclass(frozen=True, slots=True)
class GatewayRequest:
    """Validated request entering the deterministic Gateway."""

    intent: str
    profile: GatewayProfile
    max_bytes: int | None = None
    case_id: str | None = None
    items: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    host_usage: Mapping[str, Any] | None = None
    answer_status: AnswerStatus | None = None
    answer_reasons: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    role: str | None = None
    role_plan: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.intent.strip():
            raise ValueError("intent must not be empty")
        if not isinstance(self.profile, GatewayProfile):
            object.__setattr__(self, "profile", GatewayProfile(str(self.profile)))
        if self.max_bytes is None:
            from sparkforge.context.gateway_capabilities import load_profiles

            object.__setattr__(self, "max_bytes", load_profiles()[self.profile].default_max_bytes)
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if self.answer_status is not None and self.answer_status not in {
            "resolved",
            "partial",
            "unavailable",
        }:
            raise ValueError(f"invalid answer_status: {self.answer_status}")
        object.__setattr__(self, "items", tuple(dict(item) for item in self.items))
        object.__setattr__(self, "answer_reasons", tuple(str(item) for item in self.answer_reasons))
        object.__setattr__(self, "triggers", tuple(str(item) for item in self.triggers))
        if self.role_plan is not None and not isinstance(self.role_plan, Mapping):
            raise ValueError("role_plan must be a serialized RoleContextPlan mapping")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> GatewayRequest:
        items = raw.get("items", ())
        if not isinstance(items, (list, tuple)):
            raise ValueError("items must be an array")
        return cls(
            intent=str(raw.get("intent", "")),
            profile=GatewayProfile(str(raw.get("profile", GatewayProfile.BALANCED.value))),
            max_bytes=(int(raw["max_bytes"]) if raw.get("max_bytes") is not None else None),
            case_id=raw.get("case_id"),
            items=tuple(item for item in items if isinstance(item, Mapping)),
            host_usage=raw.get("host_usage"),
            answer_status=raw.get("answer_status"),
            answer_reasons=tuple(raw.get("answer_reasons", ())),
            triggers=tuple(raw.get("triggers", ())),
            role=raw.get("role"),
            role_plan=raw.get("role_plan"),
        )


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    kind: str
    score: int
    description: str = ""
    domains: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "score": self.score,
            "description": self.description,
            "domains": list(self.domains),
        }


@dataclass(frozen=True, slots=True)
class ContextRef:
    uri: str
    kind: str
    sha256: str
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "kind": self.kind,
            "sha256": self.sha256,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ContextItem:
    id: str
    kind: str
    relevance: int
    critical: bool
    payload: Mapping[str, Any]
    ref: ContextRef | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "relevance": self.relevance,
            "critical": self.critical,
        }
        if self.ref is not None:
            result["ref"] = self.ref.to_dict()
        else:
            result["payload"] = dict(self.payload)
        return result


@dataclass(frozen=True, slots=True)
class BudgetReport:
    max_bytes: int
    payload_bytes: int
    status: str
    reductions: tuple[str, ...] = ()
    paginated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_bytes": self.max_bytes,
            "payload_bytes": self.payload_bytes,
            "status": self.status,
            "reductions": list(self.reductions),
            "paginated": self.paginated,
            "unit": "serialized_utf8_json_bytes",
        }


@dataclass(frozen=True, slots=True)
class Unresolved:
    code: str
    message: str
    unlock: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.unlock is not None:
            result["unlock"] = self.unlock
        return result


@dataclass(frozen=True, slots=True)
class GatewayResponse:
    status: str
    phase: GatewayPhase
    request_id: str
    profile: GatewayProfile
    capabilities: tuple[Capability, ...]
    context: tuple[ContextItem, ...]
    refs: tuple[ContextRef, ...]
    budget: BudgetReport
    unresolved: tuple[Unresolved, ...] = ()
    reductions: tuple[str, ...] = ()
    host_usage: Mapping[str, Any] | None = None
    error: str | None = None
    answer_state: AnswerState | None = None
    query_expansion: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": 1,
            "status": self.status,
            "phase": self.phase.value,
            "request_id": self.request_id,
            "profile": self.profile.value,
            "capabilities": [item.to_dict() for item in self.capabilities],
            "context": [item.to_dict() for item in self.context],
            "refs": [item.to_dict() for item in self.refs],
            "budget": self.budget.to_dict(),
            "reductions": list(self.reductions),
            "unresolved": [item.to_dict() for item in self.unresolved],
            "provider_tokens": self.host_usage,
        }
        if self.answer_state is not None:
            result["answer_state"] = self.answer_state.to_dict()
        if self.query_expansion is not None:
            result["query_expansion"] = dict(self.query_expansion)
        if self.error is not None:
            result["error"] = self.error
        return result


def mapping_copy(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})
