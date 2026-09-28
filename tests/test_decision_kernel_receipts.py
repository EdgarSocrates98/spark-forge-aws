from copy import deepcopy

import pytest

from sparkforge.decision import BoundedDecisionKernel, ContractLoader
from sparkforge.decision.receipts import ReceiptValidationError, verify_receipt


def test_receipt_round_trip_and_tamper_detection():
    contract = ContractLoader().load("kernel.synthetic")
    evaluation = BoundedDecisionKernel().evaluate(
        contract, {"signal": "safe"}, now="2026-09-28T00:00:00Z"
    )
    assert verify_receipt(evaluation.receipt)["valid"] is True
    tampered = deepcopy(evaluation.receipt)
    tampered["result"]["selected"] = ["other"]
    assert verify_receipt(tampered)["valid"] is False
    missing = deepcopy(evaluation.receipt)
    del missing["evidence"]
    with pytest.raises(ReceiptValidationError, match="receipt_missing_fields"):
        verify_receipt(missing)
