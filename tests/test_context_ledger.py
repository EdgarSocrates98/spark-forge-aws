"""Testes do span de contexto: o que o SparkForge poe na janela.

Span de tool tem BYTE. Token de provider e do host, e custo em dolar exige uma
fonte de preco -- os dois ficam vazios aqui, e vazio significa "nao se aplica",
nao "deu zero".
"""
from __future__ import annotations

import pytest

from sparkforge.observability.tracer import AgentOpsTracker, TraceSpan


class TestOsCamposNovos:
    def test_a_tool_span_carries_bytes_and_the_formula(self):
        span = TraceSpan(
            span_id="span_1",
            run_id="run_1",
            parent_span_id=None,
            name="sparkforge_analyze_pyspark",
            component_type="tool",
            start_time=0.0,
            payload_bytes=1234,
            payload_basis='len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))',
        )

        assert span.payload_bytes == 1234
        assert "json.dumps" in span.payload_basis
        assert span.to_dict()["payload_bytes"] == 1234

    def test_the_new_fields_default_to_absent_not_zero(self):
        """`detail_level` e `item_count` vazios dizem "a tool nao declarou",
        e nao "veio vazio"."""
        span = TraceSpan(
            span_id="span_1",
            run_id="run_1",
            parent_span_id=None,
            name="sparkforge_case_get",
            component_type="tool",
            start_time=0.0,
        )

        assert span.detail_level == ""
        assert span.item_count is None
        assert span.outcome == "ok"


class TestCustoExigeFonte:
    def test_cost_without_a_basis_is_refused(self):
        """Custo sem fonte e o numero inventado que o subprojeto E recusou."""
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")

        with pytest.raises(ValueError, match="cost_basis"):
            tracker.end_span(span, estimated_cost_usd=0.05)

    def test_cost_with_a_named_basis_is_accepted(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")

        tracker.end_span(
            span, estimated_cost_usd=0.05, cost_basis="TIER_PRICING:tier_3"
        )

        assert span.estimated_cost_usd == 0.05
        assert span.cost_basis == "TIER_PRICING:tier_3"

    def test_zero_cost_needs_no_basis(self):
        """Zero nao afirma preco nenhum, entao nao precisa de fonte."""
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "tool", "tool")

        tracker.end_span(span)

        assert span.estimated_cost_usd == 0.0
        assert span.cost_basis == ""
