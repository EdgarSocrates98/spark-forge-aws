"""Testes do extrator de historico de runs Glue em Facts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.facts.glue_job_run import extract_glue_job_runs_path


def _write_run(root: Path, run_id: str, **extra) -> Path:
    run = {
        "Id": run_id,
        "JobName": "my-job",
        "JobRunState": "SUCCEEDED",
        "StartedOn": "2026-08-01T10:00:00+00:00",
        "CompletedOn": "2026-08-01T10:20:00+00:00",
        "ExecutionTime": 1200,
        "GlueVersion": "5.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Timeout": 60,
    }
    run.update(extra)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"my-job_{run_id}.json"
    target.write_text(json.dumps(run), encoding="utf-8")
    return target


class TestRunFacts:
    def test_emits_one_fact_per_run(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2")

        runs = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ]

        assert len(runs) == 2
        assert {f.subject["job_run_id"] for f in runs} == {"jr_1", "jr_2"}

    def test_static_capacity_derives_dpu_seconds(self, tmp_path):
        _write_run(tmp_path, "jr_1", WorkerType="G.2X", NumberOfWorkers=10, ExecutionTime=600)

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        # 10 workers x 2 DPU x 600 s
        assert fact.measures["dpu_seconds"] == 12000
        assert fact.attrs["dpu_source"] == "derived"
        assert "formula" in fact.provenance

    def test_autoscaling_uses_the_observed_value(self, tmp_path):
        _write_run(
            tmp_path,
            "jr_1",
            DPUSeconds=4321.0,
            Arguments={"--enable-auto-scaling": "true"},
        )

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        assert fact.measures["dpu_seconds"] == 4321.0
        assert fact.attrs["dpu_source"] == "observed"

    def test_autoscaling_without_dpu_seconds_refuses(self, tmp_path):
        _write_run(tmp_path, "jr_1", Arguments={"--enable-auto-scaling": "true"})

        facts = extract_glue_job_runs_path(tmp_path, "my-job")
        run = [f for f in facts if f.kind == "glue.job_run"][0]
        unresolved = [f for f in facts if f.kind == "glue.job_run.unresolved"]

        assert "dpu_seconds" not in run.measures
        assert any(f.attrs["reason"] == "dpu_unobservable_under_autoscaling" for f in unresolved)

    def test_error_message_never_enters_the_fact(self, tmp_path):
        _write_run(
            tmp_path,
            "jr_1",
            JobRunState="FAILED",
            ErrorMessage="s3://bucket-secreto/tabela/parte-0001 nao encontrado",
        )

        fact = [
            f for f in extract_glue_job_runs_path(tmp_path, "my-job") if f.kind == "glue.job_run"
        ][0]

        blob = json.dumps(fact.to_dict())
        assert "bucket-secreto" not in blob
        assert fact.attrs["state"] == "FAILED"

    def test_unknown_worker_type_refuses_to_derive(self, tmp_path):
        _write_run(tmp_path, "jr_1", WorkerType="Z.9X")

        facts = extract_glue_job_runs_path(tmp_path, "my-job")
        run = [f for f in facts if f.kind == "glue.job_run"][0]

        assert "dpu_seconds" not in run.measures
        assert any(
            f.attrs["reason"] == "unknown_worker_type"
            for f in facts
            if f.kind == "glue.job_run.unresolved"
        )


class TestPercentileParity:
    def test_matches_the_sibling_extractors(self):
        from sparkforge.facts.event_log import _nearest_rank as event_log_rank
        from sparkforge.facts.glue_job_run import _nearest_rank as run_rank
        from sparkforge.facts.iceberg_metadata import _nearest_rank as iceberg_rank

        values = [1, 2, 3, 10, 20, 1000]
        for pct in (50, 95, 99, 100):
            assert run_rank(values, pct) == event_log_rank(values, pct) == iceberg_rank(values, pct)
