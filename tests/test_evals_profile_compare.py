from __future__ import annotations

from sparkforge.evals.compare import compare_profile_benchmarks


def test_profile_compare_lists_transitions_without_claiming_improvement() -> None:
    result = compare_profile_benchmarks(
        [{"case_id": "a", "profile": "economy", "status": "ok", "payload_bytes": 10}],
        [{"case_id": "a", "profile": "economy", "status": "ok", "payload_bytes": 8}],
    )

    assert result["refused"] is None
    assert result["unit_separation"] is True
    assert result["rows"][0]["changed"] is True
    assert "improved" not in result


def test_profile_compare_refuses_different_case_matrix() -> None:
    result = compare_profile_benchmarks(
        [{"case_id": "a", "profile": "economy"}],
        [{"case_id": "b", "profile": "economy"}],
    )

    assert result["refused"]["reason"] == "benchmark_case_profile_mismatch"
