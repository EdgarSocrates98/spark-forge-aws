from __future__ import annotations

import pytest

from sparkforge_aws.context.gateway_budget import (
    BudgetRefusal,
    materialize_bounded,
    pack_payload,
    serialized_bytes,
)


def test_budget_reduction_keeps_critical_fields() -> None:
    packed = pack_payload(
        {
            "schema_version": 1,
            "description": "x" * 5000,
            "context": [
                {"kind": "fact", "fact_id": "f1", "evidence": "observed", "critical": True},
                {"kind": "knowledge", "content": "noise" * 500},
            ],
            "rule_id": "SF-TEST-001",
        },
        500,
    )

    assert packed.payload["rule_id"] == "SF-TEST-001"
    assert packed.payload["context"][0]["fact_id"] == "f1"
    assert packed.reductions
    assert packed.payload_bytes <= 500


def test_budget_refuses_when_critical_content_cannot_fit() -> None:
    with pytest.raises(BudgetRefusal, match="critical gateway content"):
        pack_payload({"fact_id": "f1", "evidence": "x" * 1000}, 5)


def test_materialization_rechecks_derived_metadata_until_final_size_fits() -> None:
    def rebuild(payload):
        payload["derived"] = "metadata" * 20

    result = materialize_bounded({"context": [], "budget": {}}, 500, rebuild)

    assert serialized_bytes(result) <= 500
