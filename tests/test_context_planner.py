from __future__ import annotations

from sparkforge.context.planner import derive_triggers, plan_execution


def test_planner_derives_triggers_from_structured_evidence() -> None:
    triggers = derive_triggers(
        [
            {
                "kind": "finding",
                "attrs": {
                    "conflicting_rules": True,
                    "risk_level": "high",
                    "confidence": 0.2,
                },
            },
            {"kind": "unresolved", "code": "workspace_repository_unresolved"},
        ]
    )

    assert triggers == (
        "confidence_gap",
        "conflicting_rules",
        "high_risk_change",
        "unresolved_reference",
    )


def test_planner_prefers_deterministic_path_without_triggers() -> None:
    plan = plan_execution(has_deterministic_answer=True)

    assert plan.kind == "deterministic"
    assert plan.reason == "deterministic_first"


def test_planner_does_not_escalate_when_profile_disallows_it() -> None:
    plan = plan_execution(
        has_deterministic_answer=False,
        triggers={"conflicting_rules"},
        allow_agentic_escalation=False,
    )

    assert plan.kind == "unresolved"
    assert plan.reason == "agentic_escalation_disabled"


def test_planner_routes_conflicts_to_debate_when_enabled() -> None:
    plan = plan_execution(
        has_deterministic_answer=False,
        triggers={"conflicting_rules"},
        allow_agentic_escalation=True,
    )

    assert plan.kind == "debate"
    assert plan.reason == "escalation_triggered"


def test_planner_requires_explicit_resolved_state_for_deterministic_plan() -> None:
    plan = plan_execution(
        has_deterministic_answer=True,
        answer_status="partial",
        allow_agentic_escalation=False,
    )

    assert plan.kind == "unresolved"
    assert plan.reason == "partial_answer_escalation_disabled"
