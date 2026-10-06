"""Stop policy — expected gain over observed state (§85-88).

Before spending on a new agent, review, debate, retrieval level, model
escalation or context expansion, the circuit asks whether the expected
gain justifies the cost. The evaluation is deterministic: a declared
policy over observed signals, never a pseudo-ML formula (§86).

Signals (§87) are inputs measured elsewhere — evidence gaps, uncertainty,
contradictions, role coverage, agent disagreement, novel evidence
potential, remaining budget, task risk. Nothing here invents them:
absent measurements stay absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class StopAction(str, Enum):
    """Vocabulary of §88 — what the gate can return."""

    STOP_SUFFICIENT = "stop_sufficient"
    STOP_BUDGET = "stop_budget"
    STOP_NO_GAIN = "stop_no_gain"
    STOP_SECURITY = "stop_security"
    STOP_UNRESOLVED = "stop_unresolved"
    CONTINUE = "continue"
    REVIEW = "review"
    DEBATE = "debate"
    HUMAN = "human"


PENDING_ACTIONS = frozenset(
    {
        "agent",
        "review",
        "debate",
        "retrieval",
        "model_escalation",
        "context_expansion",
    }
)


@dataclass(frozen=True, slots=True)
class ExpectedGainState:
    """Observed state at the moment of the decision (§87).

    Every field is measured or declared upstream; `None` means the signal
    was never measured — it does not count as zero.
    """

    pending_action: str
    evidence_gaps: int = 0
    uncertainty: int = 0
    contradictions: int = 0
    role_coverage: float | None = None
    agent_disagreement: bool = False
    novel_evidence_potential: bool = False
    remaining_budget: int | None = None
    task_risk: str = "low"
    security_flag: bool = False
    unresolved_required: bool = False

    def __post_init__(self) -> None:
        if self.evidence_gaps < 0 or self.uncertainty < 0 or self.contradictions < 0:
            raise ValueError("gain signals must be non-negative")
        if self.remaining_budget is not None and self.remaining_budget < 0:
            raise ValueError("remaining_budget must be non-negative")
        if self.role_coverage is not None and not 0.0 <= self.role_coverage <= 1.0:
            raise ValueError("role_coverage must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class StopDecision:
    """Gate output: action, machine-readable reason and the state seen."""

    action: StopAction
    reason: str
    pending_action: str

    @property
    def stops(self) -> bool:
        return self.action in _STOP_ACTIONS

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "pending_action": self.pending_action,
            "stops": self.stops,
        }


_STOP_ACTIONS = frozenset(
    {
        StopAction.STOP_SUFFICIENT,
        StopAction.STOP_BUDGET,
        StopAction.STOP_NO_GAIN,
        StopAction.STOP_SECURITY,
        StopAction.STOP_UNRESOLVED,
    }
)


@dataclass(frozen=True, slots=True)
class StopPolicy:
    """Deterministic expected-gain gate (§85-88).

    `budget_floor` is the remaining-budget threshold under which a
    high-risk task escalates to HUMAN instead of spending more.
    """

    budget_floor: int = 100

    def evaluate(self, state: ExpectedGainState) -> StopDecision:
        action = state.pending_action
        if action not in PENDING_ACTIONS:
            raise ValueError(
                f"pending_action must be one of {sorted(PENDING_ACTIONS)}"
            )
        if state.security_flag:
            return self._d(StopAction.STOP_SECURITY, "security_flag", action)
        if state.unresolved_required:
            return self._d(StopAction.STOP_UNRESOLVED, "required_state_unresolved", action)
        if state.remaining_budget == 0:
            return self._d(StopAction.STOP_BUDGET, "budget_exhausted", action)
        debate_warranted = (
            state.contradictions > 0
            or state.agent_disagreement
            or state.task_risk == "high"
        )
        if action == "debate":
            if debate_warranted:
                return self._d(StopAction.DEBATE, "debate_warranted", action)
            return self._d(StopAction.STOP_NO_GAIN, "debate_not_warranted", action)
        if debate_warranted and (state.contradictions > 0 or state.agent_disagreement):
            return self._d(StopAction.DEBATE, "disagreement_needs_debate", action)
        if state.evidence_gaps == 0 and not state.novel_evidence_potential:
            return self._d(StopAction.STOP_SUFFICIENT, "no_gap_no_novel_evidence", action)
        if (
            state.task_risk == "high"
            and state.remaining_budget is not None
            and state.remaining_budget <= self.budget_floor
        ):
            return self._d(StopAction.HUMAN, "high_risk_thin_budget", action)
        if state.evidence_gaps > 0:
            if state.novel_evidence_potential:
                return self._d(StopAction.CONTINUE, "gaps_with_novel_evidence", action)
            return self._d(StopAction.REVIEW, "gaps_without_novel_evidence", action)
        return self._d(StopAction.CONTINUE, "default_continue", action)

    @staticmethod
    def _d(action: StopAction, reason: str, pending: str) -> StopDecision:
        return StopDecision(action, reason, pending)


__all__ = [
    "ExpectedGainState",
    "PENDING_ACTIONS",
    "StopAction",
    "StopDecision",
    "StopPolicy",
]
