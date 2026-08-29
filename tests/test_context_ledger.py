"""Testes do span de contexto: o que o SparkForge poe na janela.

Span de tool tem BYTE. Token de provider e do host, e custo em dolar exige uma
fonte de preco -- os dois ficam vazios aqui, e vazio significa "nao se aplica",
nao "deu zero".
"""
from __future__ import annotations

import sqlite3

import pytest

from sparkforge.observability.store import SQLiteTraceStore
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


class TestMigracaoDeBancoAntigo:
    def test_save_trace_nao_quebra_num_traces_db_criado_antes_desta_task(self, tmp_path):
        """Reproduz o achado do revisor: `CREATE TABLE IF NOT EXISTS` nao
        altera tabela que ja existe, entao um `traces.db` gravado com o
        schema anterior (sem as seis colunas novas) fazia `save_trace`
        quebrar com `OperationalError: table spans has no column named
        payload_bytes`."""
        db_path = tmp_path / "traces.db"

        # Schema de ANTES desta task -- sem as seis colunas novas.
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE traces (
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
                CREATE TABLE spans (
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

        # Abrir o store sobre esse banco antigo deve migrar em silencio.
        store = SQLiteTraceStore(db_path=db_path)

        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "sparkforge_case_get", "tool")
        span.payload_bytes = 42
        tracker.end_span(span)
        tracker.finish_trace(trace)

        store.save_trace(trace)  # nao pode levantar OperationalError

        retrieved = store.get_trace(trace.run_id)
        assert retrieved is not None
        assert retrieved["spans"][0]["payload_bytes"] == 42

    def test_pragma_table_info_de_tabela_inexistente_e_o_caminho_do_banco_novo(self, tmp_path):
        """Trava o caminho que a checagem por `PRAGMA` precisa acertar sem
        engolir excecao nenhuma: tabela que ainda nao existe devolve lista
        vazia de `PRAGMA table_info`, e essa lista vazia -- nao um erro --
        e o sinal de "nada a migrar" que deixa a criacao do zero para o
        `CREATE TABLE IF NOT EXISTS` seguinte."""
        db_path = tmp_path / "novo.db"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("PRAGMA table_info(spans)").fetchall() == []

        store = SQLiteTraceStore(db_path=db_path)  # nao pode levantar

        with sqlite3.connect(store.db_path) as conn:
            colunas = {linha[1] for linha in conn.execute("PRAGMA table_info(spans)").fetchall()}
        assert "payload_bytes" in colunas
        assert "cost_basis" in colunas


class TestOSpanDaChamada:
    def test_a_successful_call_records_the_exact_bytes(self, tmp_path, monkeypatch):
        import json

        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        spans = ledger.spans_of("run_teste")
        assert len(spans) == 1
        esperado = len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
        assert spans[0]["payload_bytes"] == esperado
        assert spans[0]["name"] == "sparkforge_analyze_pyspark"
        assert spans[0]["component_type"] == "tool"
        assert spans[0]["outcome"] == "ok"

    def test_the_declared_item_count_is_carried_not_guessed(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        span = ledger.spans_of("run_teste")[0]
        assert span["item_count"] == resultado["returned_count"]

    def test_the_requested_detail_level_is_recorded(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        tools.call_tool(
            "sparkforge_analyze_pyspark",
            {"path": str(origem), "detail_level": "summary"},
        )

        assert ledger.spans_of("run_teste")[0]["detail_level"] == "summary"

    def test_a_tool_span_never_carries_provider_tokens_or_cost(
        self, tmp_path, monkeypatch
    ):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        span = ledger.spans_of("run_teste")[0]
        assert span["input_tokens"] == 0
        assert span["output_tokens"] == 0
        assert span["estimated_cost_usd"] == 0.0
        assert span["cost_basis"] == ""


class TestOsTresCaminhosDeErro:
    """Recusa tambem ocupa contexto. Uma investigacao cheia de recusa pareceria
    barata se elas nao fossem contadas."""

    def test_an_adapter_error_records_a_span(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        resultado = tools.call_tool(
            "sparkforge_analyze_pyspark", {"path": str(tmp_path / "nao_existe")}
        )

        assert "error" in resultado
        span = ledger.spans_of("run_teste")[0]
        assert span["outcome"] == "error"
        assert span["payload_bytes"] > 0

    def test_an_unauthorized_call_records_a_span(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.agents.autonomy import CallPolicy
        from sparkforge.observability.context_ledger import ContextLedger
        from sparkforge.registry.models import ExecutionProfile

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        politica = CallPolicy(
            agent="sf-runtime-specialist",
            allowed_tools=["sparkforge_case_get"],
            profile=ExecutionProfile.ECO,
            root=tmp_path,
        )
        resultado = tools.call_tool(
            "sparkforge_analyze_pyspark", {"path": str(tmp_path)}, policy=politica
        )

        assert resultado.get("error_code") == "UNAUTHORIZED"
        assert ledger.spans_of("run_teste")[0]["outcome"] == "unauthorized"

    def test_an_unknown_tool_records_nothing(self, tmp_path, monkeypatch):
        """`KeyError` de nome desconhecido e contrato de CATALOGO, e acontece
        ANTES do despacho: nao houve payload nenhum para medir."""
        import pytest

        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        with pytest.raises(KeyError):
            tools.call_tool("sparkforge_inexistente", {})

        assert ledger.spans_of("run_teste") == []


class TestLedgerQuebradoNaoQuebraATool:
    """O teste que mais importa: instrumentacao que derruba o produto e
    defeito, nao observabilidade."""

    def test_an_unwritable_ledger_does_not_change_the_result(
        self, tmp_path, monkeypatch
    ):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        impossivel = tmp_path / "arquivo_no_lugar_do_diretorio"
        impossivel.write_text("nao sou diretorio", encoding="utf-8")
        ledger = ContextLedger(db_path=impossivel / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        assert "items" in resultado
        assert "error" not in resultado
