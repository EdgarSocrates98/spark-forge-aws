from __future__ import annotations

from pathlib import Path

from sparkforge.evals.decision_replay import (
    compare_replay_benchmark,
    load_replay_suite,
    run_replay_benchmark,
    split_replay_benchmark,
)
from sparkforge.evals.evolution import EvolutionService

ROOT = Path(__file__).resolve().parents[1]


def _runner(case: dict, profile: str) -> dict:
    return {
        "status": case["expected_status"],
        "actual_route": case.get("expected_route"),
        "observed_evidence": case.get("expected_evidence", ()),
        "observed_findings": case.get("expected_findings", ()),
        "execution_plan": profile,
        "payload_bytes": case["input_manifest"]["bytes"],
        "tokens_unresolved": True,
    }


def test_replay_keeps_candidate_identity_and_separate_metrics() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    report = run_replay_benchmark(
        suite,
        old_runner=_runner,
        new_runner=_runner,
        baseline_identity={"candidate_id": "baseline", "candidate_sha256": "base"},
        candidate_identity={"candidate_id": "variant", "candidate_sha256": "cand"},
    )
    row = next(row for row in report["rows"] if row["runner"] == "new")
    assert row["candidate"]["candidate_sha256"] == "cand"
    comparison = compare_replay_benchmark(report, report)
    assert comparison["candidates"]["candidate"]["candidate_id"] == "variant"
    assert "payload_bytes" in comparison["cells"][0]
    assert "provider_tokens" in comparison["cells"][0]


def test_service_evaluate_uses_repository_fixture_without_provider(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    import shutil

    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    evaluation = EvolutionService(repo).evaluate(
        EvolutionService(repo).registry.get("routing-variant")
    )
    assert evaluation.labeled_tasks == 50
    assert evaluation.comparison["cells"]


def test_paired_report_splits_into_distinct_baseline_and_candidate_reports() -> None:
    suite = load_replay_suite(
        ROOT / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml"
    )
    calls = {"old": 0, "new": 0}

    def old_runner(case: dict, profile: str) -> dict:
        calls["old"] += 1
        return _runner(case, profile)

    def new_runner(case: dict, profile: str) -> dict:
        calls["new"] += 1
        return _runner(case, profile)

    paired = run_replay_benchmark(
        suite,
        old_runner=old_runner,
        new_runner=new_runner,
        baseline_identity={"candidate_digest": "baseline"},
        candidate_identity={"candidate_digest": "candidate"},
    )
    baseline, candidate = split_replay_benchmark(paired)
    assert calls == {"old": 50 * 3, "new": 50 * 3}
    assert baseline["candidates"]["candidate"]["candidate_digest"] == "baseline"
    assert candidate["candidates"]["candidate"]["candidate_digest"] == "candidate"
    comparison = compare_replay_benchmark(baseline, candidate)
    assert comparison["cells"]
