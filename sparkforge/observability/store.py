"""Local SQLite Storage for AgentOps Traces and Spans."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from sparkforge.observability.tracer import ExecutionTrace, TraceSpan


class SQLiteTraceStore:
    """Local SQLite backend for persistent observability traces."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (Path.cwd() / ".sparkforge" / "traces.db")
        self._init_db()

    def _init_db(self) -> None:
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    run_id TEXT PRIMARY KEY,
                    task_description TEXT,
                    start_time REAL,
                    end_time REAL,
                    profile TEXT,
                    status TEXT,
                    total_tokens INTEGER,
                    total_cost_usd REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spans (
                    span_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    parent_span_id TEXT,
                    name TEXT,
                    component_type TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration_seconds REAL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cached_tokens INTEGER,
                    estimated_cost_usd REAL,
                    status TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY(run_id) REFERENCES traces(run_id)
                )
            """)
            conn.commit()

    def save_trace(self, trace: ExecutionTrace) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO traces (
                    run_id, task_description, start_time, end_time, profile, status, total_tokens, total_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trace.run_id,
                    trace.task_description,
                    trace.start_time,
                    trace.end_time,
                    trace.profile,
                    trace.status,
                    trace.total_tokens(),
                    trace.total_cost_usd(),
                ),
            )

            for span in trace.spans:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO spans (
                        span_id, run_id, parent_span_id, name, component_type,
                        start_time, end_time, duration_seconds, input_tokens, output_tokens,
                        cached_tokens, estimated_cost_usd, status, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        span.span_id,
                        span.run_id,
                        span.parent_span_id,
                        span.name,
                        span.component_type,
                        span.start_time,
                        span.end_time,
                        span.duration_seconds(),
                        span.input_tokens,
                        span.output_tokens,
                        span.cached_tokens,
                        span.estimated_cost_usd,
                        span.status,
                        json.dumps(span.metadata, default=str),
                    ),
                )
            conn.commit()

    def get_trace(self, run_id: str) -> Optional[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM traces WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            trace_dict = dict(row)

            cursor.execute("SELECT * FROM spans WHERE run_id = ?", (run_id,))
            trace_dict["spans"] = [dict(s) for s in cursor.fetchall()]
            return trace_dict
