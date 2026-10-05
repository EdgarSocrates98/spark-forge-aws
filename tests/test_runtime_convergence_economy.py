"""FASE 2 do prompt_evo_runtime: convergencia da economia.

- `waste_detector` para de inventar estimativas (500 tokens/chamada,
  $0.80/Mtok, $15/Mtok eram numeros fabricados sem fonte).
- `economy/reconcile.py` cruza as tres superficies de medicao (transcript do
  host, ledger de eventos, spans do trace) por eixo, com status
  measured/conflict/unresolved e divergencia nomeada -- nunca media.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sparkforge.economy.ledger import LedgerEvent
from sparkforge.economy.reconcile import reconcile_run_economy
from sparkforge.economy.waste_detector import TokenWasteDetector
from sparkforge.observability.store import SQLiteTraceStore
from sparkforge.observability.tracer import ExecutionTrace, TraceSpan


class TestWasteSemEstimativaInventada:
    def test_duplicate_calls_report_observed_tokens_not_fabricated(self):
        detector = TokenWasteDetector()
        events = [
            {"type": "tool_call", "name": "t", "args": {"a": 1}, "tokens": 500},
            {"type": "tool_call", "name": "t", "args": {"a": 1}, "tokens": 500},
            {"type": "tool_call", "name": "t", "args": {"a": 1}, "tokens": 500},
        ]
        findings = detector.analyze_trace(events)
        dup = next(f for f in findings if f.pattern_id == "WASTE-001")
        # 500 medidos em cada chamada redundante, nao (count-1)*500 inventado.
        assert dup.observed_wasted_tokens == 1000
        # Sem tabela de preco declarada, custo fica unresolved -- nunca um
        # numero com fonte inventada.
        assert dup.estimated_wasted_cost_usd is None
        assert dup.measurement_status["cost"] == "unresolved"

    def test_duplicate_calls_without_event_tokens_are_unresolved(self):
        detector = TokenWasteDetector()
        events = [
            {"type": "tool_call", "name": "t", "args": {"a": 1}},
            {"type": "tool_call", "name": "t", "args": {"a": 1}},
            {"type": "tool_call", "name": "t", "args": {"a": 1}},
        ]
        dup = next(
            f for f in detector.analyze_trace(events) if f.pattern_id == "WASTE-001"
        )
        assert dup.observed_wasted_tokens is None
        assert dup.measurement_status["tokens"] == "unresolved"

    def test_premium_on_simple_is_hypothesis_not_measured_waste(self):
        detector = TokenWasteDetector()
        events = [
            {
                "type": "model_call",
                "tier": "tier_5_premium",
                "task_complexity": "low",
                "tokens": 2000,
            }
        ]
        findings = detector.analyze_trace(events)
        prem = next(f for f in findings if f.pattern_id == "WASTE-002")
        # Os tokens da chamada sao observados; a afirmacao de "desperdicio"
        # depende de um caminho mais barato que nao foi executado = hipotese.
        assert prem.observed_wasted_tokens is None
        assert prem.classification == "hypothesis"


def _trace_with_spans(db: Path, run_id: str, spans: list[TraceSpan]) -> dict:
    SQLiteTraceStore(db).save_trace(
        ExecutionTrace(run_id, "task", 1.0, 2.0, "eco", "completed", spans)
    )
    store = SQLiteTraceStore(db)
    return store.get_trace(run_id)


class TestReconcileRunEconomy:
    def test_three_surfaces_agree_measured(self, tmp_path):
        trace = _trace_with_spans(
            tmp_path / "t.db",
            "run-1",
            [
                TraceSpan(
                    "s1", "run-1", None, "m", "model", 1.0, 2.0,
                    input_tokens=100, output_tokens=20,
                    estimated_cost_usd=0.01, cost_basis="PRICE_TABLE:p/m@d",
                ),
                TraceSpan("s2", "run-1", None, "t", "tool", 2.0, 3.0, payload_bytes=42),
            ],
        )
        result = reconcile_run_economy(
            trace=trace,
            ledger_events=[
                LedgerEvent(
                    "run-1", "a", "model", observed_tokens=120,
                    observed_cost_usd=0.01, cost_basis="PRICE_TABLE:p/m@d",
                )
            ],
        )
        assert result["axes"]["provider_tokens"]["status"] == "measured"
        assert result["axes"]["provider_tokens"]["authoritative"] == 120
        assert result["axes"]["cost_usd"]["status"] == "measured"
        assert result["axes"]["tool_calls"]["status"] == "measured"
        assert result["axes"]["payload_bytes"]["authoritative"] == 42

    def test_ledger_trace_conflict_is_named_not_averaged(self, tmp_path):
        trace = _trace_with_spans(
            tmp_path / "t.db",
            "run-1",
            [
                TraceSpan(
                    "s1", "run-1", None, "m", "model", 1.0, 2.0,
                    input_tokens=100, output_tokens=20, tokens_status="measured",
                )
            ],
        )
        result = reconcile_run_economy(
            trace=trace,
            ledger_events=[
                LedgerEvent("run-1", "a", "model", observed_tokens=999)
            ],
        )
        axis = result["axes"]["provider_tokens"]
        assert axis["status"] == "conflict"
        assert axis["authoritative"] is None
        assert axis["sources"]["trace"] == 120
        assert axis["sources"]["ledger"] == 999

    def test_nothing_measured_is_unresolved_everywhere(self):
        result = reconcile_run_economy()
        assert result["axes"]["provider_tokens"]["status"] == "unresolved"
        assert result["axes"]["cost_usd"]["status"] == "unresolved"
        assert result["axes"]["tool_calls"]["status"] == "unresolved"
        assert result["axes"]["payload_bytes"]["status"] == "unresolved"

    def test_transcript_ledger_disagreement_is_conflict_not_silent_choice(self):
        """Duas medicoes que divergem nao podem ser escolhidas em silencio:
        saem como `conflict` com as duas fontes nomeadas."""
        result = reconcile_run_economy(
            ledger_events=[
                LedgerEvent("run-1", "a", "model", observed_tokens=50)
            ],
            provider_usage={"input_tokens": 80, "output_tokens": 20},
        )
        axis = result["axes"]["provider_tokens"]
        assert axis["status"] == "conflict"
        assert axis["authoritative"] is None
        assert axis["sources"]["transcript"] == 100
        assert axis["sources"]["ledger"] == 50

    def test_single_measured_source_is_authoritative(self):
        result = reconcile_run_economy(
            provider_usage={"input_tokens": 80, "output_tokens": 20},
        )
        axis = result["axes"]["provider_tokens"]
        assert axis["status"] == "measured"
        assert axis["authoritative"] == 100
