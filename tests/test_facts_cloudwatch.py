"""Testes do extrator do artefato CloudWatch em Facts."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.cloudwatch import extract_cloudwatch_path


def _artifact(tmp_path: Path, results: list[dict], period: int = 60) -> Path:
    payload = {
        "job_name": "my-job",
        "job_run_id": "jr_1",
        "start": "2026-08-26T10:00:00Z",
        "end": "2026-08-26T10:20:00Z",
        "period_seconds": period,
        "metric_data_results": results,
    }
    target = tmp_path / "cw.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestExtract:
    def test_emits_one_fact_per_metric_with_values(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {
                    "Id": "m0",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": ["t1", "t2", "t3"],
                    "Values": [0.3, 0.9, 0.6],
                }
            ],
        )

        facts = extract_cloudwatch_path(target)
        metric = [f for f in facts if f.kind == "glue.metric"]

        assert len(metric) == 1
        assert metric[0].subject == {"job_name": "my-job", "job_run_id": "jr_1"}
        assert metric[0].attrs["name"] == "glue.driver.workerUtilization"
        assert metric[0].attrs["period_s"] == 60
        assert metric[0].measures["min"] == 0.3
        assert metric[0].measures["max"] == 0.9
        assert metric[0].measures["p50"] == 0.6
        assert metric[0].measures["datapoints"] == 3

    def test_carries_the_stat_the_metric_requires(self, tmp_path):
        target = _artifact(
            tmp_path,
            [{"Id": "m0", "Label": "glue.error.ALL", "Timestamps": ["t1"], "Values": [2.0]}],
        )

        fact = [f for f in extract_cloudwatch_path(target) if f.kind == "glue.metric"][0]
        assert fact.attrs["stat"] == "Sum"

    def test_empty_series_becomes_unresolved_not_a_zero(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {
                    "Id": "m0",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": [],
                    "Values": [],
                }
            ],
        )

        facts = extract_cloudwatch_path(target)
        assert not [f for f in facts if f.kind == "glue.metric"]
        unresolved = [f for f in facts if f.kind == "glue.metric.unresolved"]
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "empty_series"

    def test_analyzed_fact_declares_the_counts(self, tmp_path):
        target = _artifact(
            tmp_path,
            [
                {"Id": "m0", "Label": "glue.error.ALL", "Timestamps": ["t"], "Values": [1.0]},
                {
                    "Id": "m1",
                    "Label": "glue.driver.workerUtilization",
                    "Timestamps": [],
                    "Values": [],
                },
            ],
        )

        analyzed = [f for f in extract_cloudwatch_path(target) if f.kind == "glue.metric.analyzed"]
        assert len(analyzed) == 1
        assert analyzed[0].measures == {"metrics_with_data": 1, "metrics_empty": 1}
