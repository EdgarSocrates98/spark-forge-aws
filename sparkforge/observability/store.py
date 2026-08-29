"""Local SQLite Storage for AgentOps Traces and Spans."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from sparkforge.observability.tracer import ExecutionTrace


class SQLiteTraceStore:
    """Local SQLite backend for persistent observability traces."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (Path.cwd() / ".sparkforge" / "traces.db")
        self._init_db()

    # Colunas que a Task 1 acrescentou a `spans`, com o tipo de cada uma. Usado
    # so pela migracao -- ver `_migrar_colunas_novas_de_spans`.
    _COLUNAS_NOVAS_DE_SPANS = (
        ("payload_bytes", "INTEGER"),
        ("payload_basis", "TEXT"),
        ("detail_level", "TEXT"),
        ("item_count", "INTEGER"),
        ("outcome", "TEXT"),
        ("cost_basis", "TEXT"),
    )

    def _init_db(self) -> None:
        """Cria as tabelas, e migra `spans` que ja existia antes destas colunas.

        `CREATE TABLE IF NOT EXISTS` nao altera tabela que ja existe -- um
        `traces.db` gravado antes desta Task ficaria com `spans` faltando as
        seis colunas novas, e todo `save_trace` seguinte quebraria com
        `OperationalError: table spans has no column named payload_bytes`.

        `sparkforge/codeintel/db.py` resolve o mesmo problema jogando o banco
        fora quando a versao diverge (`_descartar_schema_de_versao_anterior`),
        e a razao la e que aquele indice e descartavel: reindexar reproduz o
        mesmo dado, entao o DROP nao perde nada que uma nova rodada nao
        devolva identico. Trace nao tem essa propriedade -- um span registra
        uma chamada de tool que ja aconteceu, e nao ha "reindexar" que a
        reproduza. DROP aqui apagaria historico de verdade. Por isso a
        migracao e aditiva: `ALTER TABLE ADD COLUMN` por coluna, preservando
        toda linha que ja existia.
        """
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
            self._migrar_colunas_novas_de_spans(conn)
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
                    payload_bytes INTEGER,
                    payload_basis TEXT,
                    detail_level TEXT,
                    item_count INTEGER,
                    outcome TEXT,
                    cost_basis TEXT,
                    FOREIGN KEY(run_id) REFERENCES traces(run_id)
                )
            """)
            conn.commit()

    def _migrar_colunas_novas_de_spans(self, conn: sqlite3.Connection) -> None:
        """Adiciona as colunas novas de `spans` numa tabela ja existente.

        Roda ANTES do `CREATE TABLE IF NOT EXISTS spans`, entao a criacao do
        zero fica por conta da instrucao seguinte quando a tabela ainda nao
        existe.

        A checagem e por `PRAGMA table_info(spans)`, e nao por tentar o
        `ALTER TABLE` e engolir `OperationalError`. `duplicate column name` e
        `OperationalError`, mas `database is locked` e `disk I/O error`
        tambem sao -- e o caso ruim e o lock TRANSITORIO: presente durante
        este `ALTER TABLE`, liberado a tempo do `CREATE TABLE IF NOT EXISTS`
        seguinte. Engolindo por tipo de excecao, a migracao falharia de
        verdade, a tabela ficaria sem a coluna, nada acusaria aqui, e o erro
        so apareceria depois em `save_trace` -- parecendo o bug original
        voltando, sem pista de que a causa foi um lock passageiro no
        `_init_db`. Perguntar ao catalogo da tabela ANTES de agir nao
        precisa de except nenhum: as colunas que faltam foram calculadas por
        um SELECT, entao qualquer `OperationalError` que sobrar de um ALTER
        e falha de verdade e deve propagar.

        `PRAGMA table_info` de tabela que ainda nao existe devolve lista
        vazia (nao levanta), e lista vazia aqui significa "nada a migrar" --
        o `CREATE TABLE IF NOT EXISTS` seguinte cria a tabela nova ja com as
        seis colunas.
        """
        colunas_existentes = {
            linha[1] for linha in conn.execute("PRAGMA table_info(spans)").fetchall()
        }
        if not colunas_existentes:
            return
        for nome, tipo in self._COLUNAS_NOVAS_DE_SPANS:
            if nome not in colunas_existentes:
                conn.execute(f"ALTER TABLE spans ADD COLUMN {nome} {tipo}")

    def save_trace(self, trace: ExecutionTrace) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO traces (
                    run_id, task_description, start_time, end_time, profile, status,
                    total_tokens, total_cost_usd
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
                        cached_tokens, estimated_cost_usd, status, metadata_json,
                        payload_bytes, payload_basis, detail_level, item_count,
                        outcome, cost_basis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        span.payload_bytes,
                        span.payload_basis,
                        span.detail_level,
                        span.item_count,
                        span.outcome,
                        span.cost_basis,
                    ),
                )
            conn.commit()

    def get_trace(self, run_id: str) -> dict[str, Any] | None:
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
