"""FASE 10 do prompt_evo_runtime: AgentOps v2.

- §68: `agentops timeline <run>` -- eventos ordenados por lane
  (task/context/routing/agent/model/tool/review/debate/checkpoint).
- §69: critical path -- latencias maiores primeiro, retries e waiting
  nomeados, nunca somados a zero.
- §12: `provider_usage_coverage` = measured/total de spans de modelo.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.observability.agentops import (
    critical_path,
    inspect_run,
    run_timeline,
)
from sparkforge_aws.observability.store import SQLiteTraceStore
from sparkforge_aws.observability.tracer import ExecutionTrace, TraceSpan


def _trace(run_id: str, spans: list[TraceSpan]) -> ExecutionTrace:
    return ExecutionTrace(
        run_id=run_id,
        task_description="t",
        start_time=min(s.start_time for s in spans),
        end_time=max(s.end_time for s in spans),
        profile="economy",
        status="ok",
        spans=spans,
    )


_SEQ = 0


def _span(run_id, name, component, start, end, **kw) -> TraceSpan:
    global _SEQ
    _SEQ += 1
    return TraceSpan(
        span_id=f"{run_id}-{name}-{_SEQ}",
        run_id=run_id,
        parent_span_id=None,
        name=name,
        component_type=component,
        start_time=start,
        end_time=end,
        status="ok",
        **kw,
    )


def _store(tmp_path: Path) -> SQLiteTraceStore:
    return SQLiteTraceStore(tmp_path / "traces.db")


class TestTimeline:
    def test_eventos_ordenados_com_lane_e_duracao(self, tmp_path):
        store = _store(tmp_path)
        spans = [
            _span("r1", "ctx", "context", 0.0, 1.0),
            _span("r1", "model-a", "model", 1.0, 4.0),
            _span("r1", "tool-x", "tool", 4.0, 5.0),
        ]
        store.save_trace(_trace("r1", spans))
        timeline = run_timeline(tmp_path / "traces.db", "r1")
        assert timeline["status"] == "ok"
        eventos = timeline["events"]
        assert [e["name"] for e in eventos] == ["ctx", "model-a", "tool-x"]
        assert eventos[0]["lane"] == "context"
        assert eventos[1]["duration_seconds"] == 3.0

    def test_run_ausente_e_unresolved(self, tmp_path):
        _store(tmp_path)
        timeline = run_timeline(tmp_path / "traces.db", "nope")
        assert timeline["status"] == "unresolved"
        assert "run_not_found" in timeline["unresolved"]


class TestCriticalPath:
    def test_dominante_e_retry_e_waiting_nomeados(self, tmp_path):
        store = _store(tmp_path)
        spans = [
            _span("r1", "tool-x", "tool", 0.0, 1.0),
            _span("r1", "tool-x", "tool", 1.0, 2.0),  # retry: mesmo nome
            _span("r1", "model-a", "model", 5.0, 9.0),  # gap 3s = waiting
        ]
        store.save_trace(_trace("r1", spans))
        path = critical_path(tmp_path / "traces.db", "r1")
        assert path["status"] == "ok"
        dominante = path["top"][0]
        assert dominante["name"] == "model-a"
        assert dominante["duration_seconds"] == 4.0
        assert path["retries"] == {"tool-x": 2}
        assert path["waiting_seconds"] == 3.0


class TestProviderUsageCoverage:
    def test_coverage_medido_sobre_total(self, tmp_path):
        store = _store(tmp_path)
        spans = [
            _span(
                "r1",
                "model-a",
                "model",
                0.0,
                1.0,
                input_tokens=10,
                output_tokens=5,
                tokens_status="measured",
            ),
            _span("r1", "model-b", "model", 1.0, 2.0, tokens_status="unresolved"),
        ]
        store.save_trace(_trace("r1", spans))
        report = inspect_run(tmp_path / "traces.db", "r1")
        coverage = report["models"]["provider_usage_coverage"]
        assert coverage == {"measured": 1, "total": 2, "coverage": 0.5}

    def test_sem_modelo_coverage_unresolved(self, tmp_path):
        store = _store(tmp_path)
        store.save_trace(_trace("r1", [_span("r1", "t", "tool", 0.0, 1.0)]))
        report = inspect_run(tmp_path / "traces.db", "r1")
        assert report["models"]["provider_usage_coverage"]["coverage"] == "unresolved"
