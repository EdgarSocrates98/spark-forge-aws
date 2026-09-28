from __future__ import annotations

import pytest

from sparkforge.decision.contracts import ContractLoader, ContractValidationError
from sparkforge.decision.state import StateCompiler


def _contract(**changes):
    value = {
        "schema_version": 1,
        "contract_id": "hardening.contract",
        "contract_version": "1",
        "mode": "shadow",
        "primitive": "route",
        "state": {"required": [{"name": "signal", "type": "string"}]},
        "spec": {
            "rules": [
                {
                    "when": [{"field": "signal", "equals": "safe"}],
                    "route": "local",
                    "confidence": 0.9,
                }
            ],
            "default": "abstain",
            "default_confidence": 0.2,
        },
    }
    value.update(changes)
    return value


def test_state_compiler_rejects_extra_fields_by_default():
    contract = ContractLoader().parse(_contract())
    compiled = StateCompiler().compile(contract, {"signal": "safe", "secret": "x"})
    assert "undeclared_state.secret" in compiled.unresolved
    assert "secret" not in compiled.as_dict()


def test_optional_state_is_not_unresolved_when_absent():
    contract = ContractLoader().parse(
        _contract(
            state={
                "required": [{"name": "signal", "type": "string"}],
                "optional": [{"name": "trace", "type": "string"}],
            }
        )
    )
    compiled = StateCompiler().compile(contract, {"signal": "safe"})
    assert compiled.resolved
    assert contract.required_state_fields == ("signal",)


def test_referenced_field_must_be_declared():
    with pytest.raises(ContractValidationError, match="referenced_fields_undeclared"):
        ContractLoader().parse(
            _contract(
                spec={
                    "rules": [
                        {
                            "when": [{"field": "undeclared", "truthy": True}],
                            "route": "local",
                        }
                    ]
                }
            )
        )


@pytest.mark.parametrize(
    "spec, message",
    [
        (
            {
                "rules": [
                    {
                        "when": [{"field": "signal", "equals": "safe", "truthy": True}],
                        "route": "local",
                    }
                ]
            },
            "exactly one operator",
        ),
        (
            {"rules": [{"when": [{"field": "signal", "in": "safe"}], "route": "local"}]},
            "must be a non-empty list",
        ),
        (
            {
                "rules": [
                    {
                        "when": [{"field": "signal", "equals": "safe"}],
                        "route": "local",
                        "confidence": 1.1,
                    }
                ]
            },
            "between 0 and 1",
        ),
    ],
)
def test_route_condition_and_confidence_validation(spec, message):
    with pytest.raises(ContractValidationError, match=message):
        ContractLoader().parse(_contract(spec=spec))


def test_gate_uses_same_condition_schema():
    contract = _contract(
        primitive="gate",
        state={"required": [{"name": "ready", "type": "boolean"}]},
        spec={"requirements": [{"field": "ready", "truthy": True}], "on_pass": "open"},
    )
    assert ContractLoader().parse(contract).referenced_fields() == ("ready",)
