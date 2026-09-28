"""Fail-closed activation guard for the Decision Plane."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActivationEvidence:
    labeled_tasks: int
    quality_gate: bool
    economy_gate: bool

    def __post_init__(self) -> None:
        if self.labeled_tasks < 0:
            raise ValueError("labeled_tasks must be non-negative")


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    allowed: bool
    mode: str
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "unresolved": list(self.unresolved),
        }


def guard_activation(
    mode: str,
    evidence: ActivationEvidence,
    *,
    minimum_labeled_tasks: int = 50,
) -> ActivationDecision:
    """Allow shadow mode and refuse every incomplete activation request."""
    normalized_mode = mode.strip().lower()
    if normalized_mode == "shadow":
        return ActivationDecision(True, normalized_mode)
    if normalized_mode != "active":
        return ActivationDecision(False, normalized_mode, ("unsupported_activation_mode",))
    missing: list[str] = []
    if evidence.labeled_tasks < minimum_labeled_tasks:
        missing.append("activation_corpus_below_50_labeled_tasks")
    if not evidence.quality_gate:
        missing.append("activation_quality_gate_missing")
    if not evidence.economy_gate:
        missing.append("activation_economy_gate_missing")
    if not missing:
        return ActivationDecision(True, normalized_mode)
    return ActivationDecision(False, normalized_mode, tuple(missing))


__all__ = ["ActivationDecision", "ActivationEvidence", "guard_activation"]
