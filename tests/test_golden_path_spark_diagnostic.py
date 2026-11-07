"""Contrato executável do golden path de diagnóstico Spark.

O teste separa replay determinístico de execução ao vivo e de verificação
independente. Ele nunca acessa AWS, Spark ou rede.
"""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from sparkforge_aws.facts.pyspark_ast import extract_tree
from sparkforge_aws.findings.validate import validate_fact, validate_finding
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "golden-paths" / "spark-diagnostic.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_fixture(fixture: dict):
    directory = ROOT / Path(fixture["input"])
    meta = yaml.safe_load((directory / ".." / "meta.yaml").read_text(encoding="utf-8"))
    facts = list(extract_tree(directory, repo_root=directory))
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return facts, findings, skipped


def _expected(fixture: dict, field: str):
    return json.loads((ROOT / fixture[field]).read_text(encoding="utf-8"))


def test_contract_has_explicit_non_live_evidence_states():
    contract = _contract()
    assert contract["evidence_states"] == [
        "PREPARED",
        "REPLAY_VERIFIED",
        "LIVE_EXECUTED",
        "INDEPENDENTLY_VERIFIED",
    ]
    assert contract["evidence"]["replay"]["status"] == "VERIFIED"
    assert contract["evidence"]["live"]["status"] == "NOT_RUN"
    assert contract["evidence"]["independent"]["status"] == "NOT_RUN"
    assert contract["evidence"]["live"]["claims"] == []
    assert contract["evidence"]["independent"]["claims"] == []


@pytest.mark.parametrize("fixture_name", ["positive", "negative"])
def test_fixture_hashes_and_oracles_are_verified(fixture_name):
    fixture = _contract()["fixtures"][fixture_name]
    for relative_path, expected_hash in fixture["sha256"].items():
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert _sha256(path) == expected_hash, relative_path

    facts, findings, _skipped = _run_fixture(fixture)
    assert [fact.to_dict() for fact in facts] == _expected(fixture, "expected_facts")
    assert [finding.to_dict() for finding in findings] == _expected(fixture, "expected_findings")
    assert sorted({finding.rule_id for finding in findings}) == fixture["expected_rule_ids"]
    for fact in facts:
        validate_fact(fact.to_dict())
    for finding in findings:
        validate_finding(finding.to_dict())


def test_negative_fixture_is_a_real_no_finding_guard():
    fixture = _contract()["fixtures"]["negative"]
    _, findings, _ = _run_fixture(fixture)
    assert findings == []


def test_missing_input_is_unresolved_and_never_promoted():
    contract = _contract()
    missing = ROOT / "fixtures" / "pyspark" / "__missing_golden_path_input__"
    assert not missing.exists()
    assert contract["failure_policy"]["missing_input"] == "UNRESOLVED"
    assert contract["evidence"]["replay"]["status"] == "VERIFIED"
    assert contract["evidence"]["live"]["status"] == "NOT_RUN"
