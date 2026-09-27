from __future__ import annotations

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.context.gateway_models import GatewayProfile
from sparkforge.evals.runner import EvaluationRunner


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
