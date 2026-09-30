"""Compatibility bridge from the economy Decision Plane to the generic kernel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.decision import (
    ActivePromotion,
    AuthorityPolicy,
    BoundedDecisionKernel,
    DecisionCache,
)
from sparkforge.decision.contracts import ContractLoader
from sparkforge.decision.models import DecisionStatus as KernelStatus
from sparkforge.economy.decision_contracts import DecisionContract as EconomyContract
from sparkforge.economy.decision_models import (
    DecisionInput,
    DecisionResult,
    DecisionStatus,
)


def build_kernel_contract(contract: EconomyContract, *, mode: str = "shadow"):
    raw = {
        "schema_version": 1,
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "mode": mode,
        "primitive": "route",
        "state": {
            "required": [
                {"name": "task_description", "type": "string"},
                {"name": "evidence_kinds", "type": "array", "order_insensitive": True},
                {"name": "profile", "type": "string"},
                {"name": "risk_level", "type": "string"},
                {"name": "deterministic_available", "type": "boolean"},
                {"name": "cached", "type": "boolean"},
            ]
        },
        "budget": {"max_input_bytes": 6000, "cache_max_entries": 128},
        "spec": {"rules": _rules(contract)},
        "activation": {"enabled": mode == "active"},
        "measurement": {"enabled": False},
    }
    return ContractLoader().parse(raw)


def evaluate_legacy(
    contract: EconomyContract,
    state: DecisionInput,
    *,
    cache: DecisionCache | None = None,
) -> DecisionResult:
    budget_reason = _budget_reason(contract, state)
    if budget_reason is not None:
        return DecisionResult.unresolved_result(contract, state.budget, budget_reason)
    kernel_contract = build_kernel_contract(contract)
    raw_state = {
        "task_description": state.task_description,
        "evidence_kinds": list(state.evidence_kinds),
        "profile": state.profile,
        "risk_level": state.risk_level,
        "deterministic_available": state.deterministic_available,
        "cached": state.cached,
    }
    evaluation = BoundedDecisionKernel(cache=cache).evaluate(kernel_contract, raw_state)
    generic = evaluation.result
    if generic.status is KernelStatus.ACCEPTED:
        return DecisionResult(
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract.sha256,
            status=DecisionStatus.ACCEPTED,
            selected=generic.selected,
            confidence=generic.confidence,
            confidence_source="rule",
            method="declared_predicates",
            budget=state.budget,
            fingerprint=generic.fingerprint,
            cache_hit=generic.cache_hit,
            evidence=generic.evidence,
        )
    if generic.status is KernelStatus.REFUSED:
        return DecisionResult.refused_result(contract, state.budget, generic.reason or "refused")
    reason = generic.reason or "no_candidate_has_sufficient_evidence"
    return DecisionResult.unresolved_result(contract, state.budget, reason).with_kernel(
        fingerprint=generic.fingerprint,
        cache_hit=generic.cache_hit,
        evidence=generic.evidence,
    )


def evaluate_active(
    contract: EconomyContract,
    state: DecisionInput,
    *,
    promotion: ActivePromotion,
    cache: DecisionCache | None = None,
    authority_policy: AuthorityPolicy | None = None,
    repo: Path | str | None = None,
    caller_authorized: bool = False,
) -> DecisionResult:
    """Evaluate the economy contract only with explicit generic-kernel promotion."""
    budget_reason = _budget_reason(contract, state)
    if budget_reason is not None:
        return DecisionResult.refused_result(contract, state.budget, budget_reason).with_authority(
            "active"
        )
    kernel_contract = build_kernel_contract(contract, mode="active")
    raw_state = {
        "task_description": state.task_description,
        "evidence_kinds": list(state.evidence_kinds),
        "profile": state.profile,
        "risk_level": state.risk_level,
        "deterministic_available": state.deterministic_available,
        "cached": state.cached,
    }
    if authority_policy is None and repo is None:
        raise ValueError("authority_policy_or_repo_required")
    if authority_policy is None:
        assert repo is not None
        policy = AuthorityPolicy.from_repo(repo)
    else:
        policy = authority_policy
    evaluation = BoundedDecisionKernel(cache=cache, authority_policy=policy).evaluate(
        kernel_contract,
        raw_state,
        promotion=promotion,
        caller_authorized=caller_authorized,
        risk_profile=state.profile,
        risk_level=state.risk_level,
    )
    generic = evaluation.result
    if generic.status is KernelStatus.ACCEPTED:
        return DecisionResult(
            contract_id=contract.contract_id,
            contract_version=contract.contract_version,
            contract_sha256=contract.sha256,
            status=DecisionStatus.ACCEPTED,
            selected=generic.selected,
            confidence=generic.confidence,
            confidence_source="rule",
            method="declared_predicates",
            budget=state.budget,
            fingerprint=generic.fingerprint,
            cache_hit=generic.cache_hit,
            evidence=generic.evidence,
            authority="active",
        )
    reason = generic.reason or "active_promotion_refused"
    result = (
        DecisionResult.refused_result(contract, state.budget, reason)
        if generic.status is KernelStatus.REFUSED
        else DecisionResult.unresolved_result(contract, state.budget, reason)
    )
    return result.with_kernel(
        fingerprint=generic.fingerprint,
        cache_hit=generic.cache_hit,
        evidence=generic.evidence,
    ).with_authority("active")


def _rules(contract: EconomyContract) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for candidate in contract.candidates:
        conditions: list[dict[str, Any]] = []
        for predicate in candidate.predicates:
            if predicate.name == "always":
                continue
            if predicate.name == "evidence_kind":
                conditions.append({"field": "evidence_kinds", "contains": str(predicate.value)})
            elif predicate.name == "task_contains":
                conditions.append({"field": "task_description", "contains": str(predicate.value)})
            elif predicate.name == "deterministic_available":
                conditions.append({"field": predicate.name, "equals": bool(predicate.value)})
            elif predicate.name == "cached":
                conditions.append({"field": predicate.name, "equals": bool(predicate.value)})
            elif predicate.name == "profile_is":
                conditions.append({"field": "profile", "equals": str(predicate.value)})
            elif predicate.name == "risk_is":
                conditions.append({"field": "risk_level", "equals": str(predicate.value)})
        rules.append(
            {
                "when": conditions,
                "route": candidate.route,
                "confidence": contract.thresholds.confidence_for(candidate.name),
                "priority": candidate.priority,
            }
        )
    return rules


def _budget_reason(contract: EconomyContract, state: DecisionInput) -> str | None:
    if (
        state.budget.max_total_tokens is not None
        and state.budget.tokens_used > contract.budget.max_total_tokens
    ):
        return "budget_tokens_exceeded"
    if (
        state.budget.max_tool_calls is not None
        and state.budget.tool_calls_used > contract.budget.max_tool_calls
    ):
        return "budget_tool_calls_exceeded"
    return None


__all__ = ["build_kernel_contract", "evaluate_active", "evaluate_legacy"]
