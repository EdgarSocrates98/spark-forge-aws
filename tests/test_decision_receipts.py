from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.economy.decision_contracts import ContractRegistry
from sparkforge.economy.decision_models import DecisionInput, ProviderUsage
from sparkforge.economy.decision_plane import DecisionPlaneService
from sparkforge.economy.decision_receipts import DecisionReceiptError, DecisionReceiptStore

ROOT = Path(__file__).resolve().parents[1]


def test_transcript_tokens_keep_provenance(tmp_path: Path) -> None:
    service = DecisionPlaneService(
        ROOT, registry=ContractRegistry(ROOT), receipts=DecisionReceiptStore(tmp_path)
    )
    contract = service.validate("routing.data_domain")
    request = DecisionInput(
        "task",
        "diagnose",
        payload_bytes=900,
        provider_usage=ProviderUsage(3, 2, "transcript-sha"),
    )

    evaluation = service.shadow(request, "tier_3_cheap_local", contract=contract, now="fixed")
    document = evaluation.receipt.to_dict()

    assert document["token_state"]["provider_tokens"]["total_tokens"] == 5
    assert document["token_state"]["transcript_sha256"] == "transcript-sha"
    assert document["input"]["payload_bytes"] == 900
    assert document["token_state"]["transcript_sha256"] == "transcript-sha"
    assert document["kernel"]["fingerprint"]
    assert DecisionReceiptStore(tmp_path).verify(evaluation.receipt.path)["valid"] is True


def test_missing_transcript_is_tokens_unresolved(tmp_path: Path) -> None:
    service = DecisionPlaneService(
        ROOT, registry=ContractRegistry(ROOT), receipts=DecisionReceiptStore(tmp_path)
    )
    contract = service.validate("routing.data_domain")
    request = DecisionInput("task", "diagnose", payload_bytes=900)

    evaluation = service.shadow(request, "tier_3_cheap_local", contract=contract, now="fixed")

    assert evaluation.receipt.document["token_state"]["tokens_unresolved"] is True
    assert evaluation.receipt.document["input"]["payload_bytes"] == 900
    assert evaluation.receipt.document["kernel"]["cache_hit"] is False


def test_receipt_path_escape_and_tampering_fail_closed(tmp_path: Path) -> None:
    store = DecisionReceiptStore(tmp_path)
    with pytest.raises(DecisionReceiptError, match="path_escape"):
        store.verify(tmp_path / "outside.json")

    service = DecisionPlaneService(
        ROOT, registry=ContractRegistry(ROOT), receipts=DecisionReceiptStore(tmp_path)
    )
    contract = service.validate("routing.data_domain")
    receipt = service.shadow(
        DecisionInput("task", "diagnose"), "tier_3_cheap_local", contract=contract, now="fixed"
    ).receipt
    payload = json.loads(receipt.path.read_text(encoding="utf-8"))
    payload["comparison"]["state"] = "disagreement"
    receipt.path.write_text(json.dumps(payload), encoding="utf-8")

    assert store.verify(receipt.path)["valid"] is False
