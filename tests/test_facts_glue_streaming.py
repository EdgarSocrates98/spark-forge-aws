from pathlib import Path

from sparkforge.facts.glue_streaming import extract_glue_streaming_path


FIXTURES = Path(__file__).parents[1] / "fixtures" / "glue_streaming"


def test_rtm_dump_emits_observed_constraints_and_capacity():
    facts = extract_glue_streaming_path(FIXTURES / "rtm_valid" / "input" / "job.json")
    job = next(f for f in facts if f.kind == "glue.streaming.job")
    assert job.attrs["mode"] == "REAL_TIME"
    assert job.attrs["language"] == "SCALA"
    assert job.attrs["source_type"] == "KAFKA"
    assert job.measures["partition_count"] == 4
    assert job.measures["task_slots"] == 4
    assert not any(f.kind == "glue.streaming.unresolved" for f in facts)


def test_rtm_missing_capacity_is_unresolved_not_zero():
    facts = extract_glue_streaming_path(FIXTURES / "rtm_missing_capacity" / "input" / "job.json")
    unresolved = [f for f in facts if f.kind == "glue.streaming.unresolved"]
    assert any(f.attrs["reason"] == "partition_capacity" for f in unresolved)
    job = next(f for f in facts if f.kind == "glue.streaming.job")
    assert "partition_count" not in job.measures
    assert "task_slots" not in job.measures
