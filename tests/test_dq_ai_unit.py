import json

from sparkforge.dq_ai.assessment import build_assessment_facts
from sparkforge.facts.glue_dq_advanced import (
    RowPayloadRejected,
    extract_glue_dq_advanced,
    extract_glue_dq_advanced_path,
)


def test_advanced_emits_metadata_only_governance_attributes():
    facts = extract_glue_dq_advanced(
        {
            "table_name": "orders",
            "recommendation_mode": "ADVANCED",
            "classification": "restricted",
            "source_region": "us-east-1",
            "inference_region": "eu-west-1",
            "kms": {"status": "missing"},
            "arguments": {"Timeout": 60},
        },
        "recommendation.json",
    )
    recommendation = next(f for f in facts if f.kind == "dq.ai.recommendation")
    assert recommendation.attrs["payload_scope"] == "metadata_only"
    assert recommendation.attrs["incompatible_args"] == ["Timeout"]
    assessment = build_assessment_facts(facts, {"glue": "5.1"})[0]
    assert assessment.attrs["sensitive_exposure"] is True
    assert assessment.attrs["cross_region"] is True
    assert assessment.attrs["kms_insufficient"] is True


def test_row_payload_is_rejected_without_becoming_a_fact(tmp_path):
    path = tmp_path / "rows.json"
    path.write_text(
        json.dumps({"recommendation_mode": "ADVANCED", "rows": [{"email": "x"}]}),
        encoding="utf-8",
    )
    facts = extract_glue_dq_advanced_path(path)
    assert [fact.kind for fact in facts] == ["dq.ai.recommendation.unresolved"]
    assert facts[0].attrs["reason"] == "row_payload_rejected"


def test_direct_extractor_rejects_non_mapping_payload():
    try:
        extract_glue_dq_advanced([], "recommendation.json")
    except ValueError as exc:
        assert "objeto" in str(exc)
    else:
        raise AssertionError("payload de lista deveria ser recusado")
