"""Declared multi-engine equivalence and impact experiment plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EquivalencePlan:
    table: str
    catalog: str
    engines: tuple[str, ...]
    operations: tuple[dict[str, Any], ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "catalog": self.catalog,
            "engines": list(self.engines),
            "operations": [dict(item) for item in self.operations],
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class BlastRadiusComparison:
    predicted: tuple[str, ...]
    observed: tuple[str, ...]
    true_positive: tuple[str, ...]
    missed: tuple[str, ...]
    false_positive: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted": list(self.predicted),
            "observed": list(self.observed),
            "true_positive": list(self.true_positive),
            "missed": list(self.missed),
            "false_positive": list(self.false_positive),
        }


def build_equivalence_plan(
    *, table: str, catalog: str, engines: tuple[str, ...] = ("spark", "flink", "trino", "duckdb")
) -> EquivalencePlan:
    operations = (
        {"writer": "spark", "reader": "flink", "operation": "write_read"},
        {"writer": "flink", "reader": "spark", "operation": "write_read"},
        {"writer": "spark", "reader": "trino", "operation": "merge_read"},
        {"writer": "trino", "reader": "duckdb", "operation": "schema_read"},
        {"writer": "spark", "reader": "flink", "operation": "schema_evolution"},
    )
    return EquivalencePlan(table, catalog, tuple(engines), operations, "declared_unmeasured")


def compare_blast_radius(predicted: list[str], observed: list[str]) -> BlastRadiusComparison:
    predicted_set, observed_set = set(predicted), set(observed)
    return BlastRadiusComparison(
        predicted=tuple(sorted(predicted_set)),
        observed=tuple(sorted(observed_set)),
        true_positive=tuple(sorted(predicted_set & observed_set)),
        missed=tuple(sorted(observed_set - predicted_set)),
        false_positive=tuple(sorted(predicted_set - observed_set)),
    )


__all__ = [
    "BlastRadiusComparison",
    "EquivalencePlan",
    "build_equivalence_plan",
    "compare_blast_radius",
]
