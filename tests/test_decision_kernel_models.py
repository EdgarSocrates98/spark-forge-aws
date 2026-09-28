import pytest

from sparkforge.decision.models import (
    DecisionResult,
    DecisionStatus,
    LocalMeasurement,
)


def _result(status=DecisionStatus.ACCEPTED, selected=("route",)):
    return DecisionResult("contract", "1", "sha", "fp", status, selected, "test", 1.0, None)


def test_accepted_requires_selection():
    with pytest.raises(ValueError, match="accepted result"):
        _result(selected=())


def test_non_accepted_cannot_select():
    with pytest.raises(ValueError, match="non-accepted"):
        _result(DecisionStatus.ABSTAIN)


def test_measurement_keeps_provider_tokens_explicit():
    measurement = LocalMeasurement(10, 20)
    assert measurement.to_dict() == {
        "latency_ns": 10,
        "payload_bytes": 20,
        "provider_tokens": None,
        "tokens_unresolved": True,
        "cost_basis": None,
    }
    with pytest.raises(ValueError, match="cannot be unresolved"):
        LocalMeasurement(1, 1, {"input": 1})
