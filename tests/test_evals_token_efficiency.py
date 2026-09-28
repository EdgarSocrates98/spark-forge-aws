from __future__ import annotations

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_models import GatewayProfile
from sparkforge.evals.runner import EvaluationRunner
from sparkforge.evals.token_benchmark import load_benchmark_suite


def test_profile_benchmark_records_separate_token_state() -> None:
    results = EvaluationRunner().run_context_benchmark(
        ContextGateway(TOOLS),
        [{"id": "case-1", "intent": "Glue", "max_bytes": 6000}],
        baseline_id="test-baseline",
    )

    assert [item["profile"] for item in results] == ["economy", "balanced", "deep"]
    assert all(item["tokens_unresolved"] is True for item in results)
    assert all(item["provider_tokens"] is None for item in results)
    assert all(item["baseline_id"] == "test-baseline" for item in results)
    assert all(item["suite_id"] is None for item in results)
    assert all("quality" in item and "evidence_recall" in item for item in results)


def test_profile_benchmark_resolves_tokens_only_from_case_transcript_usage() -> None:
    results = EvaluationRunner().run_context_benchmark(
        ContextGateway(TOOLS),
        [
            {
                "id": "case-usage",
                "intent": "Glue",
                "max_bytes": 6000,
                "host_usage": {"input_tokens": 10, "output_tokens": 4},
            }
        ],
        profiles=(GatewayProfile.ECONOMY,),
    )

    assert results[0]["tokens_unresolved"] is False
    assert results[0]["provider_tokens"] == {"input_tokens": 10, "output_tokens": 4}


def test_profile_benchmark_preserves_answer_state_and_validates_plan() -> None:
    results = EvaluationRunner().run_context_benchmark(
        ContextGateway(TOOLS),
        [
            {
                "id": "case-planner",
                "intent": "production change review",
                "max_bytes": 6000,
                "answer_status": "partial",
                "answer_reasons": ["evidence incomplete"],
                "triggers": ["high_risk_change"],
                "expected_execution_plan": {
                    "economy": "unresolved",
                    "balanced": "unresolved",
                    "deep": "reviewer",
                },
            }
        ],
    )

    assert all(item["answer_state"]["status"] == "partial" for item in results)
    assert all(item["answer_state"]["reasons"] == ["evidence incomplete"] for item in results)
    assert all("high_risk_change" in item["answer_state"]["triggers"] for item in results)
    assert [item["execution_plan"]["kind"] for item in results] == [
        "unresolved",
        "unresolved",
        "reviewer",
    ]
    assert all(item["passed"] is True for item in results)


def test_benchmark_suite_uses_declared_fixture_and_reports_profile_contract() -> None:
    suite = load_benchmark_suite("evals/token_efficient")

    assert suite["schema_version"] == 1
    assert len(suite["cases"]) == 15
    assert suite["fixture_paths"] == (
        "fixtures/quality_cases.yaml",
        "fixtures/federated_graph_cases.yaml",
        "fixtures/provider_transcripts.yaml",
    )
    assert suite["quality_axes"] == (
        "status",
        "evidence_recall",
        "false_positive_rate",
        "unresolved",
        "execution_plan",
    )


def test_benchmark_suite_rejects_fixture_outside_root(tmp_path) -> None:
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "schema_version: 1\nid: test\nbaseline_id: local\n"
        "profiles: [economy]\nquality_axes: [status]\n"
        "quality_fixture: ../quality.yaml\ncases: []\n",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(ValueError, match="within benchmark directory"):
        load_benchmark_suite(tmp_path)
