import pytest

from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.validate import ValidationFailed, validate_fact, validate_finding


def good_finding(**over):
    base = {
        "rule_id": "SF-PY-005",
        "schema_version": 1,
        "catalog_version": 1,
        "title": "coalesce(1)",
        "severity": "P0",
        "confidence": "high",
        "status": "structural",
        "subject": {"type": "source_location", "file": "a.py", "line": 1},
        "evidence": ["f_abc123"],
        "measured": {},
        "threshold": {},
        "runtime_scope": {"glue": "*"},
        "explanation": "explica",
        "proposed_change": ["mudar"],
        "expected_effect": "",
        "benchmark_ref": "",
        "risks": [],
        "tradeoffs": [],
        "validation": ["contagem total"],
        "rollback": ["reverter"],
        "sources": [{"origin": "field-heuristic"}],
    }
    base.update(over)
    return base


class TestFactSchema:
    def test_extracted_facts_validate(self):
        for fact in extract_source("df.coalesce(1)\n", "a.py"):
            validate_fact(fact.to_dict())

    def test_fact_without_kind_is_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_fact({"id": "f_abc123", "schema_version": 1, "subject": {}})

    def test_fact_with_non_numeric_measure_is_rejected(self):
        bad = {
            "id": "f_abc123",
            "schema_version": 1,
            "kind": "k",
            "subject": {"type": "source_location"},
            "measures": {"n": "doze"},
            "attrs": {},
            "provenance": {},
        }
        with pytest.raises(ValidationFailed, match="measures"):
            validate_fact(bad)


class TestFindingSchema:
    def test_good_finding_validates(self):
        validate_finding(good_finding())

    def test_empty_evidence_rejected(self):
        with pytest.raises(ValidationFailed, match="evidence"):
            validate_finding(good_finding(evidence=[]))

    def test_unknown_severity_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_finding(good_finding(severity="BLOCKER"))

    def test_unknown_status_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_finding(good_finding(status="maybe"))


class TestNoInventedGains:
    """A regra que mata 'ganho de 40%' na origem."""

    @pytest.mark.parametrize(
        "effect",
        [
            "reduz o runtime em 40%",
            "ganho de 2x no tempo",
            "corta 30 % do custo",
            "melhora ~15%",
        ],
    )
    def test_quantified_effect_without_benchmark_is_rejected(self, effect):
        with pytest.raises(ValidationFailed, match="benchmark_ref"):
            validate_finding(good_finding(expected_effect=effect))

    def test_quantified_effect_with_benchmark_is_accepted(self):
        validate_finding(
            good_finding(
                expected_effect="reduz o runtime em 40%",
                benchmark_ref="bench/2026-07-29-coalesce.json",
            )
        )

    def test_qualitative_effect_without_benchmark_is_accepted(self):
        validate_finding(
            good_finding(expected_effect="hipotese: reduz o tempo do stage dominante")
        )
