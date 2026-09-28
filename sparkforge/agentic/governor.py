"""Deterministic risk/profile/status governance for agentic execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import yaml

from sparkforge.decision.fingerprint import digest


class GovernorProfile(str, Enum):
    ECONOMY = "economy"
    BALANCED = "balanced"
    DEEP = "deep"


class GovernorRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GovernorStatus(str, Enum):
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class GovernorLimits:
    max_agents: int
    max_debates: int
    max_retries: int
    max_tokens: int
    action: str = "allow"
    reason: str | None = None

    def __post_init__(self) -> None:
        if any(
            value < 0
            for value in (self.max_agents, self.max_debates, self.max_retries, self.max_tokens)
        ):
            raise ValueError("governor limits must be non-negative")

    def min_with(self, other: GovernorLimits) -> GovernorLimits:
        return GovernorLimits(
            max_agents=min(self.max_agents, other.max_agents),
            max_debates=min(self.max_debates, other.max_debates),
            max_retries=min(self.max_retries, other.max_retries),
            max_tokens=min(self.max_tokens, other.max_tokens),
            action=self.action if self.action != "allow" else other.action,
            reason=self.reason or other.reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_agents": self.max_agents,
            "max_debates": self.max_debates,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "action": self.action,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class GovernorDecision:
    profile: str
    risk: str
    status: str
    limits: GovernorLimits
    policy_version: str
    fingerprint: str

    @property
    def refused(self) -> bool:
        return self.limits.action == "refuse"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "risk": self.risk,
            "status": self.status,
            "limits": self.limits.to_dict(),
            "policy_version": self.policy_version,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class GovernorPolicy:
    policy_version: str
    profiles: dict[str, GovernorLimits]
    risk_caps: dict[str, GovernorLimits]
    statuses: dict[str, GovernorLimits]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> GovernorPolicy:
        if raw.get("schema_version") != 1:
            raise ValueError("unsupported governor schema_version")
        version = str(raw.get("policy_version", "")).strip()
        if not version:
            raise ValueError("policy_version is required")
        profiles = _limits_map(
            raw.get("profiles"), {item.value for item in GovernorProfile}, "profiles"
        )
        risk_caps = _limits_map(
            raw.get("risk_caps"), {item.value for item in GovernorRisk}, "risk_caps"
        )
        statuses = _limits_map(
            raw.get("status"), {item.value for item in GovernorStatus}, "status"
        )
        return cls(version, profiles, risk_caps, statuses)

    @classmethod
    def default(cls) -> GovernorPolicy:
        return cls(
            "agentic-control-v1",
            {
                "economy": GovernorLimits(1, 0, 1, 8000),
                "balanced": GovernorLimits(3, 1, 2, 16000),
                "deep": GovernorLimits(5, 2, 2, 32000),
            },
            {
                "low": GovernorLimits(5, 2, 2, 32000),
                "medium": GovernorLimits(3, 1, 1, 16000),
                "high": GovernorLimits(1, 0, 0, 8000),
            },
            {
                "accepted": GovernorLimits(64, 64, 64, 10**9),
                "unresolved": GovernorLimits(
                    1, 0, 0, 8000, "bounded_fallback", "decision_unresolved"
                ),
                "refused": GovernorLimits(0, 0, 0, 0, "refuse", "decision_status_refused"),
            },
        )

    @classmethod
    def from_yaml(cls, path: str) -> GovernorPolicy:
        raw = yaml.safe_load(open(path, encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("governor policy must be a mapping")
        return cls.from_mapping(raw)


class AgentGovernor:
    """Resolve a finite policy without increasing the caller's budget."""

    def __init__(self, policy: GovernorPolicy | None = None) -> None:
        self.policy = policy or GovernorPolicy.default()

    def resolve(
        self,
        profile: str | GovernorProfile,
        risk: str | GovernorRisk,
        status: str | GovernorStatus,
        *,
        requested: GovernorLimits | None = None,
        budget: Mapping[str, Any] | Any | None = None,
    ) -> GovernorDecision:
        profile_value = _profile_value(profile)
        risk_value = _risk_value(risk)
        status_value = _status_value(status)
        selected = self.policy.statuses[status_value]
        if selected.action == "refuse":
            limits = selected
        else:
            limits = self.policy.profiles[profile_value].min_with(self.policy.risk_caps[risk_value])
            limits = limits.min_with(selected)
            if requested is not None:
                limits = limits.min_with(requested)
            limits = limits.min_with(_remaining_budget(budget))
            if limits.max_tokens == 0 and status_value == GovernorStatus.ACCEPTED.value:
                limits = GovernorLimits(0, 0, 0, 0, "refuse", "governor_budget_exhausted")
        fingerprint = digest(
            {
                "policy_version": self.policy.policy_version,
                "profile": profile_value,
                "risk": risk_value,
                "status": status_value,
                "limits": limits.to_dict(),
            }
        )
        return GovernorDecision(
            profile_value,
            risk_value,
            status_value,
            limits,
            self.policy.policy_version,
            fingerprint,
        )

    def matrix(self) -> tuple[GovernorDecision, ...]:
        return tuple(
            self.resolve(profile, risk, status)
            for profile in GovernorProfile
            for risk in GovernorRisk
            for status in GovernorStatus
        )


def _limits_map(raw: Any, expected: set[str], label: str) -> dict[str, GovernorLimits]:
    if not isinstance(raw, Mapping) or set(raw) != expected:
        raise ValueError(f"{label} must declare exactly: {', '.join(sorted(expected))}")
    result = {}
    for key, value in raw.items():
        if not isinstance(value, Mapping):
            raise ValueError(f"{label}.{key} must be a mapping")
        result[str(key)] = GovernorLimits(
            int(value.get("max_agents", 0)),
            int(value.get("max_debates", 0)),
            int(value.get("max_retries", 0)),
            int(value.get("max_tokens", 0)),
            str(value.get("action", "allow")),
            str(value["reason"]) if value.get("reason") is not None else None,
        )
    return result


def _profile_value(value: str | GovernorProfile) -> str:
    raw = value.value if isinstance(value, GovernorProfile) else str(value)
    return {"eco": "economy", "quality": "deep"}.get(raw, raw)


def _risk_value(value: str | GovernorRisk) -> str:
    raw = value.value if isinstance(value, GovernorRisk) else str(value)
    return {
        "read_only": "low",
        "reversible": "low",
        "sensitive": "medium",
        "destructive": "high",
    }.get(raw, raw)


def _status_value(value: str | GovernorStatus) -> str:
    raw = value.value if isinstance(value, GovernorStatus) else str(value)
    return "unresolved" if raw == "abstain" else raw


def _remaining_budget(budget: Mapping[str, Any] | Any | None) -> GovernorLimits:
    if budget is None:
        return GovernorLimits(64, 64, 64, 10**9)
    def value(name: str, default: int) -> int:
        if isinstance(budget, Mapping):
            return int(budget.get(name, default))
        return int(getattr(budget, name, default))
    max_tokens = value("max_total_tokens", 10**9)
    tokens_used = value("tokens_used", 0)
    max_agents = value("max_agents", 64)
    agents_used = value("agents_spawned", 0)
    max_debates = value("max_debates", 64)
    debates_used = value("debates_held", 0)
    max_retries = value("max_retries", 64)
    retries_used = value("retries_used", 0)
    return GovernorLimits(
        max(0, max_agents - agents_used),
        max(0, max_debates - debates_used),
        max(0, max_retries - retries_used),
        max(0, max_tokens - tokens_used),
    )


__all__ = [
    "AgentGovernor",
    "GovernorDecision",
    "GovernorLimits",
    "GovernorPolicy",
    "GovernorProfile",
    "GovernorRisk",
    "GovernorStatus",
]
