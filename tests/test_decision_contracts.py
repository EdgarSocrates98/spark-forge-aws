from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge_aws.economy.decision_contracts import ContractError, ContractRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_contract_loads_with_stable_digest_and_version() -> None:
    registry = ContractRegistry(ROOT)

    first = registry.load("routing.data_domain", "1")
    second = registry.load("routing.data_domain", "1")

    assert first.contract_id == "routing.data_domain"
    assert first.sha256 == second.sha256
    assert first.budget.max_total_tokens == 8000


def test_invalid_contract_is_named_refusal(tmp_path: Path) -> None:
    directory = tmp_path / "config" / "decisions"
    directory.mkdir(parents=True)
    (directory / "bad.yaml").write_text(
        "schema_version: 1\ncontract_id: bad\ncontract_version: 1\nmode: shadow\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="candidates"):
        ContractRegistry(tmp_path).load("bad")


def test_unsupported_predicate_fails_closed(tmp_path: Path) -> None:
    directory = tmp_path / "config" / "decisions"
    directory.mkdir(parents=True)
    (directory / "bad.yaml").write_text(
        "schema_version: 1\ncontract_id: bad\ncontract_version: 1\nmode: shadow\n"
        "budget: {max_total_tokens: 1, max_tool_calls: 1}\n"
        "thresholds: {default: 0.5}\n"
        "candidates: [{name: x, route: x, predicates: [{name: unsafe}]}]\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="unsupported predicate"):
        ContractRegistry(tmp_path).load("bad")
