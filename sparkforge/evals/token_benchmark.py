"""Deterministic quality and payload benchmark for Gateway profiles."""

from __future__ import annotations

import copy
import hashlib
import statistics
from pathlib import Path
from typing import Any

import yaml

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_models import GatewayProfile
from sparkforge.evals.runner import EvaluationRunner

SCHEMA_VERSION = 1
DEFAULT_AXES = (
    "status",
    "evidence_recall",
    "false_positive_rate",
    "unresolved",
    "execution_plan",
)


def load_benchmark_suite(directory: Path | str) -> dict[str, Any]:
    """Load suite and fixture gabarito from one versioned directory."""
    root = Path(directory).expanduser().resolve()
    suite_path = root / "suite.yaml"
    raw = _load_mapping(suite_path, "benchmark suite")
    declared_fixture = raw.get("quality_fixture", "fixtures/quality_cases.yaml")
    if not isinstance(declared_fixture, str) or not declared_fixture.strip():
        raise ValueError("quality_fixture must be a non-empty relative path")
    fixture_path = _fixture_path(root, declared_fixture, "quality_fixture")
    fixture = _load_mapping(fixture_path, "quality fixture")
    if not isinstance(raw, dict) or not isinstance(fixture, dict):
        raise ValueError("benchmark suite and fixture must be mappings")
    if int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError("unsupported benchmark suite schema_version")
    if int(fixture.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError("unsupported quality fixture schema_version")
    cases = raw.get("cases")
    expected = fixture.get("cases")
    axes = tuple(str(axis) for axis in raw.get("quality_axes", ()))
    if not isinstance(cases, list) or not isinstance(expected, list) or not axes:
        raise ValueError("benchmark suite requires cases and quality_axes")
    by_id = {str(item.get("id")): item for item in expected if isinstance(item, dict)}
    if len(by_id) != len(expected) or {str(item.get("id")) for item in cases} != set(by_id):
        raise ValueError("suite and quality fixture case ids must match")
    merged = []
    for case in cases:
        if not isinstance(case, dict) or str(case.get("id")) not in by_id:
            raise ValueError("benchmark case is invalid")
        merged.append({**case, **by_id[str(case["id"])], "suite_id": str(raw["id"])})
    fixture_paths = [fixture_path]
    for key in ("federated_graph_fixture", "provider_transcript_fixture"):
        declared = raw.get(key)
        if declared is None:
            continue
        if not isinstance(declared, str) or not declared.strip():
            raise ValueError(f"{key} must be a non-empty relative path")
        additional_path = _fixture_path(root, declared, key)
        additional = _load_mapping(additional_path, key)
        if int(additional.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ValueError(f"unsupported {key} schema_version")
        fixture_paths.append(additional_path)
    decision_fixture_path = None
    declared_decision = raw.get("decision_fixture")
    if declared_decision is not None:
        if not isinstance(declared_decision, str) or not declared_decision.strip():
            raise ValueError("decision_fixture must be a non-empty relative path")
        decision_fixture_path = _fixture_path(root, declared_decision, "decision_fixture")
        decision_fixture = _load_mapping(decision_fixture_path, "decision_fixture")
        if int(decision_fixture.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ValueError("unsupported decision_fixture schema_version")
    digest_input = suite_path.read_bytes()
    for path in fixture_paths:
        digest_input += b"\n" + path.read_bytes()
    if decision_fixture_path is not None:
        digest_input += b"\n" + decision_fixture_path.read_bytes()
    digest = hashlib.sha256(digest_input).hexdigest()
    return {
        "schema_version": int(raw.get("schema_version", 0)),
        "id": str(raw["id"]),
        "baseline_id": str(raw["baseline_id"]),
        "profiles": tuple(str(profile) for profile in raw.get("profiles", ())),
        "quality_axes": axes,
        "cases": merged,
        "fixture_paths": tuple(path.relative_to(root).as_posix() for path in fixture_paths),
        "decision_fixture_path": (
            decision_fixture_path.relative_to(root).as_posix()
            if decision_fixture_path is not None
            else None
        ),
        "sha256": digest,
    }


def run_benchmark_matrix(
    suite: dict[str, Any], *, gateway: ContextGateway | None = None
) -> dict[str, Any]:
    """Run identical cases over all declared profiles and keep raw axes."""
    runner = EvaluationRunner()
    gateway_to_use = gateway or ContextGateway(TOOLS)
    profiles = tuple(GatewayProfile(profile) for profile in suite["profiles"])
    results = runner.run_context_benchmark(
        gateway_to_use,
        list(suite["cases"]),
        baseline_id=str(suite["baseline_id"]),
        profiles=profiles,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": {
            "id": str(suite["id"]),
            "sha256": str(suite["sha256"]),
            "baseline_id": str(suite["baseline_id"]),
        },
        "profiles": list(suite["profiles"]),
        "quality_axes": list(suite["quality_axes"]),
        "fixture_paths": list(suite.get("fixture_paths", ())),
        "decision_fixture_path": suite.get("decision_fixture_path"),
        "results": results,
        "summary": _summary(results, suite["profiles"]),
    }


def compare_benchmark_matrix(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    """Compare two matrices without inventing a composite quality score."""
    before_suite = before.get("suite") or {}
    after_suite = after.get("suite") or {}
    if (
        before_suite.get("id") != after_suite.get("id")
        or before_suite.get("sha256") != after_suite.get("sha256")
    ):
        return {
            "schema_version": SCHEMA_VERSION,
            "refused": {"reason": "suite_mismatch"},
            "cells": [],
        }
    if tuple(before.get("quality_axes", ())) != tuple(after.get("quality_axes", ())):
        return {
            "schema_version": SCHEMA_VERSION,
            "refused": {"reason": "quality_axes_mismatch"},
            "cells": [],
        }
    left = {
        (str(item["case_id"]), str(item["profile"])): item
        for item in before.get("results", [])
    }
    right = {
        (str(item["case_id"]), str(item["profile"])): item
        for item in after.get("results", [])
    }
    if set(left) != set(right):
        return {
            "schema_version": SCHEMA_VERSION,
            "refused": {"reason": "matrix_cells_mismatch"},
            "cells": [],
        }
    cells = []
    for key in sorted(left):
        old, new = left[key], right[key]
        quality = {}
        for axis in before["quality_axes"]:
            quality[axis] = {
                "before": _axis_value(old, axis),
                "after": _axis_value(new, axis),
            }
        old_bytes, new_bytes = old.get("payload_bytes"), new.get("payload_bytes")
        cells.append(
            {
                "case_id": key[0],
                "profile": key[1],
                "quality": quality,
                "payload_bytes": {
                    "before": old_bytes,
                    "after": new_bytes,
                    "delta": new_bytes - old_bytes
                    if isinstance(old_bytes, int) and isinstance(new_bytes, int)
                    else None,
                },
                "provider_tokens": {
                    "before": old.get("provider_tokens"),
                    "after": new.get("provider_tokens"),
                    "tokens_unresolved": {
                        "before": old.get("tokens_unresolved"),
                        "after": new.get("tokens_unresolved"),
                    },
                },
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": copy.deepcopy(before_suite),
        "quality_axes": list(before["quality_axes"]),
        "cells": cells,
    }


def _axis_value(result: dict[str, Any], axis: str) -> Any:
    if axis == "execution_plan":
        plan = result.get("execution_plan") or {}
        return plan.get("kind")
    if axis == "unresolved":
        return list(result.get("unresolved") or ())
    if axis == "status":
        return result.get("status")
    return result.get(axis)


def _summary(results: list[dict[str, Any]], profiles: tuple[str, ...]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for profile in profiles:
        current = [item for item in results if item.get("profile") == profile]
        output[profile] = {
            "cases": len(current),
            "passed": sum(1 for item in current if item.get("passed") is True),
            "failed": sum(1 for item in current if item.get("passed") is False),
            "status": _counts(current, "status"),
            "execution_plan": _counts(
                [
                    {"value": (item.get("execution_plan") or {}).get("kind")}
                    for item in current
                ],
                "value",
            ),
            "payload_bytes": _spread(
                [
                    item.get("payload_bytes")
                    for item in current
                    if isinstance(item.get("payload_bytes"), int)
                ]
            ),
            "evidence_recall": _spread(
                [
                    item.get("evidence_recall")
                    for item in current
                    if isinstance(item.get("evidence_recall"), (int, float))
                ]
            ),
            "false_positive_rate": _spread(
                [
                    item.get("false_positive_rate")
                    for item in current
                    if isinstance(item.get("false_positive_rate"), (int, float))
                ]
            ),
            "tokens_unresolved": sum(1 for item in current if item.get("tokens_unresolved")),
        }
    return output


def _counts(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _spread(values: list[int | float]) -> dict[str, int | float] | None:
    if not values:
        return None
    return {"median_low": statistics.median_low(values), "max": max(values)}


def _load_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{label} unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _fixture_path(root: Path, declared: str, key: str) -> Path:
    path = (root / declared).resolve()
    if root not in path.parents:
        raise ValueError(f"{key} must stay within benchmark directory")
    return path


__all__ = [
    "compare_benchmark_matrix",
    "load_benchmark_suite",
    "run_benchmark_matrix",
]
