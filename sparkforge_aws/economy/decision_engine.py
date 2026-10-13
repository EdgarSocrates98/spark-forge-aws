"""Pure deterministic evaluation of versioned Decision Plane contracts."""

from __future__ import annotations

from collections.abc import Iterable

from sparkforge_aws.decision.cache import DecisionCache
from sparkforge_aws.economy.decision_contracts import Candidate, DecisionContract
from sparkforge_aws.economy.decision_kernel_bridge import evaluate_legacy
from sparkforge_aws.economy.decision_models import DecisionInput, DecisionResult


class DeterministicDecisionEngine:
    """Evaluate declared predicates without dispatching work."""

    def __init__(self) -> None:
        self._cache = DecisionCache(max_entries=128)

    def evaluate(self, contract: DecisionContract, state: DecisionInput) -> DecisionResult:
        return evaluate_legacy(contract, state, cache=self._cache)


def candidate_routes(candidates: Iterable[Candidate]) -> tuple[str, ...]:
    """Return declared routes in stable contract order for diagnostics."""
    return tuple(
        candidate.route for candidate in sorted(candidates, key=lambda item: item.priority)
    )


__all__ = ["DeterministicDecisionEngine", "candidate_routes"]
