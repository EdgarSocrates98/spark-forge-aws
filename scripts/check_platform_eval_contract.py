"""Validate the offline Platform Intelligence eval contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

QUALITY_AXES = {
    "fact_recall",
    "finding_precision",
    "false_positive_rate",
    "false_negative_rate",
    "unresolved_recall",
    "evidence_recall",
    "routing_accuracy",
    "architecture_conformance",
}
ECONOMY_AXES = {"context_bytes", "tool_calls", "provider_tokens_when_observable", "elapsed_ms"}
EXPECTED_FIELDS = {"facts", "findings", "architecture"}


def validate(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    errors: list[dict[str, Any]] = []
    if not isinstance(raw, dict):
        return {"valid": False, "errors": [{"code": "suite_root_invalid"}]}
    for field in ("schema_version", "id", "baseline_id", "quality_axes", "economy_axes", "cases"):
        if field not in raw:
            errors.append({"code": "suite_field_missing", "field": field})
    if not QUALITY_AXES.issubset(set(raw.get("quality_axes", []))):
        errors.append(
            {
                "code": "quality_axes_incomplete",
                "missing": sorted(QUALITY_AXES - set(raw.get("quality_axes", []))),
            }
        )
    if not ECONOMY_AXES.issubset(set(raw.get("economy_axes", []))):
        errors.append(
            {
                "code": "economy_axes_incomplete",
                "missing": sorted(ECONOMY_AXES - set(raw.get("economy_axes", []))),
            }
        )
    if raw.get("provider_token_policy") != "host_transcript_only":
        errors.append({"code": "provider_token_policy_invalid"})
    cases = raw.get("cases", [])
    if not isinstance(cases, list) or not cases:
        errors.append({"code": "cases_missing"})
        cases = []
    ids: set[str] = set()
    valid_cases = 0
    for case in cases:
        if not isinstance(case, dict):
            errors.append({"code": "case_invalid"})
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            errors.append({"code": "case_id_invalid", "id": case_id})
        ids.add(str(case_id))
        for field in (
            "domain",
            "intent",
            "artifact",
            "expected",
            "forbidden",
            "unresolved",
            "required_evidence",
            "routing",
            "economy",
        ):
            if field not in case:
                errors.append({"code": "case_field_missing", "case_id": case_id, "field": field})
        expected = case.get("expected")
        if not isinstance(expected, dict) or not EXPECTED_FIELDS.issubset(expected):
            errors.append({"code": "expected_shape_invalid", "case_id": case_id})
        economy = case.get("economy")
        if (
            not isinstance(economy, dict)
            or not isinstance(economy.get("max_context_bytes"), int)
            or not isinstance(economy.get("max_tool_calls"), int)
        ):
            errors.append({"code": "economy_shape_invalid", "case_id": case_id})
        if isinstance(economy, dict):
            provider_tokens = economy.get("provider_tokens")
            if provider_tokens != "unresolved_without_host_transcript" and not (
                isinstance(provider_tokens, dict) and provider_tokens.get("host_transcript_ref")
            ):
                errors.append({"code": "provider_tokens_without_transcript", "case_id": case_id})
        valid_cases += not any(error.get("case_id") == case_id for error in errors)
    return {
        "valid": not errors,
        "suite": str(source),
        "case_count": len(cases),
        "valid_case_count": int(valid_cases),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    result = validate(args.path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
