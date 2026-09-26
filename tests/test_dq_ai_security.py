import json

from sparkforge.adapters import _core
from sparkforge.facts.glue_dq_advanced import extract_glue_dq_advanced_path


def test_assessment_never_calls_provider_or_carries_rows(tmp_path):
    recommendation = tmp_path / "recommendation.json"
    recommendation.write_text(
        json.dumps(
            {
                "table_name": "orders",
                "recommendation_mode": "ADVANCED",
                "classification": "sensitive",
                "source_region": "us-east-1",
                "inference_region": "us-east-1",
                "kms": {"status": "sufficient"},
            }
        ),
        encoding="utf-8",
    )
    facts = [fact.to_dict() for fact in extract_glue_dq_advanced_path(recommendation)]
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(facts), encoding="utf-8")
    report = _core.dq_ai_assess([str(facts_path)], glue="6.0")
    assert report["metrics"]["provider_calls"] == 0
    assert report["metrics"]["row_payloads"] == 0
    assert all("rows" not in fact for fact in report["facts"])
