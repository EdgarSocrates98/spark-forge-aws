from __future__ import annotations

from pathlib import Path

from sparkforge.evals.decision_plane import DecisionEvaluationRunner

ROOT = Path(__file__).resolve().parents[1]


def test_seed_suite_matches_ground_truth() -> None:
    report = DecisionEvaluationRunner(ROOT).run(
        "evals/token_efficient/fixtures/decision_plane_cases.yaml"
    )

    assert report["total_cases"] == 23
    assert report["passed_cases"] == 23
    assert report["source_counts"] == {
        "federated_graph": 6,
        "provider_transcript": 2,
        "quality": 15,
    }
    assert report["seed_passed"] is True
    assert report["activation_ready"] is False
