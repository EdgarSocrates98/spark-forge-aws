from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.fusion import fuse
from sparkforge.facts.glue_streaming import extract_glue_streaming_path
from sparkforge.facts.streaming_glue_runtime import (
    EMITTED_KINDS,
    build_streaming_glue_runtime_observation,
)
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_glue_runtime_observation"


def _fact(kind: str, *, attrs=None, measures=None, subject=None, file="artifact.json", symbol="", line=1):
    return Fact(
        kind=kind,
        subject=subject
        or {
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "symbol": symbol,
            "snippet": "",
        },
        attrs=attrs or {},
        measures=measures or {},
        provenance={
            "artifact": file,
            "artifact_sha256": "a" * 64,
            "extractor": "test@0.1.0",
        },
    )


def _effective(name="orders-stream", *, version="6.0", workers=4, worker_type="G.1X"):
    attrs = {"name": name, "mode": "REAL_TIME", "glue_version": version}
    if worker_type is not None:
        attrs["worker_type"] = worker_type
    measures = {}
    if workers is not None:
        measures["worker_count"] = workers
    return _fact("glue.streaming.job", attrs=attrs, measures=measures, file="effective.json", symbol=name)


def _run(
    run_id="jr-1",
    job_name="orders-stream",
    *,
    version="6.0",
    workers=4,
    worker_type="G.1X",
    state="SUCCEEDED",
):
    attrs = {"state": state, "started_on": "2026-10-02T00:00:00Z", "completed_on": "2026-10-02T00:01:00Z"}
    if version is not None:
        attrs["glue_version"] = version
    if worker_type is not None:
        attrs["worker_type"] = worker_type
    measures = {"execution_time_s": 60}
    if workers is not None:
        measures["number_of_workers"] = workers
    return _fact(
        "glue.job_run",
        attrs=attrs,
        measures=measures,
        subject={"job_name": job_name, "job_run_id": run_id, "type": "job_run", "symbol": run_id},
        file=f"{run_id}.json",
        symbol=run_id,
    )


def _link(facts):
    return [fact for fact in build_streaming_glue_runtime_observation(facts) if fact.kind == "glue.streaming.runtime_link"]


def test_effective_glue_fact_preserves_runtime_capacity_fields(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "job": {
                    "name": "orders-stream",
                    "glue_version": "6.0",
                    "WorkerType": "G.1X",
                    "NumberOfWorkers": 4,
                    "default_arguments": {"--enable-real-time-mode": "true"},
                    "stream": {"source_type": "kafka"},
                }
            }
        ),
        encoding="utf-8",
    )
    facts = extract_glue_streaming_path(path)
    job = next(fact for fact in facts if fact.kind == "glue.streaming.job")
    assert job.attrs["worker_type"] == "G.1X"
    assert job.measures["worker_count"] == 4


def test_runtime_link_matches_literal_job_and_preserves_sources():
    link = _link([_effective(), _run()])[0]
    assert link.attrs["comparison_status"] == "consistent"
    assert link.attrs["job_name"] == "orders-stream"
    assert link.attrs["observed_states"] == ["SUCCEEDED"]
    assert link.attrs["observed_glue_versions"] == ["6.0"]
    assert link.attrs["observed_worker_types"] == ["G.1X"]
    assert link.measures["run_count"] == 1
    assert link.measures["comparison_count"] == 3
    assert link.measures["divergence_count"] == 0
    assert len(link.attrs["source_fact_ids"]) == 2
    validate_fact(link.to_dict())


def test_runtime_link_reports_drift_and_unresolved_without_inference():
    drift = _link([_effective(), _run(version="5.0", workers=2, worker_type="G.2X")])[0]
    assert drift.attrs["comparison_status"] == "divergent"
    assert set(drift.attrs["drifts"]) == {"glue_version", "worker_type", "worker_count"}
    assert drift.measures["divergence_count"] == 3

    missing = _link([_effective(), _run(version=None, workers=None, worker_type=None)])[0]
    assert missing.attrs["comparison_status"] == "unresolved"
    assert set(missing.attrs["unresolved_fields"]) == {"glue_version", "worker_type", "worker_count"}
    assert missing.measures["unresolved_count"] == 3

    no_run = build_streaming_glue_runtime_observation([_effective()])
    assert {fact.kind for fact in no_run} == {"glue.streaming.runtime.unresolved"}
    assert no_run[0].attrs["reason"] == "run_observation_missing"


def test_runtime_observation_rules_are_evidence_backed():
    drift = fuse([_effective(), _run(version="5.0", workers=2, worker_type="G.2X")])
    findings = judge(drift, load_catalog(), {})
    assert "SF-GLUESTREAM-006" in {finding.rule_id for finding in findings}
    assert all(finding.evidence for finding in findings)

    unresolved = fuse([_effective(), _run(version=None, workers=None, worker_type=None)])
    findings = judge(unresolved, load_catalog(), {})
    assert "SF-GLUESTREAM-007" in {finding.rule_id for finding in findings}
    assert all(finding.evidence for finding in findings)


def test_fuse_runtime_observation_is_guarded_and_idempotent():
    base = [_fact("streaming.query", attrs={"query_name": "orders"})]
    assert not [fact for fact in fuse(base) if fact.kind in EMITTED_KINDS]

    once = fuse([_effective(), _run()])
    twice = fuse(once)
    as_dicts = lambda facts: sorted((fact.to_dict() for fact in facts), key=lambda item: item["id"])
    assert as_dicts(once) == as_dicts(twice)


def _run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    inputs: list[Fact] = []
    for path in sorted((directory / "input").iterdir()):
        inputs.extend(
            Fact(
                kind=item["kind"],
                subject=item["subject"],
                measures=item.get("measures") or {},
                attrs=item.get("attrs") or {},
                provenance=item.get("provenance") or {},
                schema_version=item.get("schema_version", 1),
            )
            for item in json.loads(path.read_text(encoding="utf-8"))
        )
    facts = sort_facts(fuse(inputs))
    findings = judge(facts, load_catalog(), {})
    return meta, facts, findings


def test_fixture_goldens_cover_consistent_drift_and_unresolved():
    required = {"consistent", "drift", "unresolved"}
    assert {path.name for path in FIXTURES.iterdir() if path.is_dir()} == required
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta, facts, findings = _run_fixture(directory)
        expected_facts = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        expected_findings = json.loads((directory / "expected" / "findings.json").read_text(encoding="utf-8"))
        assert [fact.to_dict() for fact in facts] == expected_facts
        assert [finding.to_dict() for finding in findings] == expected_findings
        assert {fact.kind for fact in facts} == set(meta["expects_kinds"])
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", sorted(FIXTURES.glob("*/")), ids=lambda path: path.name)
def test_fixture_extraction_is_deterministic(directory: Path):
    first = _run_fixture(directory)[1]
    second = _run_fixture(directory)[1]
    assert [fact.to_dict() for fact in first] == [fact.to_dict() for fact in second]
