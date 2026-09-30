"""Canonical metric derivation for replay and external evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sparkforge.evals.decision_replay import compare_replay_benchmark


class MetricCompilationError(ValueError):
    """Named failure while deriving metrics from primitive reports."""


def compile_reports(
    reports: Mapping[str, Any], *, require_raw: bool = False
) -> dict[str, dict[str, Any]]:
    """Compile canonical metrics without trusting producer-derived metrics.

    ``reports.derived_metrics`` is deliberately ignored. The compact report
    shape remains readable for legacy/surrogate fixtures; recorded and live
    execution must provide paired primitive rows.
    """
    baseline = reports.get("baseline")
    candidate = reports.get("candidate")
    if isinstance(baseline, Mapping) and isinstance(candidate, Mapping):
        baseline_rows = baseline.get("rows")
        candidate_rows = candidate.get("rows")
        if isinstance(baseline_rows, list) and isinstance(candidate_rows, list):
            comparison = compare_replay_benchmark(baseline, candidate)
            if comparison.get("refused") is not None:
                raise MetricCompilationError("metrics_unresolved")
            metrics = comparison.get("metrics")
            if not isinstance(metrics, Mapping):
                raise MetricCompilationError("metrics_unresolved")
            candidate_metrics = metrics.get("candidate")
            if not isinstance(candidate_metrics, Mapping):
                raise MetricCompilationError("metrics_unresolved")
            return {
                "comparison": dict(comparison),
                "quality": _quality_metrics(candidate_metrics),
                "economy": _economy_metrics(candidate_metrics),
            }
        if require_raw:
            raise MetricCompilationError("metrics_unresolved")

    if require_raw:
        raise MetricCompilationError("metrics_unresolved")

    comparison = reports.get("comparison")
    if isinstance(comparison, Mapping):
        return {
            "comparison": dict(comparison),
            "quality": _mapping_or_empty(reports.get("quality")),
            "economy": _mapping_or_empty(reports.get("economy")),
        }

    if isinstance(baseline, Mapping) and isinstance(candidate, Mapping):
        baseline_metrics = baseline.get("metrics")
        candidate_metrics = candidate.get("metrics")
        if isinstance(baseline_metrics, Mapping) and isinstance(candidate_metrics, Mapping):
            return {
                "comparison": {
                    "metrics": {
                        "baseline": dict(baseline_metrics),
                        "candidate": dict(candidate_metrics),
                    },
                    "cells": list(reports.get("cells", [])),
                },
                "quality": _mapping_or_empty(reports.get("quality")),
                "economy": _mapping_or_empty(reports.get("economy")),
            }
    raise MetricCompilationError("metrics_unresolved")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _quality_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: metrics.get(name)
        for name in (
            "status_accuracy",
            "evidence_recall",
            "false_positive_rate",
            "route_accuracy",
        )
    }


def _economy_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: metrics.get(name)
        for name in (
            "payload_bytes_mean",
            "provider_tokens_mean",
            "cost_mean",
        )
    }


__all__ = ["MetricCompilationError", "compile_reports"]
