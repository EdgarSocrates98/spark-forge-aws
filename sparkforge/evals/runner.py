"""Evaluation Runner for Router and Economy Accuracy."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_models import GatewayProfile, GatewayRequest
from sparkforge.economy.router import CapabilityModelRouter
from sparkforge.registry.models import ExecutionProfile, RiskLevel


@dataclass
class EvalResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    failures: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProfileBenchmarkResult:
    schema_version: int
    case_id: str
    profile: str
    status: str
    payload_bytes: int | None
    provider_tokens: dict[str, int] | None
    tokens_unresolved: bool
    execution_plan: dict[str, Any] | None
    passed: bool
    baseline_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "profile": self.profile,
            "status": self.status,
            "payload_bytes": self.payload_bytes,
            "provider_tokens": self.provider_tokens,
            "tokens_unresolved": self.tokens_unresolved,
            "execution_plan": self.execution_plan,
            "passed": self.passed,
            "baseline_id": self.baseline_id,
        }


class EvaluationRunner:
    def __init__(self, router: CapabilityModelRouter | None = None) -> None:
        self.router = router or CapabilityModelRouter()

    def run_context_benchmark(
        self,
        gateway: ContextGateway,
        cases: list[dict[str, Any]],
        *,
        baseline_id: str | None = None,
        profiles: tuple[GatewayProfile, ...] = (
            GatewayProfile.ECONOMY,
            GatewayProfile.BALANCED,
            GatewayProfile.DEEP,
        ),
    ) -> list[dict[str, Any]]:
        """Run identical deterministic cases across Gateway profiles."""
        results: list[dict[str, Any]] = []
        for case in cases:
            case_id = str(case.get("id", "unknown"))
            for profile in profiles:
                request = GatewayRequest(
                    intent=str(case.get("intent", "")),
                    profile=profile,
                    max_bytes=int(case.get("max_bytes", 0)),
                    case_id=case_id,
                    items=tuple(item for item in case.get("items", []) if isinstance(item, dict)),
                    host_usage=case.get("host_usage"),
                )
                response = gateway.start(
                    request,
                    skills=[item for item in case.get("skills", []) if isinstance(item, dict)],
                    knowledge=[
                        item for item in case.get("knowledge", []) if isinstance(item, dict)
                    ],
                )
                expected = case.get("expected_status", "ok")
                state = response.get("token_state", {})
                result = ProfileBenchmarkResult(
                    schema_version=1,
                    case_id=case_id,
                    profile=profile.value,
                    status=str(response.get("status", "unknown")),
                    payload_bytes=(response.get("budget") or {}).get("payload_bytes"),
                    provider_tokens=state.get("provider_tokens"),
                    tokens_unresolved=bool(state.get("tokens_unresolved", True)),
                    execution_plan=response.get("execution_plan"),
                    passed=response.get("status") == expected,
                    baseline_id=baseline_id,
                )
                results.append(result.to_dict())
        return results

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

            profile = (
                ExecutionProfile(profile_str)
                if isinstance(profile_str, str)
                else ExecutionProfile.ECO
            )
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
                failures.append(
                    {
                        "case_id": case_id,
                        "task": task,
                        "expected_tier": expected_tier,
                        "actual_tier": decision.tier.value,
                        "expected_skills": expected_skills,
                        "actual_skills": decision.selected_skills,
                    }
                )

        total = len(data)
        rate = (passed / total) if total > 0 else 1.0
        return EvalResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            pass_rate=round(rate, 4),
            failures=failures,
        )
