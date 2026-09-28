import pytest

from sparkforge.decision.contracts import ContractLoader
from sparkforge.decision.models import DecisionStatus, PrimitiveKind
from sparkforge.decision.primitives import evaluator_for


def _parse(primitive, spec, field, value):
    raw = {
        "schema_version": 1,
        "contract_id": f"test.{primitive}",
        "contract_version": "1",
        "mode": "shadow",
        "primitive": primitive,
        "state": {"required": [{"name": field, "type": "any"}]},
        "spec": spec,
    }
    return ContractLoader().parse(raw), {field: value}


@pytest.mark.parametrize(
    "primitive,spec,field,value,selected",
    [
        ("choice", {"options": ["a", "b"]}, "choice", "a", "a"),
        ("boolean", {"field": "enabled"}, "enabled", True, "true"),
        (
            "gate",
            {"requirements": [{"field": "ready", "equals": True}], "on_pass": "open"},
            "ready",
            True,
            "open",
        ),
        ("score", {"weights": {"score": 1}, "threshold": 0.5}, "score", 0.8, "score_pass"),
        (
            "route",
            {"rules": [{"when": [{"field": "signal", "equals": "safe"}], "route": "local"}]},
            "signal",
            "safe",
            "local",
        ),
        (
            "threshold",
            {"field": "score", "operator": "gte", "value": 10, "on_pass": "pass"},
            "score",
            10,
            "pass",
        ),
    ],
)
def test_each_primitive_accepts_declared_happy_path(primitive, spec, field, value, selected):
    contract, state = _parse(primitive, spec, field, value)
    outcome = evaluator_for(PrimitiveKind(primitive)).evaluate(contract, state)
    assert outcome.status is DecisionStatus.ACCEPTED
    assert outcome.selected == (selected,)


def test_threshold_boundary_abstains_and_missing_state_is_unresolved():
    contract, state = _parse(
        "threshold",
        {"field": "score", "operator": "gt", "value": 10, "on_pass": "pass"},
        "score",
        10,
    )
    outcome = evaluator_for(PrimitiveKind.THRESHOLD).evaluate(contract, state)
    assert outcome.status is DecisionStatus.ABSTAIN
    missing = evaluator_for(PrimitiveKind.THRESHOLD).evaluate(contract, {})
    assert missing.status is DecisionStatus.UNRESOLVED
