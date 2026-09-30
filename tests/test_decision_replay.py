from __future__ import annotations

from pathlib import Path

from sparkforge.evals.decision_replay import (
    PROFILES,
    compare_replay_benchmark,
    load_replay_suite,
    run_replay_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]


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


def test_benchmark_has_50_labeled_cases_six_domains_three_profiles_and_two_runners() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    report = run_replay_benchmark(
        suite,
        old_runner=_observation,
        new_runner=_observation,
    )
    assert len(suite["cases"]) == 50
    assert suite["labeled_tasks"] == 50
    assert len({case["domain"] for case in suite["cases"]}) == 10
    assert len(report["rows"]) == 50 * len(PROFILES) * 2
    assert set(report["summary"]) == {
        f"{runner}:{profile}"
        for runner in ("old", "new")
        for profile in PROFILES
    }
    assert set(report["rows"][0]["quality"]) == {
        "status",
        "evidence_recall",
        "false_positive_rate",
        "unresolved",
        "execution_plan",
    }
    assert report["candidates"]["baseline"]["candidate_id"] == "baseline"
    assert report["candidates"]["candidate"]["candidate_id"] == "candidate"


def test_benchmark_cost_without_basis_is_unresolved_not_zero() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    report = run_replay_benchmark(suite, old_runner=_observation, new_runner=_observation)
    row = next(row for row in report["rows"] if row["case_id"] == "routing-03")
    assert row["cost"]["status"] == "unresolved"
    assert row["cost"]["value"] is None
    assert report["summary"]["old:economy"]["cost"]["denominator"] < 30


def test_compare_refuses_mismatched_suite() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    report = run_replay_benchmark(suite, old_runner=_observation, new_runner=_observation)
    changed = dict(report)
    changed["suite"] = {**report["suite"], "sha256": "different"}
    comparison = compare_replay_benchmark(report, changed)
    assert comparison["refused"]["reason"] == "suite_mismatch"


def test_replay_rows_keep_provider_tokens_separate_from_payload_bytes() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    report = run_replay_benchmark(suite, old_runner=_observation, new_runner=_observation)
    row = next(row for row in report["rows"] if row["case_id"] == "routing-03")

    assert row["payload_bytes"] >= 100
    assert row["provider_tokens"] is None
    assert row["cost"]["status"] == "unresolved"
