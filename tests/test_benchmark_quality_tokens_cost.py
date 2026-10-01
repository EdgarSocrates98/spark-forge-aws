from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from sparkforge.evals.decision_replay import (
    MAX_INPUT_VOLUME_DELTA,
    compare_replay_benchmark,
    load_replay_suite,
    run_replay_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"


def _observation(case: dict, profile: str) -> dict:
    return {
        "status": case["expected_status"],
        "observed_evidence": list(case.get("expected_evidence", ())),
        "observed_findings": list(case.get("expected_findings", ())),
        "unresolved": list(case.get("expected_unresolved", ())),
        "execution_plan": f"{profile}-deterministic",
        "payload_bytes": 100 + len(profile),
        "provider_tokens": case.get("provider_tokens"),
        "tokens_unresolved": case.get("provider_tokens") is None,
        "transcript_hash": case.get("transcript_hash"),
        "cost": case.get("cost"),
        "cost_basis": case.get("cost_basis"),
    }


def _report() -> dict:
    suite = load_replay_suite(SUITE_PATH)
    return run_replay_benchmark(suite, old_runner=_observation, new_runner=_observation)


def test_benchmark_contract_has_labels_and_separate_evidence_axes() -> None:
    report = _report()

    assert report["benchmark_contract"] == {
        "labeled_tasks": 50,
        "minimum_labeled_tasks": 50,
        "same_case_required": True,
        "same_input_manifest_required": True,
        "max_input_volume_delta": MAX_INPUT_VOLUME_DELTA,
        "cost_requires_basis": True,
    }
    row = next(row for row in report["rows"] if row["case_id"] == "routing-03")
    assert row["label"] == "routing-03"
    assert row["payload_bytes"] == 107
    assert row["provider_tokens"] is None
    assert row["tokens_unresolved_reason"] == "provider_transcript_absent"
    assert row["cost"]["value"] is None
    assert row["cost_unresolved_reason"] == "cost_basis_absent"


def test_compare_refuses_changed_same_case_input_manifest() -> None:
    before = _report()
    after = deepcopy(before)
    after["rows"][0]["input_manifest"]["records"] += 1
    comparison = compare_replay_benchmark(before, after)

    assert comparison["refused"]["reason"] == "input_manifest_mismatch"
    assert comparison["cells"] == []


def test_compare_refuses_input_volume_delta_above_ten_percent() -> None:
    before = _report()
    after = deepcopy(before)
    after["rows"][0]["input_volume_bytes"] = 1111
    comparison = compare_replay_benchmark(before, after)

    assert comparison["refused"]["reason"] == "input_volume_mismatch"
    assert comparison["refused"]["max_delta"] == MAX_INPUT_VOLUME_DELTA
    assert comparison["cells"] == []


def test_route_accuracy_is_independent_and_missing_ground_truth_is_unresolved() -> None:
    suite = load_replay_suite(SUITE_PATH)
    case = dict(suite["cases"][0])
    case["expected_route"] = "local"
    case["input_manifest"] = dict(case["input_manifest"])
    case["input_manifest"]["bytes"] = 1000
    observation = _observation(case, "economy") | {"actual_route": "remote"}
    report = run_replay_benchmark(
        {**suite, "cases": (case,), "sha256": "route-test"},
        old_runner=lambda _case, _profile: observation,
        new_runner=lambda _case, _profile: observation,
    )
    row = report["rows"][0]
    assert row["route"] == {
        "expected": "local",
        "actual": "remote",
        "match": False,
        "reason": None,
    }
