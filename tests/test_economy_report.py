"""Testes do relatorio de contexto.

Ele compoe sobre o ledger; nao le artefato e nao mede nada por conta propria. O
usage do host, quando existe, aparece AO LADO do byte -- nunca somado a ele,
porque byte de payload e token de provider nao sao a mesma unidade.
"""
from __future__ import annotations

from sparkforge.economy.report import build_context_report
from sparkforge.observability.context_ledger import ContextLedger


def _ledger_com_chamadas(tmp_path, monkeypatch):
    from sparkforge.adapters import tools

    ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
    monkeypatch.setattr(tools, "_LEDGER", ledger)
    origem = tmp_path / "job"
    origem.mkdir()
    (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
    tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})
    tools.call_tool(
        "sparkforge_analyze_pyspark",
        {"path": str(origem), "detail_level": "summary"},
    )
    return ledger


class TestORelatorio:
    def test_payload_is_grouped_by_tool(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        por_tool = relatorio["by_tool"]["sparkforge_analyze_pyspark"]
        assert por_tool["calls"] == 2
        assert por_tool["payload_bytes"] > 0

    def test_the_detail_level_effect_is_reported_whatever_it_is(
        self, tmp_path, monkeypatch
    ):
        """A frase "detail_level reduz" esta publicada e nunca foi medida.

        Este bloco a MEDE. Ele nao afirma que `summary` e menor -- ele reporta
        os dois numeros, e quem le conclui.
        """
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        efeito = relatorio["detail_level_effect"]["sparkforge_analyze_pyspark"]
        assert "" in efeito
        assert "summary" in efeito
        assert all(isinstance(v, int) for v in efeito.values())

    def test_the_surface_at_rest_is_included(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        assert relatorio["surface"]["tools"]["tool_count"] > 0

    def test_host_usage_sits_beside_bytes_never_summed(self, tmp_path, monkeypatch):
        import json

        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        transcript = tmp_path / "sessao.jsonl"
        transcript.write_text(
            json.dumps(
                {"type": "assistant", "message": {"usage": {"input_tokens": 500}}}
            )
            + "\n",
            encoding="utf-8",
        )
        relatorio = build_context_report(
            ledger, run_id="run_teste", host_transcript=transcript
        )

        assert relatorio["host_usage"]["input_tokens"] == 500
        assert "input_tokens" not in relatorio["by_tool"]["sparkforge_analyze_pyspark"]


class TestRecusas:
    def test_a_run_without_spans_is_refused_by_name(self, tmp_path):
        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_vazio")
        relatorio = build_context_report(ledger, run_id="run_inexistente")

        assert relatorio["by_tool"] == {}
        assert {"reason": "run_unresolved", "count": 1} in relatorio["unresolved"]

    def test_without_a_transcript_there_is_no_host_usage(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        assert relatorio["host_usage"] is None
        assert {"reason": "tokens_unresolved", "count": 1} in relatorio["unresolved"]

    def test_nothing_reports_a_dollar_cost(self, tmp_path, monkeypatch):
        """A invariante e "nenhum campo NUMERICO deste relatorio e valor em
        dolar" -- nao "a palavra custo nao aparece em lugar nenhum".

        Por isso a varredura fica restrita ao que o MODULO produz por conta
        propria: `by_tool`, `detail_level_effect` e `host_usage`. `surface`
        fica de fora de proposito: `by_name` dentro dela e nomenclatura
        EXTERNA (nome de tool, de skill, de documento de knowledge) que este
        modulo so repassa sem medir. Descricoes reais ja tem "cost"/"custo"
        (`sparkforge_finops`, `sparkforge_capacity`, entre outras) sem que
        isso seja numero em dolar reportado -- varrer `surface` faria este
        teste quebrar por uma mudanca de nomenclatura alheia ao relatorio, e
        nao por uma regressao real na invariante que ele protege.
        """
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        blob = str(
            (
                relatorio["by_tool"],
                relatorio["detail_level_effect"],
                relatorio["host_usage"],
            )
        ).lower()
        for palavra in ("usd", "cost", "custo"):
            assert palavra not in blob
