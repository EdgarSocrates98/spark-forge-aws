"""Spark Physical Plan Profiler for Operator and Optimization Inspection."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class PlanFinding:
    severity: str  # critical, high, medium, low
    operator: str
    title: str
    description: str
    recommendation: str


@dataclass
class PlanProfileReport:
    total_operators: int
    has_cartesian_product: bool
    has_broadcast_nested_loop: bool
    exchange_count: int
    findings: list[PlanFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SparkPlanProfiler:
    """Analyzes formatted Spark physical plan text (EXPLAIN FORMATTED output)."""

    def profile_plan(self, plan_text: str) -> PlanProfileReport:
        findings: list[PlanFinding] = []

        has_cartesian = "CartesianProduct" in plan_text
        has_bnlj = "BroadcastNestedLoopJoin" in plan_text
        exchanges = len(re.findall(r"\b(Exchange|ShuffleExchangeExec)\b", plan_text))
        total_ops = len(re.findall(r"^\(\d+\)", plan_text, flags=re.MULTILINE))

        if has_cartesian:
            findings.append(
                PlanFinding(
                    severity="critical",
                    operator="CartesianProduct",
                    title="Cartesian Product detected in physical plan",
                    description="O(M*N) row explosion causing extreme memory allocation and execution time.",
                    recommendation="Add explicit join condition or rewrite logic.",
                )
            )

        if has_bnlj:
            findings.append(
                PlanFinding(
                    severity="critical",
                    operator="BroadcastNestedLoopJoin",
                    title="BroadcastNestedLoopJoin detected",
                    description="Inefficient join operator chosen due to missing equi-join condition.",
                    recommendation="Ensure equi-join condition on keys (`df1.id == df2.id`).",
                )
            )

        if exchanges > 5:
            findings.append(
                PlanFinding(
                    severity="medium",
                    operator="Exchange",
                    title=f"High shuffle exchange count ({exchanges} Exchanges)",
                    description="Multiple shuffles indicate repeated repartitioning or successive joins on different keys.",
                    recommendation="Reorganize join order or use bucketed / partition-aligned data layout.",
                )
            )

        return PlanProfileReport(
            total_operators=total_ops,
            has_cartesian_product=has_cartesian,
            has_broadcast_nested_loop=has_bnlj,
            exchange_count=exchanges,
            findings=findings,
        )
