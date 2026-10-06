from pathlib import Path

import pytest

from sparkforge_aws.decision.contracts import ContractLoader, ContractValidationError


def _contract(**changes):
    value = {
        "schema_version": 1,
        "contract_id": "test.contract",
        "contract_version": "1",
        "mode": "shadow",
        "primitive": "choice",
        "state": {"required": [{"name": "choice", "type": "string"}]},
        "spec": {"options": ["a", "b"], "threshold": 0.5},
        "budget": {"max_input_bytes": 100, "cache_max_entries": 2},
    }
    value.update(changes)
    return value


def test_valid_contract_has_digest_and_bounds():
    contract = ContractLoader().parse(_contract())
    assert len(contract.sha256) == 64
    assert contract.cache_max_entries == 2


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"primitive": "python"}, "unknown primitive"),
        ({"spec": {"options": ["a", "a"]}}, "options must be unique"),
        ({"spec": {"options": ["a"], "threshold": 2}}, "between 0 and 1"),
        ({"spec": {"options": ["a"], "secret_policy": "ignore"}}, "unknown choice spec"),
        ({"unknown": True}, "unknown contract fields"),
    ],
)
def test_invalid_contract_fails_closed(changes, message):
    with pytest.raises(ContractValidationError, match=message):
        ContractLoader().parse(_contract(**changes))


def test_loader_confines_contract_path(tmp_path: Path):
    with pytest.raises(ContractValidationError, match="invalid"):
        ContractLoader(tmp_path, tmp_path / "config" / "decisions").load("../outside")
