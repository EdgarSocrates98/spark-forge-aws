"""Observed-only Athena cost projection."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts


def build_observed_athena_cost(facts: Sequence[Fact]) -> dict[str, Any]:
    costs = [fact for fact in sort_facts(facts) if fact.kind == "athena.query_cost"]
    if not costs:
        return {
            "status": "unresolved",
            "refused": True,
            "reason": "athena_cost_measurement_missing",
            "required": ["cost", "cost_basis", "observed_at"],
            "fact_ids": [],
        }
    currencies = {str(fact.attrs.get("currency") or "") for fact in costs}
    bases = {str(fact.attrs.get("cost_basis") or "") for fact in costs}
    if len(currencies) != 1 or len(bases) != 1 or "" in currencies or "" in bases:
        return {
            "status": "unresolved",
            "refused": True,
            "reason": "cost_basis_or_currency_ambiguous",
            "fact_ids": [fact.id for fact in costs],
        }
    return {
        "status": "observed",
        "refused": False,
        "cost": sum(float(fact.measures["cost"]) for fact in costs),
        "currency": next(iter(currencies)),
        "cost_basis": next(iter(bases)),
        "fact_ids": [fact.id for fact in costs],
    }
