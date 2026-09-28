from sparkforge.decision.contracts import ContractLoader
from sparkforge.decision.fingerprint import decision_fingerprint
from sparkforge.decision.state import StateCompiler


def _raw(version="1", choice="safe"):
    return {
        "schema_version": 1,
        "contract_id": "test.fp",
        "contract_version": version,
        "mode": "shadow",
        "primitive": "choice",
        "state": {"required": [{"name": "choice", "type": "string"}]},
        "spec": {"options": ["safe", "fast"]},
        "_state": {"choice": choice},
    }


def test_same_semantics_are_stable_and_changes_invalidate():
    first = _raw()
    contract = ContractLoader().parse(
        {key: value for key, value in first.items() if key != "_state"}
    )
    state = StateCompiler().compile(contract, first["_state"])
    same = decision_fingerprint(contract, state)
    changed_contract = ContractLoader().parse(
        {
            **{key: value for key, value in first.items() if key != "_state"},
            "contract_version": "2",
        }
    )
    changed_state = StateCompiler().compile(contract, {"choice": "fast"})
    assert same == decision_fingerprint(contract, state)
    assert same != decision_fingerprint(changed_contract, state)
    assert same != decision_fingerprint(contract, changed_state)
