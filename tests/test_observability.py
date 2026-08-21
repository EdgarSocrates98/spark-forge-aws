"""Tests for SparkForge Local-First Observability (Phase 9)."""
import time
import pytest

from sparkforge.observability import AgentOpsTracker, SQLiteTraceStore


def test_agentops_tracer_and_sqlite_store(tmp_path):
    tracker = AgentOpsTracker()
    store = SQLiteTraceStore(db_path=tmp_path / "traces.db")

    trace = tracker.start_trace(task_description="Diagnose Glue memory skew", profile="eco")
    span1 = tracker.start_span(trace, name="extract_facts", component_type="tool")
    tracker.end_span(span1, input_tokens=500, output_tokens=100, cached_tokens=0, estimated_cost_usd=0.0002)

    span2 = tracker.start_span(trace, name="judge_bottleneck", component_type="agent", parent_span_id=span1.span_id)
    tracker.end_span(span2, input_tokens=1200, output_tokens=300, cached_tokens=500, estimated_cost_usd=0.0008)

    tracker.finish_trace(trace, status="completed")

    assert trace.total_tokens() == 2100
    assert trace.total_cost_usd() == 0.001

    # Save to SQLite
    store.save_trace(trace)

    # Retrieve and verify
    retrieved = store.get_trace(trace.run_id)
    assert retrieved is not None
    assert retrieved["task_description"] == "Diagnose Glue memory skew"
    assert retrieved["total_tokens"] == 2100
    assert len(retrieved["spans"]) == 2
