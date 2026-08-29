"""Testes do extrator de historico de runs Glue em Facts."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.glue_job_run import EMITTED_KINDS, extract_glue_job_runs_path
from sparkforge.findings.validate import validate_fact


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


class TestDistribution:
    def test_groups_by_capacity_and_terminal_state(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)
        _write_run(tmp_path, "jr_2", ExecutionTime=300)
        _write_run(tmp_path, "jr_3", ExecutionTime=999, JobRunState="FAILED")
        _write_run(tmp_path, "jr_4", ExecutionTime=200, NumberOfWorkers=20)

        dists = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ]

        keys = {(f.subject["number_of_workers"], f.subject["state"]) for f in dists}
        assert keys == {(10, "SUCCEEDED"), (10, "FAILED"), (20, "SUCCEEDED")}

        ten_ok = [
            f
            for f in dists
            if f.subject["number_of_workers"] == 10 and f.subject["state"] == "SUCCEEDED"
        ][0]
        assert ten_ok.measures["n"] == 2
        assert ten_ok.measures["runtime_min_s"] == 100
        assert ten_ok.measures["runtime_max_s"] == 300
        assert ten_ok.measures["runtime_p50_s"] == 100

    def test_single_run_group_declares_n_of_one(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.measures["n"] == 1
        assert dist.measures["runtime_p95_s"] == 100

    def test_mixed_dpu_source_is_marked_not_merged(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)
        _write_run(tmp_path, "jr_2", ExecutionTime=200, DPUSeconds=50.0)

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.attrs["dpu_source"] == "mixed"

    def test_window_bounds_come_from_the_runs(self, tmp_path):
        _write_run(tmp_path, "jr_1", StartedOn="2026-08-01T10:00:00+00:00")
        _write_run(tmp_path, "jr_2", StartedOn="2026-08-09T10:00:00+00:00")

        dist = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.distribution"
        ][0]

        assert dist.attrs["window_first"] == "2026-08-01T10:00:00+00:00"
        assert dist.attrs["window_last"] == "2026-08-09T10:00:00+00:00"


class TestOutcome:
    def test_counts_states_within_one_capacity(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2")
        _write_run(tmp_path, "jr_3", JobRunState="FAILED")
        _write_run(tmp_path, "jr_4", JobRunState="TIMEOUT")

        outcomes = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.outcome"
        ]

        assert len(outcomes) == 1
        assert outcomes[0].measures == {
            "n_total": 4,
            "n_succeeded": 2,
            "n_failed": 1,
            "n_timeout": 1,
            "n_stopped": 0,
        }

    def test_outcome_carries_counts_not_a_rate(self, tmp_path):
        _write_run(tmp_path, "jr_1")
        _write_run(tmp_path, "jr_2", JobRunState="FAILED")

        outcome = [
            f
            for f in extract_glue_job_runs_path(tmp_path, "my-job")
            if f.kind == "glue.job_run.outcome"
        ][0]

        assert not any("rate" in k or "ratio" in k for k in outcome.measures)


def _write_cloudwatch(root: Path, run_id: str, value: float) -> Path:
    payload = {
        "job_name": "my-job",
        "job_run_id": run_id,
        "start": "2026-08-01T10:00:00Z",
        "end": "2026-08-01T10:20:00Z",
        "period_seconds": 60,
        "metric_data_results": [
            {
                "Id": "m0",
                "Label": "glue.driver.workerUtilization",
                "Timestamps": ["t1"],
                "Values": [value],
            }
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"my-job_{run_id}.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestSchemaValidation:
    """O gate que faltava: nenhum dos cinco kinds deste modulo emitia
    `subject.type`, e `sparkforge.findings.validate.validate_fact` reprovava
    com "'type' is a required property" em `subject`. `tests/test_fixtures_
    golden_s3.py::TestGolden::test_everything_validates_against_schema` ja
    cobre este gate para os extratores irmaos; este modulo golden nao existia
    ainda quando o defeito entrou."""

    def test_all_emitted_kinds_validate_against_the_fact_schema(self, tmp_path):
        _write_run(tmp_path, "jr_1", ExecutionTime=100)
        _write_run(tmp_path, "jr_2", ExecutionTime=200, JobRunState="FAILED")

        facts = extract_glue_job_runs_path(tmp_path, "my-job")

        assert EMITTED_KINDS == {f.kind for f in facts}
        for fact in facts:
            validate_fact(fact.to_dict())


class TestCorrelation:
    def test_metric_facts_are_emitted_for_runs_with_artifacts(self, tmp_path):
        runs_dir = tmp_path / "runs"
        cw_dir = tmp_path / "cw"
        _write_run(runs_dir, "jr_1")
        _write_cloudwatch(cw_dir, "jr_1", 0.42)

        facts = extract_glue_job_runs_path(runs_dir, "my-job", cloudwatch_dir=cw_dir)
        metrics = [f for f in facts if f.kind == "glue.metric"]

        assert len(metrics) == 1
        assert metrics[0].subject["job_run_id"] == "jr_1"
        assert metrics[0].measures["p50"] == 0.42

    def test_run_without_metrics_names_the_command_that_fixes_it(self, tmp_path):
        runs_dir = tmp_path / "runs"
        cw_dir = tmp_path / "cw"
        cw_dir.mkdir(parents=True)
        _write_run(runs_dir, "jr_1")

        facts = extract_glue_job_runs_path(runs_dir, "my-job", cloudwatch_dir=cw_dir)
        missing = [
            f
            for f in facts
            if f.kind == "glue.job_run.unresolved"
            and f.attrs["reason"] == "cloudwatch_artifact_missing"
        ]

        assert len(missing) == 1
        assert "sparkforge collect cloudwatch" in missing[0].attrs["collect_command"]
        assert "--job-run jr_1" in missing[0].attrs["collect_command"]

    def test_without_the_directory_correlation_is_declared_not_silent(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "jr_1")

        facts = extract_glue_job_runs_path(runs_dir, "my-job")
        assert not [f for f in facts if f.kind == "glue.metric"]
        assert any(
            f.attrs["reason"] == "cloudwatch_not_requested"
            for f in facts
            if f.kind == "glue.job_run.unresolved"
        )
