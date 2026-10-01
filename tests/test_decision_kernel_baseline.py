from pathlib import Path

from scripts.benchmark_decision_kernel import run_fixture


def test_baseline_has_complete_local_measurements():
    report = run_fixture(
        Path.cwd(), Path("evals/token_efficient/fixtures/decision_kernel_cases.yaml")
    )
    assert report["failed_cases"] == 0
    assert report["passed_cases"] == report["total_cases"]
    assert all(row["latency_ns"] >= 0 for row in report["cases"])
    assert all(row["payload_bytes"] >= 0 for row in report["cases"])
    assert all(row["provider_tokens"] is None for row in report["cases"])
    assert all(row["tokens_unresolved"] is True for row in report["cases"])
    assert report["cost_basis"] is None
