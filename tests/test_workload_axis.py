"""Testes do contrato do eixo do fingerprint."""
from __future__ import annotations

import pytest

from sparkforge.workload.axis import Axis, unknown_axis


class TestContrato:
    def test_measured_axis_carries_basis_and_evidence(self):
        eixo = Axis(
            value="extreme", confidence="measured", basis="history_p99", evidence=("a1",)
        )

        assert eixo.value == "extreme"
        assert eixo.confidence == "measured"
        assert eixo.to_dict()["basis"] == "history_p99"

    def test_measured_without_evidence_is_refused(self):
        with pytest.raises(ValueError, match="evidence"):
            Axis(value="high", confidence="measured", basis="history_p95", evidence=())

    def test_measured_without_basis_is_refused(self):
        with pytest.raises(ValueError, match="basis"):
            Axis(value="high", confidence="measured", basis="", evidence=("a1",))

    def test_unknown_axis_carries_what_is_missing(self):
        eixo = unknown_axis("glue.job_run.distribution", "sparkforge collect glue-job-runs ...")

        assert eixo.value == "unknown"
        assert eixo.confidence == "unknown"
        assert eixo.to_dict()["missing"] == "glue.job_run.distribution"
        assert "collect glue-job-runs" in eixo.to_dict()["collect_command"]

    def test_a_value_other_than_unknown_cannot_have_unknown_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            Axis(value="high", confidence="unknown", basis="", evidence=())

    def test_unknown_value_never_carries_evidence(self):
        with pytest.raises(ValueError, match="unknown"):
            Axis(value="unknown", confidence="unknown", basis="", evidence=("a1",))

    def test_declared_axis_never_claims_to_be_measured(self):
        eixo = Axis(
            value="critical", confidence="declared", basis="declared", evidence=("d1",)
        )

        assert eixo.confidence == "declared"
        assert eixo.to_dict()["confidence"] != "measured"

    def test_unknown_value_is_refused_by_the_enum(self):
        with pytest.raises(ValueError, match="valor"):
            Axis(value="gigantesco", confidence="measured", basis="x", evidence=("a1",))
