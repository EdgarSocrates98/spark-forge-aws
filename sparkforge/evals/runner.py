"""Evaluation Runner for Router and Economy Accuracy."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from sparkforge.economy.router import CapabilityModelRouter
from sparkforge.registry.models import ExecutionProfile, ModelTier, RiskLevel


@dataclass
class EvalResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    failures: list[dict[str, Any]] = field(default_factory=list)


class EvaluationRunner:
    def __init__(self, router: Optional[CapabilityModelRouter] = None) -> None:
        self.router = router or CapabilityModelRouter()

    def run_router_eval(self, dataset_path: Path) -> EvalResult:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        passed = 0
        failed = 0
        failures = []

        for case in data:
            case_id = case.get("id", "unknown")
            task = case.get("task", "")
            profile_str = case.get("profile", "eco")
            risk_str = case.get("risk_level", "read_only")
            is_det = case.get("is_deterministic_available", False)

            profile = ExecutionProfile(profile_str) if isinstance(profile_str, str) else ExecutionProfile.ECO
            risk = RiskLevel(risk_str) if isinstance(risk_str, str) else RiskLevel.READ_ONLY

            decision = self.router.route_task(
                task_description=task,
                profile=profile,
                risk_level=risk,
                is_deterministic_available=is_det,
            )

            expected_tier = case.get("expected_tier")
            expected_skills = case.get("expected_skills", [])

            tier_match = (decision.tier.value == expected_tier) if expected_tier else True
            skills_match = all(s in decision.selected_skills for s in expected_skills)

            if tier_match and skills_match:
                passed += 1
            else:
                failed += 1
                failures.append({
                    "case_id": case_id,
                    "task": task,
                    "expected_tier": expected_tier,
                    "actual_tier": decision.tier.value,
                    "expected_skills": expected_skills,
                    "actual_skills": decision.selected_skills,
                })

        total = len(data)
        rate = (passed / total) if total > 0 else 1.0
        return EvalResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            pass_rate=round(rate, 4),
            failures=failures,
        )
