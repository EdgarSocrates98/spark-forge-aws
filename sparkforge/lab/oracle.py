"""Independent expected-result oracle for Forge Lab runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OracleResult:
    classification: str
    expected_facts: tuple[str, ...]
    observed_facts: tuple[str, ...]
    missing_facts: tuple[str, ...]
    expected_findings: tuple[str, ...]
    observed_findings: tuple[str, ...]
    missing_findings: tuple[str, ...]
    forbidden_findings: tuple[str, ...]
    unresolved_expected: tuple[str, ...]
    unresolved_observed: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "expected_facts": list(self.expected_facts),
            "observed_facts": list(self.observed_facts),
            "missing_facts": list(self.missing_facts),
            "expected_findings": list(self.expected_findings),
            "observed_findings": list(self.observed_findings),
            "missing_findings": list(self.missing_findings),
            "forbidden_findings": list(self.forbidden_findings),
            "unresolved_expected": list(self.unresolved_expected),
            "unresolved_observed": list(self.unresolved_observed),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class ExpectedOracle:
    source: str
    expected_facts: tuple[str, ...]
    expected_findings: tuple[str, ...]
    forbidden_findings: tuple[str, ...]
    expected_unresolved: tuple[str, ...]
    predicates: tuple[str, ...]

    @classmethod
    def from_scenario(cls, scenario: Any) -> "ExpectedOracle":
        expected = scenario.expected
        return cls(
            source="scenario.expected",
            expected_facts=tuple(sorted(str(item) for item in expected.get("facts", []))),
            expected_findings=tuple(sorted(str(item) for item in expected.get("findings", []))),
            forbidden_findings=tuple(sorted(str(item) for item in expected.get("must_not_find", expected.get("forbidden", [])))),
            expected_unresolved=tuple(sorted(str(item) for item in expected.get("unresolved", []))),
            predicates=tuple(sorted(str(item) for item in expected.get("predicates", []))),
        )

    def compare(self, facts: list[dict[str, Any]], findings: list[dict[str, Any]], unresolved: list[str] | None = None) -> OracleResult:
        observed_facts = tuple(sorted({str(item.get("kind")) for item in facts if item.get("kind")}))
        observed_findings = tuple(sorted({str(item.get("rule_id", item.get("id"))) for item in findings if item.get("rule_id", item.get("id"))}))
        observed_unresolved = tuple(sorted(set(unresolved or [])))
        missing_facts = tuple(item for item in self.expected_facts if item not in observed_facts)
        missing_findings = tuple(item for item in self.expected_findings if item not in observed_findings)
        forbidden = tuple(item for item in observed_findings if item in self.forbidden_findings)
        missing_unresolved = tuple(item for item in self.expected_unresolved if item not in observed_unresolved)
        reasons: list[str] = []
        if missing_facts:
            reasons.append("expected_fact_missing")
        if missing_findings:
            reasons.append("expected_finding_missing")
        if forbidden:
            reasons.append("forbidden_finding_observed")
        if missing_unresolved:
            reasons.append("expected_unresolved_missing")
        if reasons:
            classification = "FAIL"
        elif observed_unresolved and not self.expected_unresolved:
            classification = "UNRESOLVED"
            reasons.append("unexpected_unresolved")
        else:
            classification = "PASS"
        return OracleResult(
            classification=classification,
            expected_facts=self.expected_facts,
            observed_facts=observed_facts,
            missing_facts=missing_facts,
            expected_findings=self.expected_findings,
            observed_findings=observed_findings,
            missing_findings=missing_findings,
            forbidden_findings=forbidden,
            unresolved_expected=self.expected_unresolved,
            unresolved_observed=observed_unresolved,
            reasons=tuple(reasons),
        )


__all__ = ["ExpectedOracle", "OracleResult"]
