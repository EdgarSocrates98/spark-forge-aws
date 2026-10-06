"""Finite recovery policy for bounded agentic execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureClass(str, Enum):
    INVALID_INPUT = "invalid_input"
    SCHEMA_VALIDATION = "schema_validation"
    MISSING_EVIDENCE = "missing_evidence"
    BUDGET_EXCEEDED = "budget_exceeded"
    TRANSIENT_HOST = "transient_host"
    DETERMINISTIC_CONFLICT = "deterministic_conflict"
    STRATEGY_REJECTED = "strategy_rejected"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TOOL_FAILURE = "tool_failure"
    POLICY_CONFLICT = "policy_conflict"
    SECURITY_REFUSAL = "security_refusal"
    CONTEXT_INSUFFICIENT = "context_insufficient"
    LOOP = "loop"
    DEPENDENCY_FAILURE = "dependency_failure"


class RecoveryAction(str, Enum):
    REFUSE = "refuse"
    ABSTAIN = "abstain"
    FALLBACK_DETERMINISTIC = "fallback_deterministic"
    RETRY = "retry"
    ESCALATE = "escalate"
    REPLAN = "replan"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    failure_class: str
    action: str
    attempt: int
    reason: str
    strategy_fingerprint: str
    terminal: bool
    budget_consumed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_class": self.failure_class,
            "action": self.action,
            "attempt": self.attempt,
            "reason": self.reason,
            "strategy_fingerprint": self.strategy_fingerprint,
            "terminal": self.terminal,
            "budget_consumed": self.budget_consumed,
        }


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    max_attempts: int = 2
    actions: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        values = dict(self.actions or _DEFAULT_ACTIONS)
        expected = {item.value for item in FailureClass}
        if set(values) != expected:
            raise ValueError(
                "recovery policy must declare exactly "
                f"{len(expected)} failure classes"
            )
        allowed = {item.value for item in RecoveryAction}
        if any(value not in allowed for value in values.values()):
            raise ValueError("recovery policy contains unsupported action")
        object.__setattr__(self, "actions", values)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> RecoveryPolicy:
        block = raw.get("recovery", raw)
        if not isinstance(block, Mapping):
            raise ValueError("recovery policy must be a mapping")
        actions = block.get("failure_classes")
        if not isinstance(actions, Mapping):
            raise ValueError("recovery.failure_classes is required")
        return cls(
            int(block.get("max_attempts", 2)),
            {str(key): str(value) for key, value in actions.items()},
        )

    def next(
        self,
        failure: str | FailureClass,
        *,
        attempt: int,
        strategy_fingerprint: str,
        history: Sequence[str] = (),
    ) -> RecoveryDecision:
        failure_value = failure.value if isinstance(failure, FailureClass) else str(failure)
        if failure_value not in self.actions:
            raise ValueError(f"unknown failure class: {failure_value}")
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        configured = str(self.actions[failure_value])
        repeated = strategy_fingerprint in set(history)
        if repeated and configured in {RecoveryAction.RETRY.value, RecoveryAction.REPLAN.value}:
            action = RecoveryAction.STOP.value
            reason = "strategy_fingerprint_repeated"
            terminal = True
        elif configured == RecoveryAction.RETRY.value and attempt >= self.max_attempts:
            action = RecoveryAction.STOP.value
            reason = "retry_limit_exceeded"
            terminal = True
        else:
            action = configured
            reason = f"failure_class:{failure_value}"
            terminal = action in {
                RecoveryAction.REFUSE.value,
                RecoveryAction.ABSTAIN.value,
                RecoveryAction.FALLBACK_DETERMINISTIC.value,
                RecoveryAction.ESCALATE.value,
                RecoveryAction.STOP.value,
            }
        return RecoveryDecision(
            failure_value,
            action,
            attempt,
            reason,
            strategy_fingerprint,
            terminal,
        )


_DEFAULT_ACTIONS = {
    "invalid_input": "refuse",
    "schema_validation": "refuse",
    "missing_evidence": "abstain",
    "budget_exceeded": "fallback_deterministic",
    "transient_host": "retry",
    "deterministic_conflict": "escalate",
    "strategy_rejected": "replan",
    "timeout": "retry",
    "provider_unavailable": "retry",
    "tool_failure": "replan",
    "policy_conflict": "escalate",
    "security_refusal": "refuse",
    "context_insufficient": "replan",
    "loop": "stop",
    "dependency_failure": "escalate",
}


__all__ = ["FailureClass", "RecoveryAction", "RecoveryDecision", "RecoveryPolicy"]
