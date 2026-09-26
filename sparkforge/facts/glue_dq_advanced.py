"""Offline facts for AWS Glue Data Quality recommendation governance."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "glue_dq_advanced@0.1.0"
EMITTED_KINDS = frozenset(
    {
        "dq.ai.recommendation",
        "dq.ai.recommendation.unresolved",
        "dq.ai.review",
        "dq.ai.review.unresolved",
        "dq.ai.analyzed",
    }
)

_MODES = frozenset({"BASIC", "ADVANCED"})
_PROHIBITED_ADVANCED_ARGUMENTS = frozenset(
    {"PreProcessingQuery", "NumberOfWorkers", "Timeout", "AdditionalRunOptions"}
)
_ROW_KEYS = frozenset(
    {"rows", "records", "sample", "sampled_rows", "query_result", "row_data"}
)


class RowPayloadRejected(ValueError):
    """Input contains a field that may carry table rows."""

    def __init__(self, field_path: str):
        super().__init__(field_path)
        self.field_path = field_path


def reject_row_payload(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text in _ROW_KEYS:
                raise RowPayloadRejected(f"{path}.{key_text}")
            reject_row_payload(child, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_row_payload(child, f"{path}[{index}]")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _subject(payload: Mapping[str, Any], path: str) -> dict[str, Any]:
    table = payload.get("table")
    if isinstance(table, Mapping):
        name = table.get("name") or table.get("table_name")
        database = table.get("database") or table.get("database_name")
        if isinstance(name, str) and name:
            subject: dict[str, Any] = {"type": "table", "symbol": name}
            if isinstance(database, str) and database:
                subject["database"] = database
            return subject
    name = payload.get("table_name")
    if isinstance(name, str) and name:
        return {"type": "table", "symbol": name}
    return {"type": "source_location", "file": path, "line": 0, "col": 0, "symbol": ""}


def _provenance(path: str, artifact_sha256: str) -> dict[str, Any]:
    return {
        "extractor": EXTRACTOR_ID,
        "artifact": path,
        "artifact_sha256": artifact_sha256,
    }


def _unresolved(
    *,
    kind: str,
    subject: dict[str, Any],
    path: str,
    artifact_sha256: str,
    reason: str,
    **attrs: Any,
) -> Fact:
    return Fact(
        kind=kind,
        subject=subject,
        attrs={"reason": reason, **attrs},
        provenance=_provenance(path, artifact_sha256),
    )


def _normal_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _scalar_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): child
        for key, child in value.items()
        if isinstance(child, (str, int, float, bool))
    }


def _mode(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("recommendation_mode", payload.get("mode"))
    if not isinstance(value, str):
        return None
    return value.strip().upper()


def _arguments(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("arguments", {})
    names: set[str] = set()
    if isinstance(raw, Mapping):
        names.update(str(key) for key in raw)
    raw_names = payload.get("prohibited_arguments", [])
    if isinstance(raw_names, Sequence) and not isinstance(raw_names, (str, bytes)):
        names.update(str(value) for value in raw_names)
    return sorted(names & _PROHIBITED_ADVANCED_ARGUMENTS)


def _recommendation_facts(
    payload: Mapping[str, Any], path: str, artifact_sha256: str
) -> list[Fact]:
    subject = _subject(payload, path)
    mode = _mode(payload)
    if mode not in _MODES:
        reason = "mode_missing" if mode is None else "mode_invalid"
        return [
            _unresolved(
                kind="dq.ai.recommendation.unresolved",
                subject=subject,
                path=path,
                artifact_sha256=artifact_sha256,
                reason=reason,
                received_mode=mode or "",
            )
        ]

    sampling = payload.get("sampling")
    sampling_map = sampling if isinstance(sampling, Mapping) else {}
    geography = payload.get("geography")
    geography_map = geography if isinstance(geography, Mapping) else {}
    kms = payload.get("kms")
    kms_map = kms if isinstance(kms, Mapping) else {}
    authorization = payload.get("authorization")
    authorization_map = authorization if isinstance(authorization, Mapping) else {}
    risk_context = _scalar_metadata(payload.get("risk"))
    iceberg_context = _scalar_metadata(payload.get("iceberg"))
    migration_context = _scalar_metadata(payload.get("migration"))
    source_region = _normal_string(payload.get("source_region"))
    inference_region = _normal_string(payload.get("inference_region"))
    classification = _normal_string(payload.get("classification"))
    runtime_version = _normal_string(payload.get("runtime_version", payload.get("runtime")))
    retention = sampling_map.get("retention_days", payload.get("retention_days"))
    retention_days = (
        retention if isinstance(retention, int) and not isinstance(retention, bool) else None
    )
    bucket = _normal_string(sampling_map.get("bucket", payload.get("sampling_bucket")))
    workgroup = _normal_string(
        sampling_map.get("workgroup", payload.get("sampling_workgroup"))
    )
    source_geography = _normal_string(
        geography_map.get("source", payload.get("source_geography"))
    )
    inference_geography = _normal_string(
        geography_map.get("inference", payload.get("inference_geography"))
    )
    geographic_boundary_status = _normal_string(
        geography_map.get(
            "boundary_status", payload.get("geographic_boundary_status")
        )
    )
    if geographic_boundary_status:
        geographic_boundary_status = geographic_boundary_status.lower()
    if geographic_boundary_status not in {
        "same",
        "approved",
        "disallowed",
        "unresolved",
    }:
        geographic_boundary_status = "unresolved"
    kms_status = _normal_string(kms_map.get("status", payload.get("kms_status")))
    key_policy_status = _normal_string(
        authorization_map.get(
            "key_policy_status",
            kms_map.get("key_policy_status", payload.get("key_policy_status")),
        )
    )
    runtime_role_status = _normal_string(
        authorization_map.get(
            "runtime_role_status",
            kms_map.get("runtime_role_status", payload.get("runtime_role_status")),
        )
    )
    lakeformation_status = _normal_string(
        authorization_map.get(
            "lakeformation_status",
            kms_map.get("lakeformation_status", payload.get("lakeformation_status")),
        )
    )
    kms_required = kms_map.get("required", payload.get("kms_required"))
    if kms_status is None and kms_required is True:
        kms_status = "unresolved"
    review_status = _normal_string(payload.get("human_review_status"))
    incompatible_args = _arguments(payload) if mode == "ADVANCED" else []
    if source_region and inference_region:
        cross_region_status = "true" if source_region != inference_region else "false"
    else:
        cross_region_status = "unresolved"
    if isinstance(payload.get("cross_region_inference"), bool):
        cross_region_status = "true" if payload["cross_region_inference"] else "false"

    exposure_labels = ["BEDROCK_DATA_EXPOSURE", "ATHENA_SAMPLING"] if mode == "ADVANCED" else []
    if cross_region_status == "true":
        exposure_labels.append("CROSS_REGION_INFERENCE")
    if bucket or retention_days is not None:
        exposure_labels.append("SAMPLING_BUCKET_RETENTION")
    if kms_required is True or kms_status is not None:
        exposure_labels.append("KMS_REQUIREMENTS")

    attrs: dict[str, Any] = {
        "mode": mode,
        "runtime_version": runtime_version or "",
        "source_region": source_region or "",
        "inference_region": inference_region or "",
        "cross_region_status": cross_region_status,
        "classification": classification or "",
        "classification_status": "declared" if classification else "unresolved",
        "sampling_bucket": bucket or "",
        "sampling_bucket_status": "declared" if bucket else "unresolved",
        "sampling_workgroup": workgroup or "",
        "sampling_workgroup_status": "declared" if workgroup else "unresolved",
        "sampling_retention_status": "declared" if retention_days is not None else "unresolved",
        "source_geography": source_geography or "",
        "inference_geography": inference_geography or "",
        "geographic_boundary_status": geographic_boundary_status,
        "kms_status": kms_status or "",
        "key_policy_status": key_policy_status or "",
        "runtime_role_status": runtime_role_status or "",
        "lakeformation_status": lakeformation_status or "",
        "human_review_status": review_status or "",
        "incompatible_args": incompatible_args,
        "exposure_labels": exposure_labels,
        "payload_scope": "metadata_only",
        "recommendation_variability": "possible" if mode == "ADVANCED" else "not_applicable",
        "review_required": mode == "ADVANCED",
    }
    if risk_context:
        attrs["risk_context"] = risk_context
    if iceberg_context:
        attrs["iceberg_context"] = iceberg_context
    if migration_context:
        attrs["migration_context"] = migration_context
    if retention_days is not None:
        attrs["retention_days"] = retention_days
    kms_key_arn = _normal_string(kms_map.get("key_arn", payload.get("kms_key_arn")))
    if kms_key_arn:
        attrs["kms_key_arn"] = kms_key_arn
    return [
        Fact(
            kind="dq.ai.recommendation",
            subject=subject,
            measures={"attribute_count": len(attrs)},
            attrs=attrs,
            provenance=_provenance(path, artifact_sha256),
        )
    ]


def _review_facts(payload: Mapping[str, Any], path: str, artifact_sha256: str) -> list[Fact]:
    review = payload.get("review")
    if not isinstance(review, Mapping) and "human_review_status" in payload:
        review = {
            "status": payload.get("human_review_status"),
            "ref": payload.get("human_review_ref", ""),
        }
    if not isinstance(review, Mapping):
        return []
    status = _normal_string(review.get("status"))
    subject = _subject(payload, path)
    if status not in {"declared", "missing", "unresolved"}:
        return [
            _unresolved(
                kind="dq.ai.review.unresolved",
                subject=subject,
                path=path,
                artifact_sha256=artifact_sha256,
                reason="review_status_invalid",
            )
        ]
    attrs = {"status": status, "review_ref": _normal_string(review.get("ref")) or ""}
    return [
        Fact(
            kind="dq.ai.review",
            subject=subject,
            attrs=attrs,
            provenance=_provenance(path, artifact_sha256),
        )
    ]


def extract_glue_dq_advanced(
    payload: Mapping[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload precisa ser um objeto")
    reject_row_payload(payload)
    facts = _recommendation_facts(payload, path, artifact_sha256)
    facts.extend(_review_facts(payload, path, artifact_sha256))
    unresolved_count = sum(1 for fact in facts if fact.kind.endswith(".unresolved"))
    facts.append(
        Fact(
            kind="dq.ai.analyzed",
            subject={"type": "source_location", "file": path, "line": 0, "col": 0, "symbol": ""},
            measures={"fact_count": len(facts), "unresolved_count": unresolved_count},
            attrs={"payload_scope": "metadata_only"},
            provenance=_provenance(path, artifact_sha256),
        )
    )
    return sort_facts(facts)


def _load_payload(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError("payload precisa ser um objeto")
    return payload


def extract_glue_dq_advanced_path(path: str | Path) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    try:
        payload = _load_payload(target)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"{target}: payload invalido: {exc}") from exc
    try:
        return extract_glue_dq_advanced(payload, str(target), _sha256(target))
    except RowPayloadRejected as exc:
        return sort_facts(
            [
                _unresolved(
                    kind="dq.ai.recommendation.unresolved",
                    subject={
                        "type": "source_location",
                        "file": str(target),
                        "line": 0,
                        "col": 0,
                        "symbol": "",
                    },
                    path=str(target),
                    artifact_sha256=_sha256(target),
                    reason="row_payload_rejected",
                    field_path=exc.field_path,
                )
            ]
        )


def extract_glue_dq_advanced_tree(path: str | Path) -> list[Fact]:
    target = Path(path)
    if target.is_file():
        return extract_glue_dq_advanced_path(target)
    if not target.is_dir():
        raise FileNotFoundError(str(target))
    facts: list[Fact] = []
    for entry in sorted(target.iterdir()):
        if entry.is_file() and entry.suffix.lower() in {".json", ".yaml", ".yml"}:
            payload = _load_payload(entry)
            recommendation_markers = {"recommendation_mode", "mode", "table", "table_name"}
            if not recommendation_markers.intersection(payload):
                continue
            facts.extend(extract_glue_dq_advanced_path(entry))
    return sort_facts(facts)


def extract_dq_review_path(path: str | Path, subject: dict[str, Any] | None = None) -> list[Fact]:
    """Read a small human-review manifest; never reads recommendation rows."""
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    payload = _load_payload(target)
    review = payload.get("review", payload)
    if not isinstance(review, Mapping):
        raise ValueError("review precisa ser um objeto")
    status = _normal_string(review.get("status"))
    target_subject = subject or _subject(payload, str(target))
    provenance = _provenance(str(target), _sha256(target))
    if status not in {"declared", "missing", "unresolved"}:
        return [
            Fact(
                kind="dq.ai.review.unresolved",
                subject=target_subject,
                attrs={"reason": "review_status_invalid"},
                provenance=provenance,
            )
        ]
    return [
        Fact(
            kind="dq.ai.review",
            subject=target_subject,
            attrs={"status": status, "review_ref": _normal_string(review.get("ref")) or ""},
            provenance=provenance,
        )
    ]
