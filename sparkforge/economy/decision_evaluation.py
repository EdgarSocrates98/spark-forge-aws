"""Offline seed evaluation for the declarative shadow Decision Plane.

This runner belongs to the runtime-facing economy package so the CLI does not
depend on ``sparkforge.evals``. The evaluation package re-exports it for hosts.
Its legacy seed remains the compatibility regression for the generic bounded
kernel route facade.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sparkforge.economy.decision_models import DecisionInput
from sparkforge.economy.decision_plane import DecisionPlaneService


class DecisionEvaluationRunner:
    """Run versioned decision cases against one contract and ground truth."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()

    def run(
        self,
        fixture_path: Path | str = "evals/token_efficient/fixtures/decision_plane_cases.yaml",
    ) -> dict[str, Any]:
        requested = Path(fixture_path).expanduser()
        path = (self.repo / requested if not requested.is_absolute() else requested).resolve()
        if self.repo not in path.parents:
            raise ValueError("decision fixture must be within repository")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError("decision fixture schema_version unsupported")
        cases = raw.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError("decision fixture requires cases")
        service = DecisionPlaneService(self.repo)
        contract = service.validate("routing.data_domain")
        results: list[dict[str, Any]] = []
        for raw_case in cases:
            if not isinstance(raw_case, dict):
                raise ValueError("decision fixture case must be an object")
            results.append(self._run_case(service, contract, raw_case))
        passed = sum(1 for result in results if result["passed"])
        source_counts = Counter(str(case.get("source", "unknown")) for case in cases)
        return {
            "schema_version": 1,
            "suite_id": str(raw.get("suite_id", "decision-plane-seed")),
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "total_cases": len(results),
            "passed_cases": passed,
            "failed_cases": len(results) - passed,
            "seed_passed": passed == len(results),
            "activation_ready": False,
            "source_counts": dict(sorted(source_counts.items())),
            "results": results,
        }

    @staticmethod
    def _run_case(
        service: DecisionPlaneService, contract: Any, case: dict[str, Any]
    ) -> dict[str, Any]:
        budget = case.get("budget") or {}
        provider_usage = case.get("provider_usage")
        raw_input = {
            "task_id": str(case["id"]),
            "task_description": str(case.get("task_description", case["id"])),
            "evidence_kinds": tuple(case.get("evidence_kinds", ())),
            "current_route": case.get("current_route"),
            "profile": str(case.get("profile", "eco")),
            "risk_level": str(case.get("risk_level", "read_only")),
            "deterministic_available": bool(case.get("deterministic_available", False)),
            "cached": bool(case.get("cached", False)),
            "budget": budget,
            "provider_usage": provider_usage,
        }
        request = DecisionInput.from_mapping(raw_input)
        evaluation = service.shadow(
            request,
            case.get("current_route"),
            contract=contract,
            now="2026-09-28T00:00:00Z",
        )
        result = evaluation.result.to_dict()
        comparison = evaluation.comparison.to_dict()
        token_state = request.provider_usage.to_dict()
        passed = (
            result["status"] == case.get("expected_status")
            and (result["selected"][0] if result["selected"] else None)
            == case.get("expected_route")
            and comparison["state"] == case.get("expected_comparison")
            and token_state["tokens_unresolved"]
            == bool(case.get("expected_tokens_unresolved", token_state["tokens_unresolved"]))
        )
        return {
            "case_id": str(case["id"]),
            "source": str(case.get("source", "unknown")),
            "passed": passed,
            "status": result["status"],
            "selected": result["selected"],
            "comparison": comparison["state"],
            "tokens_unresolved": token_state["tokens_unresolved"],
            "provider_tokens": token_state["provider_tokens"],
            "receipt_id": result["receipt_id"],
            "unresolved": result["unresolved"],
        }


__all__ = ["DecisionEvaluationRunner"]
