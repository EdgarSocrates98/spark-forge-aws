from __future__ import annotations

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.evals.runner import EvaluationRunner


def test_quality_metrics_record_evidence_recall_and_unresolved_codes() -> None:
    results = EvaluationRunner().run_context_benchmark(
        ContextGateway(TOOLS),
        [
            {
                "id": "quality",
                "intent": "Iceberg quality",
                "max_bytes": 6000,
                "items": [{"fact_id": "f-quality", "kind": "fact", "value": "observed"}],
                "expected_status": "ok",
                "expected_evidence": ["f-quality"],
            }
        ],
    )

    assert all(result["evidence_recall"] == 1.0 for result in results)
    assert all(result["false_positive_rate"] == 0.0 for result in results)
    assert all(result["passed"] is True for result in results)
