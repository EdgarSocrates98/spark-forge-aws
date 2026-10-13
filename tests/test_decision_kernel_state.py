from sparkforge_aws.decision.contracts import ContractLoader
from sparkforge_aws.decision.models import DecisionStatus
from sparkforge_aws.decision.runtime import BoundedDecisionKernel
from sparkforge_aws.decision.state import StateCompiler


def _contract():
    return ContractLoader().parse(
        {
            "schema_version": 1,
            "contract_id": "test.state",
            "contract_version": "1",
            "mode": "shadow",
            "primitive": "choice",
            "state": {
                "required": [
                    {"name": "choice", "type": "string"},
                    {"name": "evidence", "type": "array", "order_insensitive": True},
                ]
            },
            "spec": {"options": ["safe"]},
        }
    )


def test_order_insensitive_state_compiles_identically():
    contract = _contract()
    first = StateCompiler().compile(contract, {"choice": "safe", "evidence": ["b", "a"]})
    second = StateCompiler().compile(contract, {"evidence": ["a", "b"], "choice": "safe"})
    assert first == second


def test_missing_required_state_is_unresolved_without_inference():
    evaluation = BoundedDecisionKernel().evaluate(_contract(), {"evidence": ["a"]})
    assert evaluation.result.status is DecisionStatus.UNRESOLVED
    assert evaluation.result.reason == "missing_state.choice"
