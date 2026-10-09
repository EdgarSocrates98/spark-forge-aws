from __future__ import annotations

from sparkforge_aws.agentic.governor import (
    AgentGovernor,
    GovernorLimits,
    GovernorStatus,
)


def test_governor_resolves_all_27_profile_risk_status_combinations() -> None:
    decisions = AgentGovernor().matrix()
    assert len(decisions) == 27
    assert len({item.fingerprint for item in decisions}) == 27
    assert all(item.limits.max_tokens >= 0 for item in decisions)


def test_governor_is_deterministic_and_does_not_expand_budget() -> None:
    governor = AgentGovernor()
    requested = GovernorLimits(5, 3, 3, 32000)
    budget = {"max_total_tokens": 1000, "tokens_used": 900, "max_agents": 1}
    first = governor.resolve("deep", "high", "accepted", requested=requested, budget=budget)
    second = governor.resolve("deep", "high", "accepted", requested=requested, budget=budget)
    assert first.to_dict() == second.to_dict()
    assert first.limits.max_agents <= 1
    assert first.limits.max_tokens <= 100


def test_refused_status_is_named_and_bounded() -> None:
    decision = AgentGovernor().resolve("balanced", "low", GovernorStatus.REFUSED)
    assert decision.refused is True
    assert decision.limits.reason == "decision_status_refused"
    assert decision.limits.max_agents == 0
