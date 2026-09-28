"""Broad replay benchmark for independent quality, usage and cost axes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
PROFILES = ("economy", "balanced", "deep")
MINIMUM_LABELED_TASKS = 50
MAX_INPUT_VOLUME_DELTA = 0.10
QUALITY_AXES = (
    "status",
    "evidence_recall",
    "false_positive_rate",
    "unresolved",
    "execution_plan",
)
Runner = Callable[[Mapping[str, Any], str], Mapping[str, Any]]


class ReplayBenchmarkError(ValueError):
    """Named benchmark validation or denominator error."""


def load_replay_suite(path: Path | str) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReplayBenchmarkError(f"replay_suite_unreadable:{target}") from exc
    if not isinstance(raw, Mapping) or raw.get("schema_version") != SCHEMA_VERSION:
        raise ReplayBenchmarkError("replay_suite_invalid:schema_version")
    suite_id = str(raw.get("suite_id", "")).strip()
    profiles = tuple(str(item) for item in raw.get("profiles", ()))
    cases = raw.get("cases")
    if not suite_id or profiles != PROFILES or not isinstance(cases, list):
        raise ReplayBenchmarkError("replay_suite_invalid:identity_or_profiles")
    if len(cases) < MINIMUM_LABELED_TASKS:
        raise ReplayBenchmarkError(
            f"replay_suite_incomplete:minimum_{MINIMUM_LABELED_TASKS}_cases"
        )
    normalized: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ReplayBenchmarkError("replay_case_invalid:object")
        required = {
            "id",
            "domain",
            "partition",
            "expected_status",
            "label",
            "input_manifest",
        }
        if not required <= set(case):
            missing = ",".join(sorted(required - set(case)))
            raise ReplayBenchmarkError(f"replay_case_invalid:missing:{missing}")
        if not str(case.get("label", "")).strip():
            raise ReplayBenchmarkError(f"replay_case_invalid:empty_label:{case['id']}")
        if not isinstance(case.get("input_manifest"), Mapping):
            raise ReplayBenchmarkError(
                f"replay_case_invalid:input_manifest:{case['id']}"
            )
        normalized.append(dict(case))
    ids = [str(case["id"]) for case in normalized]
    domains = {str(case["domain"]) for case in normalized}
    if len(set(ids)) != len(ids):
        raise ReplayBenchmarkError("replay_case_ids_must_be_unique")
    if len(domains) < 6:
        raise ReplayBenchmarkError("replay_suite_incomplete:minimum_6_domains")
    holdout = [case for case in normalized if case["partition"] == "holdout"]
    train = [case for case in normalized if case["partition"] == "train"]
    if not holdout or not train:
        raise ReplayBenchmarkError("replay_suite_requires_train_and_holdout")
    labeled_tasks = sum(1 for case in normalized if str(case.get("label", "")).strip())
    if labeled_tasks < MINIMUM_LABELED_TASKS:
        raise ReplayBenchmarkError(
            f"replay_suite_incomplete:minimum_{MINIMUM_LABELED_TASKS}_labels"
        )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "suite_id": suite_id,
        "profiles": profiles,
        "quality_axes": QUALITY_AXES,
        "cases": tuple(normalized),
        "train_case_ids": tuple(str(case["id"]) for case in train),
        "holdout_case_ids": tuple(str(case["id"]) for case in holdout),
        "labeled_tasks": labeled_tasks,
        "minimum_labeled_tasks": MINIMUM_LABELED_TASKS,
        "same_case_required": True,
        "same_input_manifest_required": True,
        "max_input_volume_delta": MAX_INPUT_VOLUME_DELTA,
        "cost_requires_basis": True,
        "sha256": digest,
        "path": target.as_posix(),
    }


def run_replay_benchmark(
    suite: Mapping[str, Any], *, old_runner: Runner, new_runner: Runner
) -> dict[str, Any]:
    cases = suite.get("cases")
    profiles = tuple(str(item) for item in suite.get("profiles", ()))
    if not isinstance(cases, (list, tuple)) or profiles != PROFILES:
        raise ReplayBenchmarkError("replay_suite_invalid:loaded_shape")
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ReplayBenchmarkError("replay_case_invalid:loaded_shape")
        for profile in profiles:
            old = old_runner(case, profile)
            new = new_runner(case, profile)
            rows.append(_row(case, profile, "old", old))
            rows.append(_row(case, profile, "new", new))
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": {
            "suite_id": str(suite["suite_id"]),
            "sha256": str(suite["sha256"]),
            "profiles": list(profiles),
        },
        "quality_axes": list(QUALITY_AXES),
        "benchmark_contract": {
            "labeled_tasks": int(suite.get("labeled_tasks", len(cases))),
            "minimum_labeled_tasks": int(
                suite.get("minimum_labeled_tasks", MINIMUM_LABELED_TASKS)
            ),
            "same_case_required": bool(suite.get("same_case_required", True)),
            "same_input_manifest_required": bool(
                suite.get("same_input_manifest_required", True)
            ),
            "max_input_volume_delta": float(
                suite.get("max_input_volume_delta", MAX_INPUT_VOLUME_DELTA)
            ),
            "cost_requires_basis": bool(suite.get("cost_requires_basis", True)),
        },
        "rows": rows,
        "summary": _summary(rows),
    }


def compare_replay_benchmark(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    left_suite = before.get("suite") or {}
    right_suite = after.get("suite") or {}
    if (
        left_suite.get("suite_id") != right_suite.get("suite_id")
        or left_suite.get("sha256") != right_suite.get("sha256")
    ):
        return {
            "schema_version": SCHEMA_VERSION,
            "refused": {"reason": "suite_mismatch"},
            "cells": [],
        }
    left = {
        (str(row["case_id"]), str(row["profile"]), str(row["runner"])): row
        for row in before.get("rows", [])
    }
    right = {
        (str(row["case_id"]), str(row["profile"]), str(row["runner"])): row
        for row in after.get("rows", [])
    }
    if set(left) != set(right):
        return {
            "schema_version": SCHEMA_VERSION,
            "refused": {"reason": "replay_cells_mismatch"},
            "cells": [],
        }
    for key in sorted(left):
        old = left[key]
        new = right[key]
        if old.get("label") != new.get("label"):
            return {
                "schema_version": SCHEMA_VERSION,
                "refused": {
                    "reason": "label_mismatch",
                    "case_id": key[0],
                    "profile": key[1],
                    "runner": key[2],
                },
                "cells": [],
            }
        if old.get("input_manifest") != new.get("input_manifest"):
            return {
                "schema_version": SCHEMA_VERSION,
                "refused": {
                    "reason": "input_manifest_mismatch",
                    "case_id": key[0],
                    "profile": key[1],
                    "runner": key[2],
                },
                "cells": [],
            }
        old_volume = old.get("input_volume_bytes")
        new_volume = new.get("input_volume_bytes")
        if isinstance(old_volume, (int, float)) and isinstance(new_volume, (int, float)):
            denominator = max(abs(float(old_volume)), 1.0)
            if abs(float(new_volume) - float(old_volume)) / denominator > MAX_INPUT_VOLUME_DELTA:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "refused": {
                        "reason": "input_volume_mismatch",
                        "case_id": key[0],
                        "profile": key[1],
                        "runner": key[2],
                        "before": old_volume,
                        "after": new_volume,
                        "max_delta": MAX_INPUT_VOLUME_DELTA,
                    },
                    "cells": [],
                }
    cells = []
    for key in sorted(left):
        old = left[key]
        new = right[key]
        cells.append(
            {
                "case_id": key[0],
                "profile": key[1],
                "runner": key[2],
                "label": new.get("label"),
                "input_manifest": new.get("input_manifest"),
                "quality": {
                    axis: {"before": old["quality"].get(axis), "after": new["quality"].get(axis)}
                    for axis in QUALITY_AXES
                },
                "payload_bytes": _delta(old.get("payload_bytes"), new.get("payload_bytes")),
                "provider_tokens": {
                    "before": old.get("provider_tokens"),
                    "after": new.get("provider_tokens"),
                    "tokens_unresolved": {
                        "before": old.get("tokens_unresolved"),
                        "after": new.get("tokens_unresolved"),
                    },
                },
                "cost": _cost_delta(old, new),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": dict(left_suite),
        "quality_axes": list(QUALITY_AXES),
        "cells": cells,
    }


def _row(
    case: Mapping[str, Any], profile: str, runner: str, observation: Mapping[str, Any]
) -> dict[str, Any]:
    expected_evidence = {str(item) for item in case.get("expected_evidence", ())}
    observed_evidence = {str(item) for item in observation.get("observed_evidence", ())}
    expected_findings = {str(item) for item in case.get("expected_findings", ())}
    observed_findings = {str(item) for item in observation.get("observed_findings", ())}
    evidence_recall = (
        len(expected_evidence & observed_evidence) / len(expected_evidence)
        if expected_evidence
        else None
    )
    false_positive_rate = (
        len(observed_findings - expected_findings) / len(observed_findings)
        if observed_findings
        else 0.0
    )
    unresolved = tuple(str(item) for item in observation.get("unresolved", ()))
    quality = {
        "status": observation.get("status"),
        "evidence_recall": evidence_recall,
        "false_positive_rate": false_positive_rate,
        "unresolved": list(unresolved),
        "execution_plan": observation.get("execution_plan"),
    }
    cost_basis = observation.get("cost_basis")
    cost_value = observation.get("cost") if isinstance(cost_basis, Mapping) else None
    cost_status = "measured" if cost_value is not None and cost_basis else "unresolved"
    provider_tokens = observation.get("provider_tokens")
    tokens_unresolved = bool(observation.get("tokens_unresolved", provider_tokens is None))
    if provider_tokens is not None and tokens_unresolved:
        raise ReplayBenchmarkError(
            f"replay_observation_invalid:tokens_unresolved_with_value:{case['id']}"
        )
    input_manifest = dict(case["input_manifest"])
    input_volume_bytes = input_manifest.get("bytes")
    if not isinstance(input_volume_bytes, (int, float)) or input_volume_bytes < 0:
        raise ReplayBenchmarkError(f"replay_case_invalid:input_bytes:{case['id']}")
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": str(case["id"]),
        "domain": str(case["domain"]),
        "partition": str(case["partition"]),
        "label": str(case["label"]),
        "profile": profile,
        "runner": runner,
        "quality": quality,
        "status": observation.get("status"),
        "payload_bytes": observation.get("payload_bytes"),
        "provider_tokens": provider_tokens,
        "tokens_unresolved": tokens_unresolved,
        "tokens_unresolved_reason": (
            observation.get("tokens_unresolved_reason") or "provider_transcript_absent"
            if tokens_unresolved
            else None
        ),
        "input_manifest": input_manifest,
        "input_volume_bytes": input_volume_bytes,
        "cost": {"value": cost_value, "status": cost_status, "basis": cost_basis},
        "cost_basis": cost_basis,
        "cost_unresolved_reason": (
            None
            if cost_status == "measured"
            else (
                "cost_basis_absent"
                if not isinstance(cost_basis, Mapping)
                else "cost_value_absent"
            )
        ),
        "unresolved": list(unresolved),
        "provenance": {
            "case_partition": str(case["partition"]),
            "transcript_hash": case.get("transcript_hash"),
            "suite_case_hash": hashlib.sha256(
                json.dumps(dict(case), sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for runner in ("old", "new"):
        for profile in PROFILES:
            selected = [
                row for row in rows if row["runner"] == runner and row["profile"] == profile
            ]
            cost_rows = [row for row in selected if row["cost"]["status"] == "measured"]
            result[f"{runner}:{profile}"] = {
                "cases": len(selected),
                "status": _counts(selected, "status"),
                "evidence_recall": _mean(
                    [row["quality"]["evidence_recall"] for row in selected]
                ),
                "false_positive_rate": _mean(
                    [row["quality"]["false_positive_rate"] for row in selected]
                ),
                "payload_bytes": _mean([row.get("payload_bytes") for row in selected]),
                "provider_tokens_resolved": sum(
                    1 for row in selected if not row["tokens_unresolved"]
                ),
                "tokens_unresolved": sum(
                    1 for row in selected if row["tokens_unresolved"]
                ),
                "cost": {
                    "measured_cases": len(cost_rows),
                    "denominator": len(cost_rows),
                    "value": _mean([row["cost"]["value"] for row in cost_rows]),
                },
            }
    return result


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _mean(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numbers) / len(numbers) if numbers else None


def _delta(before: Any, after: Any) -> dict[str, Any]:
    delta = (
        after - before
        if isinstance(before, (int, float)) and isinstance(after, (int, float))
        else None
    )
    return {"before": before, "after": after, "delta": delta}


def _cost_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    left = before.get("cost") or {}
    right = after.get("cost") or {}
    if left.get("status") != "measured" or right.get("status") != "measured":
        return {
            "status": "unresolved",
            "reason": "cost_basis_absent",
            "before_basis": left.get("basis"),
            "after_basis": right.get("basis"),
        }
    return _delta(left.get("value"), right.get("value")) | {"status": "measured"}


__all__ = [
    "PROFILES",
    "MINIMUM_LABELED_TASKS",
    "MAX_INPUT_VOLUME_DELTA",
    "QUALITY_AXES",
    "ReplayBenchmarkError",
    "compare_replay_benchmark",
    "load_replay_suite",
    "run_replay_benchmark",
]
