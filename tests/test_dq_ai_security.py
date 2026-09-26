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


def test_authorization_requires_all_external_evidence_parts(tmp_path):
    recommendation = tmp_path / "recommendation.json"
    recommendation.write_text(
        json.dumps(
            {
                "table_name": "payments",
                "recommendation_mode": "ADVANCED",
                "source_region": "us-east-1",
                "inference_region": "us-east-1",
                "kms": {"status": "sufficient"},
                "authorization": {
                    "key_policy_status": "declared",
                    "runtime_role_status": "insufficient",
                    "lakeformation_status": "unresolved",
                },
            }
        ),
        encoding="utf-8",
    )
    facts = [fact.to_dict() for fact in extract_glue_dq_advanced_path(recommendation)]
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    report = _core.dq_ai_assess([str(facts_path)], glue="5.1")
    assessment = next(f for f in report["facts"] if f["kind"] == "dq.ai.assessment")

    assert assessment["attrs"]["authorization_evidence_status"] == "insufficient"
    assert assessment["attrs"]["key_policy_status"] == "declared"
    assert assessment["attrs"]["runtime_role_status"] == "insufficient"
    assert assessment["attrs"]["lakeformation_status"] == "unresolved"
    assert "SF-DQ-AI-008" in {finding["rule_id"] for finding in report["findings"]}
    assert report["metrics"]["provider_calls"] == 0
