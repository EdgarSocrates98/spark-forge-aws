"""FASE 1 do prompt_evo_runtime: P0 de corretude.

Tres defeitos auditados em `docs/audit/RUNTIME-CONVERGENCE-BASELINE.md`:

1. `unknown -> zero`: tokens e custo de modelo sem medicao saiam como 0.
2. `cost_basis` reconciliado sobre TODOS os eventos -- um evento de tool sem
   custo invalidava o run inteiro.
3. `risk`, `required_reasoning` e `complexity` decorativos no router.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sparkforge_aws.economy.ledger import LedgerEvent, TokenLedger
from sparkforge_aws.economy.model_router import (
    AdaptiveModelRouter,
    ModelCandidate,
    ModelRoutingInput,
    ModelScorecard,
)
from sparkforge_aws.observability.agentops import inspect_run
from sparkforge_aws.observability.store import SQLiteTraceStore
from sparkforge_aws.observability.tracer import AgentOpsTracker, ExecutionTrace, TraceSpan


class TestCostBasisSoEventosComCusto:
    def test_tool_event_without_cost_does_not_poison_a_priced_model_event(self):
        """O defeito medido: `reconcile` exigia `cost_basis` de TODO evento.
        Um evento de tool (custo legitimamente ausente) marcava o run inteiro
        `cost_basis_unresolved` mesmo com o modelo carregando a fonte do preco."""
        ledger = TokenLedger(
            [
                LedgerEvent(
                    "run-1",
                    "agent-1",
                    "model",
                    observed_cost_usd=0.01,
                    cost_basis="PRICE_TABLE:provider/model@2026-10-04",
                ),
                LedgerEvent("run-1", "agent-1", "tool", observed_tool_calls=1),
            ]
        )
        result = ledger.reconcile()
        assert result["metrics"]["cost_usd"]["status"] == "measured"
        assert result["metrics"]["cost_usd"]["observed"] == 0.01

    def test_cost_basis_still_required_when_cost_is_present(self):
        """O gate de `LedgerEvent.__post_init__` nao muda: custo sem fonte
        continua recusado na entrada."""
        with pytest.raises(ValueError, match="cost_basis"):
            LedgerEvent("run-1", "agent-1", "model", observed_cost_usd=0.01)


class TestTokenStatusDoSpan:
    def test_tool_span_without_tokens_is_not_applicable_not_zero(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "sparkforge_case_get", "tool")
        tracker.end_span(span)
        assert span.resolved_tokens_status() == "not_applicable"

    def test_model_span_without_usage_is_unresolved(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")
        tracker.end_span(span)
        assert span.resolved_tokens_status() == "unresolved"

    def test_model_span_with_usage_is_measured(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")
        tracker.end_span(span, input_tokens=10, output_tokens=5)
        assert span.resolved_tokens_status() == "measured"

    def test_explicit_status_allows_a_measured_zero(self):
        """Provider que reporta 0 tokens existe; so o chamador sabe. Valor
        explicito sempre vence a derivacao."""
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")
        tracker.end_span(span, tokens_status="measured")
        assert span.resolved_tokens_status() == "measured"

    def test_unknown_status_is_refused(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")
        with pytest.raises(ValueError, match="tokens_status"):
            tracker.end_span(span, tokens_status="meio-medido")

    def test_tokens_status_persisted_and_migrated(self, tmp_path):
        """Coluna nova entra por migracao aditiva como as seis anteriores, e
        banco antigo sem ela continua abrindo."""
        db = tmp_path / "traces.db"
        store = SQLiteTraceStore(db)
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        model = tracker.start_span(trace, "modelo", "model")
        tracker.end_span(model)
        tool = tracker.start_span(trace, "tool", "tool")
        tracker.end_span(tool)
        tracker.finish_trace(trace)
        store.save_trace(trace)

        row = store.get_trace(trace.run_id)
        by_type = {s["component_type"]: s for s in row["spans"]}
        assert by_type["model"]["tokens_status"] == "unresolved"
        assert by_type["tool"]["tokens_status"] == "not_applicable"

        # Banco criado antes da coluna: migra e grava normal.
        db_antigo = tmp_path / "velho.db"
        with sqlite3.connect(db_antigo) as conn:
            conn.execute(
                "CREATE TABLE traces (run_id TEXT PRIMARY KEY, task_description TEXT,"
                " start_time REAL, end_time REAL, profile TEXT, status TEXT,"
                " total_tokens INTEGER, total_cost_usd REAL)"
            )
            conn.execute(
                "CREATE TABLE spans (span_id TEXT PRIMARY KEY, run_id TEXT,"
                " parent_span_id TEXT, name TEXT, component_type TEXT, start_time REAL,"
                " end_time REAL, duration_seconds REAL, input_tokens INTEGER,"
                " output_tokens INTEGER, cached_tokens INTEGER, estimated_cost_usd REAL,"
                " status TEXT, metadata_json TEXT)"
            )
        velho = SQLiteTraceStore(db_antigo)
        velho.save_trace(trace)  # nao pode levantar OperationalError


class TestInspectRunDistingueNaoObservado:
    def _save(self, db: Path, run_id: str, spans: list[TraceSpan]) -> None:
        SQLiteTraceStore(db).save_trace(
            ExecutionTrace(run_id, "task", 1.0, 2.0, "economy", "completed", spans)
        )

    def test_tool_only_run_reports_not_applicable(self, tmp_path):
        self._save(
            tmp_path / "t.db",
            "run-t",
            [TraceSpan("s1", "run-t", None, "facts", "tool", 1.0, 2.0, payload_bytes=10)],
        )
        report = inspect_run(tmp_path / "t.db", "run-t")
        assert report["models"]["tokens"]["status"] == "not_applicable"
        assert report["models"]["cost"]["status"] == "not_applicable"

    def test_unobserved_model_span_is_unresolved_not_zero(self, tmp_path):
        self._save(
            tmp_path / "t.db",
            "run-m",
            [TraceSpan("s1", "run-m", None, "modelo", "model", 1.0, 2.0)],
        )
        report = inspect_run(tmp_path / "t.db", "run-m")
        assert report["models"]["tokens"]["status"] == "unresolved"
        assert report["models"]["tokens"]["observed"] is None
        assert report["models"]["cost"]["status"] == "unresolved"
        assert report["models"]["cost"]["observed"] is None

    def test_measured_model_reports_sum(self, tmp_path):
        self._save(
            tmp_path / "t.db",
            "run-m",
            [
                TraceSpan(
                    "s1",
                    "run-m",
                    None,
                    "modelo",
                    "model",
                    1.0,
                    2.0,
                    input_tokens=100,
                    output_tokens=20,
                    estimated_cost_usd=0.005,
                    cost_basis="PRICE_TABLE:p/m@2026-10-04",
                )
            ],
        )
        report = inspect_run(tmp_path / "t.db", "run-m")
        assert report["models"]["tokens"]["status"] == "measured"
        assert report["models"]["tokens"]["observed"] == 120
        assert report["models"]["cost"]["status"] == "measured"
        assert report["models"]["cost"]["observed"] == 0.005

    def test_mixed_model_spans_are_partial(self, tmp_path):
        self._save(
            tmp_path / "t.db",
            "run-x",
            [
                TraceSpan(
                    "s1",
                    "run-x",
                    None,
                    "m1",
                    "model",
                    1.0,
                    2.0,
                    input_tokens=50,
                    output_tokens=10,
                    estimated_cost_usd=0.001,
                    cost_basis="PRICE_TABLE:p/m@2026-10-04",
                ),
                TraceSpan("s2", "run-x", None, "m2", "model", 2.0, 3.0),
            ],
        )
        report = inspect_run(tmp_path / "t.db", "run-x")
        assert report["models"]["tokens"]["status"] == "partial"
        assert report["models"]["tokens"]["observed"] == 60
        assert report["models"]["cost"]["status"] == "partial"


class TestRouterInputsOperacionais:
    def test_risk_above_declared_max_excludes_candidate(self):
        router = AdaptiveModelRouter(
            (
                ModelCandidate("p", "weak", max_risk=1),
                ModelCandidate("p", "strong", max_risk=3),
            )
        )
        decision = router.route(ModelRoutingInput("diagnosis", risk=3))
        assert decision.selected is not None
        assert decision.selected.model == "strong"

    def test_required_reasoning_demands_declared_capability(self):
        router = AdaptiveModelRouter(
            (
                ModelCandidate("p", "plain"),
                ModelCandidate("p", "thinker", capabilities=("reasoning",)),
            )
        )
        decision = router.route(ModelRoutingInput("diagnosis", required_reasoning=2))
        assert decision.selected is not None
        assert decision.selected.model == "thinker"

    def test_no_declared_reasoning_candidate_names_the_gap(self):
        router = AdaptiveModelRouter((ModelCandidate("p", "plain"),))
        decision = router.route(ModelRoutingInput("diagnosis", required_reasoning=2))
        assert decision.selected is None
        assert "required_reasoning_unmet" in decision.unresolved

    def test_complexity_differentiates_candidates(self):
        """`-complexity` identico para todos nao move ranking. Com complexidade
        alta, o modelo de menor qualidade tem que perder para o de maior."""
        router = AdaptiveModelRouter(
            (ModelCandidate("p", "low"), ModelCandidate("p", "high")),
            (
                ModelScorecard("p", "low", "diagnosis", quality=0.60),
                ModelScorecard("p", "high", "diagnosis", quality=0.90),
            ),
        )
        low_complexity = router.route(ModelRoutingInput("diagnosis", complexity=1))
        assert low_complexity.selected is not None and low_complexity.selected.model == "high"

        # Complexidade alta: a margem do modelo forte continua maior, e a
        # distancia entre os dois cresce -- prova de que `complexity` entra no
        # score por candidato, nao como constante morta.
        scores = {
            c.model: router._score(c, ModelRoutingInput("diagnosis", complexity=5))
            for c in router.candidates
        }
        assert scores["high"][0] > scores["low"][0]
        simples = {
            c.model: router._score(c, ModelRoutingInput("diagnosis", complexity=1))
            for c in router.candidates
        }
        assert (scores["high"][0] - scores["low"][0]) > (
            simples["high"][0] - simples["low"][0]
        )
