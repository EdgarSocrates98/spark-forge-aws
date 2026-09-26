"""Canonical report and three projections for Glue DQ AI governance."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.finops.athena_observed import build_observed_athena_cost
from sparkforge.findings.models import Fact, Finding, RuntimeContext, sort_facts, sort_findings


def _runtime_dict(runtime: RuntimeContext | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(runtime, RuntimeContext):
        return runtime.to_dict()
    return dict(runtime or {})


def render_maintainer(canonical: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "finding_ids": [item["rule_id"] for item in canonical["findings"]],
        "fact_ids": [item["id"] for item in canonical["facts"]],
        "unresolved": canonical["unresolved"],
        "compatibility": canonical["compatibility"],
        "catalog_version": canonical["catalog_version"],
    }


def render_operator(canonical: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "review_required" if canonical["findings"] or canonical["unresolved"] else "clear_on_observed_evidence",
        "actions": [
            {
                "rule_id": item["rule_id"],
                "title": item["title"],
                "proposed_change": item["proposed_change"],
                "rollback": item["rollback"],
                "validation": item["validation"],
            }
            for item in canonical["findings"]
        ],
        "cost": canonical["cost"],
        "unresolved": canonical["unresolved"],
    }


def render_security(canonical: Mapping[str, Any]) -> dict[str, Any]:
    assessments = [fact for fact in canonical["facts"] if fact["kind"] == "dq.ai.assessment"]
    def risk_context_for(fact: Mapping[str, Any]) -> dict[str, Any]:
        context = dict(fact["attrs"].get("risk_context", {}))
        if "iceberg_context" in fact["attrs"]:
            context["iceberg"] = fact["attrs"]["iceberg_context"]
        if "migration_context" in fact["attrs"]:
            context["migration"] = fact["attrs"]["migration_context"]
        return context

    return {
        "exposure": [
            {
                "subject": fact["subject"],
                "mode": fact["attrs"].get("mode"),
                "labels": fact["attrs"].get("exposure_labels", []),
                "source_region": fact["attrs"].get("source_region", ""),
                "inference_region": fact["attrs"].get("inference_region", ""),
                "kms_status": fact["attrs"].get("kms_status", ""),
                "authorization_evidence_status": fact["attrs"].get(
                    "authorization_evidence_status", ""
                ),
                "sampling_controls_status": fact["attrs"].get(
                    "sampling_controls_status", ""
                ),
                "geographic_boundary_status": fact["attrs"].get(
                    "geographic_boundary_status", ""
                ),
                "review_status": fact["attrs"].get("review_status", ""),
                "recommendation_variability": fact["attrs"].get(
                    "recommendation_variability", ""
                ),
                "provider_data_protection_claims": fact["attrs"].get(
                    "provider_data_protection_claims", {}
                ),
                "risk_context": risk_context_for(fact),
                "iceberg_context": fact["attrs"].get("iceberg_context", {}),
                "migration_context": fact["attrs"].get("migration_context", {}),
                "evidence": [fact["id"]],
            }
            for fact in assessments
        ],
        "finding_ids": [item["rule_id"] for item in canonical["findings"]],
        "unresolved": canonical["unresolved"],
    }


def build_dq_ai_report(
    facts: Sequence[Fact],
    findings: Sequence[Finding],
    runtime: RuntimeContext | Mapping[str, Any] | None = None,
    skipped: Sequence[Mapping[str, Any]] | None = None,
    view: str = "all",
) -> dict[str, Any]:
    ordered_facts = sort_facts(facts)
    ordered_findings = sort_findings(findings)
    fact_dicts = [fact.to_dict() for fact in ordered_facts]
    finding_dicts = [finding.to_dict() for finding in ordered_findings]
    unresolved = [
        {"id": fact.id, "kind": fact.kind, "subject": fact.subject, "attrs": fact.attrs}
        for fact in ordered_facts
        if fact.kind.endswith(".unresolved")
    ]
    assessments = [fact for fact in ordered_facts if fact.kind == "dq.ai.assessment"]
    canonical: dict[str, Any] = {
        "schema_version": 1,
        "feature": "GLUE_DQ_ADVANCED_GOVERNANCE",
        "runtime": _runtime_dict(runtime),
        "facts": fact_dicts,
        "findings": finding_dicts,
        "unresolved": unresolved,
        "skipped": list(skipped or []),
        "compatibility": [
            {
                "subject": fact.subject,
                "runtime": fact.attrs.get("runtime_glue", ""),
                "mode": fact.attrs.get("mode", ""),
                "status": fact.attrs.get("compatibility_status", "unresolved"),
                "matrix_advanced": fact.attrs.get("matrix_advanced", "unresolved"),
                "evidence": [fact.id],
            }
            for fact in assessments
        ],
        "cost": build_observed_athena_cost(ordered_facts),
        "catalog_version": 1,
        "metrics": {
            "fact_count": len(ordered_facts),
            "finding_count": len(ordered_findings),
            "unresolved_count": len(unresolved),
            "provider_calls": 0,
            "row_payloads": 0,
        },
    }
    views = {
        "maintainer": render_maintainer(canonical),
        "operator": render_operator(canonical),
        "security_compliance": render_security(canonical),
    }
    if view == "all":
        canonical["views"] = views
    elif view in views:
        canonical["views"] = {view: views[view]}
    else:
        raise ValueError(f"view desconhecida: {view}")
    return canonical
