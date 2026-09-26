from sparkforge.dq_ai.assessment import build_assessment_facts
from sparkforge.facts.glue_dq_advanced import extract_glue_dq_advanced
from sparkforge.reporting.dq_ai import build_dq_ai_report


def test_report_has_exactly_three_views_and_zero_provider_calls():
    facts = extract_glue_dq_advanced(
        {
            "table_name": "orders",
            "recommendation_mode": "ADVANCED",
            "source_region": "us-east-1",
            "inference_region": "us-east-1",
            "kms": {"status": "sufficient"},
            "human_review_status": "declared",
        },
        "recommendation.json",
    )
    facts += build_assessment_facts(facts, {"glue": "5.1"})
    report = build_dq_ai_report(facts, [], {"glue": "5.1"})
    assert set(report["views"]) == {"maintainer", "operator", "security_compliance"}
    assert report["metrics"]["provider_calls"] == 0
    assert report["metrics"]["row_payloads"] == 0


def test_single_view_does_not_duplicate_projection():
    report = build_dq_ai_report([], [], {}, view="operator")
    assert list(report["views"]) == ["operator"]


def test_report_exposes_documented_claims_and_risk_context():
    facts = extract_glue_dq_advanced(
        {
            "table_name": "orders",
            "recommendation_mode": "ADVANCED",
            "classification": "restricted",
            "source_region": "us-east-1",
            "inference_region": "us-east-1",
            "kms": {"status": "sufficient"},
            "risk": {"residency_required": True},
            "iceberg": {"format_version": "2", "operation": "read_write"},
            "migration": {"risk": "medium", "path": "5.1_to_6.0"},
            "human_review_status": "declared",
        },
        "recommendation.json",
    )
    facts += build_assessment_facts(facts, {"glue": "5.1"})
    report = build_dq_ai_report(facts, [], {"glue": "5.1"})
    exposure = report["views"]["security_compliance"]["exposure"][0]

    assert (
        exposure["provider_data_protection_claims"]["inputs_outputs_retained"]["status"]
        == "documented_claim"
    )
    assert exposure["risk_context"]["residency_required"] is True
    assert exposure["risk_context"]["iceberg"]["format_version"] == "2"
    assert exposure["risk_context"]["migration"]["risk"] == "medium"
    assert exposure["recommendation_variability"] == "possible"
    assert "variance_score" not in exposure
