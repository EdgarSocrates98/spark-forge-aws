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
    answer_state: dict[str, Any] | None
    passed: bool
    baseline_id: str | None = None
    suite_id: str | None = None
    quality: dict[str, Any] = field(default_factory=dict)
    evidence_recall: float | None = None
    false_positive_rate: float | None = None
    refusal_reason: str | None = None
    unresolved: tuple[str, ...] = ()

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
            "answer_state": self.answer_state,
            "passed": self.passed,
            "baseline_id": self.baseline_id,
            "suite_id": self.suite_id,
            "quality": self.quality,
            "evidence_recall": self.evidence_recall,
            "false_positive_rate": self.false_positive_rate,
            "refusal_reason": self.refusal_reason,
            "unresolved": list(self.unresolved),
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
                    max_bytes=(
                        int(case["max_bytes"])
                        if case.get("max_bytes") is not None
                        else None
                    ),
                    case_id=case_id,
                    items=tuple(item for item in case.get("items", []) if isinstance(item, dict)),
                    host_usage=case.get("host_usage"),
                    answer_status=case.get("answer_status"),
                    answer_reasons=tuple(
                        str(item) for item in case.get("answer_reasons", ()) if str(item)
                    ),
                    triggers=tuple(
                        str(item) for item in case.get("triggers", ()) if str(item)
                    ),
                )
                response = gateway.start(
                    request,
                    skills=[item for item in case.get("skills", []) if isinstance(item, dict)],
                    knowledge=[
                        item for item in case.get("knowledge", []) if isinstance(item, dict)
                    ],
                )
                expected = case.get("expected_status", "ok")
                unresolved = tuple(
                    str(item.get("code"))
                    for item in response.get("unresolved", [])
                    if isinstance(item, dict) and item.get("code")
                )
                expected_evidence = {
                    str(item) for item in case.get("expected_evidence", []) if str(item)
                }
                actual_evidence = _evidence_ids(response)
                evidence_recall = (
                    len(expected_evidence & actual_evidence) / len(expected_evidence)
                    if expected_evidence
                    else None
                )
                expected_unresolved = {
                    str(item) for item in case.get("expected_unresolved", []) if str(item)
                }
                expected_findings = {
                    str(item) for item in case.get("expected_findings", []) if str(item)
                }
                actual_findings = _finding_ids(response)
                false_positive_rate = (
                    len(actual_findings - expected_findings) / len(actual_findings)
                    if actual_findings
                    else 0.0
                )
                quality = {
                    "expected_evidence": sorted(expected_evidence),
                    "observed_evidence": sorted(actual_evidence),
                    "expected_unresolved": sorted(expected_unresolved),
                    "observed_unresolved": list(unresolved),
                    "expected_findings": sorted(expected_findings),
                    "observed_findings": sorted(actual_findings),
                }
                answer_state = response.get("answer_state") or {}
                expected_answer_status = case.get("answer_status")
                expected_answer_reasons = {
                    str(item) for item in case.get("answer_reasons", ()) if str(item)
                }
                expected_triggers = {
                    str(item) for item in case.get("triggers", ()) if str(item)
                }
                observed_answer_reasons = {
                    str(item)
                    for item in answer_state.get("reasons", ())
                    if str(item)
                }
                observed_triggers = {
                    str(item)
                    for item in answer_state.get("triggers", ())
                    if str(item)
                }
                expected_plans = case.get("expected_execution_plan") or {}
                expected_plan = (
                    expected_plans.get(profile.value)
                    if isinstance(expected_plans, dict)
                    else None
                )
                observed_plan = (response.get("execution_plan") or {}).get("kind")
                answer_status_passed = (
                    expected_answer_status is None
                    or answer_state.get("status") == expected_answer_status
                )
                answer_reasons_passed = expected_answer_reasons <= observed_answer_reasons
                triggers_passed = expected_triggers <= observed_triggers
                plan_passed = expected_plan is None or observed_plan == expected_plan
                quality.update(
                    {
                        "expected_answer_status": expected_answer_status,
                        "observed_answer_status": answer_state.get("status"),
                        "expected_answer_reasons": sorted(expected_answer_reasons),
                        "observed_answer_reasons": sorted(observed_answer_reasons),
                        "expected_triggers": sorted(expected_triggers),
                        "observed_triggers": sorted(observed_triggers),
                        "expected_execution_plan": expected_plan,
                        "observed_execution_plan": observed_plan,
                    }
                )
                quality_passed = (
                    expected_evidence <= actual_evidence
                    and expected_unresolved <= set(unresolved)
                    and answer_status_passed
                    and answer_reasons_passed
                    and triggers_passed
                    and plan_passed
                )
                refusal_reason = None
                if response.get("status") == "refused":
                    refusal_reason = next(iter(unresolved), response.get("error"))
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
                    answer_state=answer_state or None,
                    passed=response.get("status") == expected and quality_passed,
                    baseline_id=baseline_id,
                    suite_id=case.get("suite_id"),
                    quality=quality,
                    evidence_recall=evidence_recall,
                    false_positive_rate=false_positive_rate,
                    refusal_reason=refusal_reason,
                    unresolved=unresolved,
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


def _evidence_ids(response: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for item in response.get("context", []):
        if not isinstance(item, dict):
            continue
        for key in ("fact_id", "finding_id", "rule_id"):
            value = item.get(key)
            if value:
                values.add(str(value))
        payload = item.get("payload")
        if isinstance(payload, dict):
            for key in ("fact_id", "finding_id", "rule_id"):
                value = payload.get(key)
                if value:
                    values.add(str(value))
    return values


def _finding_ids(response: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for item in response.get("context", []):
        if not isinstance(item, dict) or item.get("kind") != "finding":
            continue
        value = item.get("finding_id") or item.get("id")
        if value:
            values.add(str(value))
        payload = item.get("payload")
        if isinstance(payload, dict) and payload.get("finding_id"):
            values.add(str(payload["finding_id"]))
    return values
