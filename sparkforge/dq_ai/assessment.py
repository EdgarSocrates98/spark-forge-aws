"""Join evidence for Glue DQ governance before rule evaluation."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, RuntimeContext, sort_facts

MATRIX_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "glue" / "dq-advanced-matrix.yaml"
EXTRACTOR_ID = "dq_ai_assessment@0.1.0"
EMITTED_KINDS = frozenset({"dq.ai.assessment", "dq.ai.assessment.unresolved"})


def _subject_key(subject: Mapping[str, Any]) -> str:
    return json.dumps(dict(subject), sort_keys=True, separators=(",", ":"), default=str)


def _runtime_glue(runtime: RuntimeContext | Mapping[str, Any] | None) -> str:
    if isinstance(runtime, RuntimeContext):
        return runtime.glue
    if isinstance(runtime, Mapping):
        return str(runtime.get("glue") or "")
    return ""


def _matrix() -> Mapping[str, Any]:
    payload = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Glue DQ matrix precisa ser um objeto")
    return payload


def _compatibility(mode: str, runtime_glue: str) -> tuple[str, Mapping[str, Any] | None]:
    if not runtime_glue:
        return "unresolved", None
    row = _matrix().get("runtimes", {}).get(runtime_glue)
    if not isinstance(row, Mapping):
        return "unresolved", None
    value = row.get(mode.lower())
    return str(value or "unresolved"), row


def _same_subject(facts: Sequence[Fact], kind: str, subject: Mapping[str, Any]) -> list[Fact]:
    key = _subject_key(subject)
    return [fact for fact in facts if fact.kind == kind and _subject_key(fact.subject) == key]


def _evidence_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"declared", "sufficient", "complete", "observed", "ok"}:
        return "declared"
    if normalized in {"missing", "insufficient", "denied"}:
        return normalized
    return "unresolved"


def build_assessment_facts(
    facts: Sequence[Fact], runtime: RuntimeContext | Mapping[str, Any] | None = None
) -> list[Fact]:
    recommendations = [fact for fact in facts if fact.kind == "dq.ai.recommendation"]
    runtime_glue = _runtime_glue(runtime)
    assessments: list[Fact] = []
    unresolved: list[Fact] = []
    for recommendation in recommendations:
        attrs = dict(recommendation.attrs)
        mode = str(attrs.get("mode") or "")
        reviews = _same_subject(facts, "dq.ai.review", recommendation.subject)
        dqdl = _same_subject(facts, "dq.dqdl", recommendation.subject)
        dqdl_invalid = _same_subject(facts, "dq.dqdl.unresolved", recommendation.subject)
        review_status = str(attrs.get("human_review_status") or "")
        if reviews:
            review_status = str(reviews[0].attrs.get("status") or "unresolved")
        dqdl_status = "valid" if dqdl else ("invalid" if dqdl_invalid else "unresolved")
        cross_region = str(attrs.get("cross_region_status") or "unresolved")
        classification = str(attrs.get("classification") or "")
        kms_status = str(attrs.get("kms_status") or "")
        if mode == "ADVANCED" and not kms_status:
            kms_status = "unresolved"
        key_policy_status = _evidence_status(attrs.get("key_policy_status"))
        runtime_role_status = _evidence_status(attrs.get("runtime_role_status"))
        lakeformation_status = _evidence_status(attrs.get("lakeformation_status"))
        authorization_parts = (key_policy_status, runtime_role_status, lakeformation_status)
        authorization_evidence_status = (
            "not_applicable"
            if mode != "ADVANCED"
            else "complete"
            if all(value == "declared" for value in authorization_parts)
            else "insufficient"
            if any(value in {"missing", "insufficient", "denied"} for value in authorization_parts)
            else "unresolved"
        )
        incompatible_args = list(attrs.get("incompatible_args") or [])
        matrix_status, matrix_row = _compatibility(mode, runtime_glue)
        matrix_sampling = _matrix().get("sampling", {})
        if not isinstance(matrix_sampling, Mapping):
            matrix_sampling = {}
        sampling_workgroup = str(attrs.get("sampling_workgroup") or "")
        sampling_bucket = str(attrs.get("sampling_bucket") or "")
        retention_declared = "retention_days" in attrs
        sampling_controls_status = (
            "not_applicable"
            if mode != "ADVANCED"
            else "complete"
            if sampling_workgroup and sampling_bucket and retention_declared
            else "unresolved"
        )
        sampling_reference_status = (
            "not_applicable"
            if mode != "ADVANCED"
            else "declared"
            if sampling_controls_status == "complete"
            else "documented_not_observed"
        )
        geographic_boundary_status = str(
            attrs.get("geographic_boundary_status") or "unresolved"
        )
        assessment_attrs: dict[str, Any] = {
            "mode": mode,
            "runtime_glue": runtime_glue,
            "runtime_status": "declared" if runtime_glue else "unresolved",
            "compatibility_status": matrix_status,
            "classification": classification,
            "classification_status": "declared" if classification else "unresolved",
            "cross_region_status": cross_region,
            "kms_status": kms_status,
            "key_policy_status": key_policy_status,
            "runtime_role_status": runtime_role_status,
            "lakeformation_status": lakeformation_status,
            "authorization_evidence_status": authorization_evidence_status,
            "dqdl_status": dqdl_status,
            "review_status": review_status
            or ("missing" if dqdl_status == "valid" else "unresolved"),
            "incompatible_args": incompatible_args,
            "exposure_labels": list(attrs.get("exposure_labels") or []),
            "source_region": str(attrs.get("source_region") or ""),
            "inference_region": str(attrs.get("inference_region") or ""),
            "sampling_bucket": sampling_bucket,
            "sampling_workgroup": sampling_workgroup,
            "sampling_bucket_status": str(
                attrs.get("sampling_bucket_status") or "unresolved"
            ),
            "sampling_workgroup_status": str(
                attrs.get("sampling_workgroup_status") or "unresolved"
            ),
            "sampling_retention_status": str(
                attrs.get("sampling_retention_status") or "unresolved"
            ),
            "sampling_controls_status": sampling_controls_status,
            "sampling_reference_status": sampling_reference_status,
            "documented_sampling_workgroup": str(
                matrix_sampling.get("workgroup") or ""
            ),
            "documented_sampling_bucket_pattern": str(
                matrix_sampling.get("bucket_pattern") or ""
            ),
            "documented_sampling_retention_days": matrix_sampling.get(
                "retention_days"
            ),
            "geographic_boundary_status": geographic_boundary_status,
            "payload_scope": "metadata_only",
            "recommendation_variability": str(
                attrs.get("recommendation_variability")
                or ("possible" if mode == "ADVANCED" else "not_applicable")
            ),
            "review_required": mode == "ADVANCED",
        }
        for context_name in ("risk_context", "iceberg_context", "migration_context"):
            if context_name in attrs:
                assessment_attrs[context_name] = attrs[context_name]
        provider_claims = _matrix().get("provider_data_protection_claims", {})
        if isinstance(provider_claims, Mapping):
            assessment_attrs["provider_data_protection_claims"] = dict(provider_claims)
        if matrix_row is not None:
            assessment_attrs["matrix_runtime"] = runtime_glue
            assessment_attrs["matrix_advanced"] = matrix_row.get("advanced", "unresolved")
        if "retention_days" in attrs:
            assessment_attrs["retention_days"] = attrs["retention_days"]
        if "kms_key_arn" in attrs:
            assessment_attrs["kms_key_arn"] = attrs["kms_key_arn"]
        assessment_attrs["sensitive_exposure"] = (
            mode == "ADVANCED" and classification.lower() in {"sensitive", "restricted", "pii"}
        )
        assessment_attrs["cross_region"] = mode == "ADVANCED" and cross_region == "true"
        assessment_attrs["geographic_boundary_incomplete"] = (
            mode == "ADVANCED"
            and assessment_attrs["cross_region"]
            and geographic_boundary_status not in {"same", "approved"}
        )
        assessment_attrs["sampling_controls_incomplete"] = (
            mode == "ADVANCED" and sampling_controls_status != "complete"
        )
        assessment_attrs["kms_insufficient"] = (
            mode == "ADVANCED" and kms_status in {"missing", "insufficient"}
        )
        assessment_attrs["authorization_incomplete"] = (
            mode == "ADVANCED" and authorization_evidence_status != "complete"
        )
        assessment_attrs["review_missing"] = (
            mode == "ADVANCED" and dqdl_status == "valid" and review_status != "declared"
        )
        assessment_attrs["has_incompatible_args"] = mode == "ADVANCED" and bool(incompatible_args)
        derived_ids = [recommendation.id, *[fact.id for fact in reviews + dqdl + dqdl_invalid]]
        provenance = dict(recommendation.provenance)
        provenance.update(
            {"extractor": "dq_ai_assessment@0.1.0", "derived_from": sorted(set(derived_ids))}
        )
        assessment = Fact(
            kind="dq.ai.assessment",
            subject=recommendation.subject,
            measures={
                "unresolved_count": sum(
                    value == "unresolved"
                    for value in (matrix_status, cross_region, kms_status, dqdl_status)
                )
            },
            attrs=assessment_attrs,
            provenance=provenance,
        )
        assessments.append(assessment)
        reasons: list[str] = []
        if not runtime_glue:
            reasons.append("runtime_missing")
        if cross_region == "unresolved":
            reasons.append("region_relation_unresolved")
        if mode == "ADVANCED" and kms_status == "unresolved":
            reasons.append("kms_evidence_unresolved")
        if reasons:
            unresolved.append(
                Fact(
                    kind="dq.ai.assessment.unresolved",
                    subject=recommendation.subject,
                    attrs={"reasons": reasons},
                    provenance=provenance,
                )
            )
    return sort_facts([*assessments, *unresolved])
