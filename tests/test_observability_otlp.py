"""Unidade de `sparkforge/observability/otlp.py`: o export OTLP/JSON.

Cada teste prende uma decisao do DESIGN (`DESIGN_OTEL_GENAI_EXPORT.md`): ids e
tempo deterministicos, canal medido, recusa nomeada, provider declarado e
metricas so onde ha medida.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from sparkforge.observability.otlp import (
    AGENT_DURATION_BOUNDS,
    KIND_INTERNAL,
    KIND_SERVER,
    MCP_DURATION_BOUNDS,
    SEMCONV_GENAI_COMMIT,
    STATUS_ERROR,
    id_hex,
    linhas_jsonl,
    nanos_de_epoch,
    nanos_de_iso,
    projetar,
)

T0 = 1_757_600_000.0


def _span(
    span_id: str,
    name: str = "sparkforge_judge",
    *,
    inicio: float | None = T0,
    fim: float | None = T0 + 0.5,
    outcome: str = "ok",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "span_id": span_id,
        "run_id": "run_t",
        "name": name,
        "start_time": inicio,
        "end_time": fim,
        "outcome": outcome,
        "payload_bytes": 10,
        "payload_basis": "len(json)",
        "detail_level": "",
        "item_count": None,
        **extra,
    }


def _transcript(**attrs: Any) -> dict[str, Any]:
    base = {
        "source": "claude_code",
        "models": ["claude-x"],
        "host_versions": ["2.0.0"],
        "first_timestamp": "2026-09-11T10:00:00.000Z",
        "last_timestamp": "2026-09-11T10:00:30.000Z",
    }
    base.update(attrs)
    return {
        "id": "f_trans",
        "kind": "host.transcript",
        "subject": {"type": "source_location", "file": "q.jsonl", "symbol": "q"},
        "attrs": {k: v for k, v in base.items() if v is not None},
        "provenance": {"artifact_sha256": "abc"},
    }


def _chamada(
    call_id: str,
    *,
    inicio: str | None = "2026-09-11T10:00:01.000Z",
    fim: str | None = "2026-09-11T10:00:02.500Z",
    erro: bool = False,
) -> dict[str, Any]:
    attrs = {
        "channel": "mcp",
        "tool": "mcp__sparkforge__sparkforge_judge",
        "verb": "judge",
        "is_error": erro,
        "call_id": call_id,
        "started_at": inicio,
        "ended_at": fim,
    }
    return {
        "id": "f_" + call_id,
        "kind": "host.tool_call",
        "subject": {"line": 3},
        "measures": {"ordinal": 1, "result_bytes": 42},
        "attrs": {k: v for k, v in attrs.items() if v is not None},
    }


def _uso(**measures: int) -> dict[str, Any]:
    base = {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_tokens": 5,
        "cache_creation_tokens": 7,
        "message_count": 3,
    }
    base.update(measures)
    return {"id": "f_uso", "kind": "host.usage", "measures": base}


def _todos_spans(p) -> list[dict[str, Any]]:
    return [s for rs in p.traces["resourceSpans"] for e in rs["scopeSpans"] for s in e["spans"]]


def _attrs(span: dict[str, Any]) -> dict[str, Any]:
    return {a["key"]: next(iter(a["value"].values())) for a in span["attributes"]}


def _metricas(p) -> dict[str, dict[str, Any]]:
    if p.metrics is None:
        return {}
    return {
        m["name"]: m
        for rm in p.metrics["resourceMetrics"]
        for e in rm["scopeMetrics"]
        for m in e["metrics"]
    }


def _projetar(spans, host=None, provider=None):
    return projetar(spans, host, run_id="run_t", provider=provider, versao="0.0.0+t")


class TestIdsETempo:
    def test_ids_tem_o_tamanho_do_otlp_e_sao_hex(self):
        assert re.fullmatch(r"[0-9a-f]{32}", id_hex("x", 32))
        assert re.fullmatch(r"[0-9a-f]{16}", id_hex("x", 16))

    def test_id_e_deterministico_e_depende_da_semente(self):
        assert id_hex("a", 16) == id_hex("a", 16) != id_hex("b", 16)

    def test_epoch_em_nanos_com_resolucao_de_microssegundo(self):
        assert nanos_de_epoch(1.5) == 1_500_000_000
        assert nanos_de_epoch(0.0000014) == 1000
        assert nanos_de_epoch(None) is None
        assert nanos_de_epoch(True) is None

    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("1970-01-01T00:00:01Z", 1_000_000_000),
            ("1970-01-01T00:00:01.000001+00:00", 1_000_001_000),
            ("1970-01-01T01:00:00+01:00", 0),
        ],
    )
    def test_iso_em_nanos_por_aritmetica_inteira(self, texto, esperado):
        assert nanos_de_iso(texto) == esperado

    @pytest.mark.parametrize("texto", ["", "ontem", "2026-09-11T10:00:00", None, 5])
    def test_iso_invalido_ou_sem_fuso_nao_vira_tempo(self, texto):
        assert nanos_de_iso(texto) is None


class TestSpanDoSparkForge:
    def test_sem_canal_e_execute_tool_interno(self):
        (s,) = _todos_spans(_projetar([_span("a")]))
        assert s["name"] == "execute_tool sparkforge_judge"
        assert s["kind"] == KIND_INTERNAL
        attrs = _attrs(s)
        assert attrs["gen_ai.operation.name"] == "execute_tool"
        assert attrs["gen_ai.tool.name"] == "sparkforge_judge"
        assert "mcp.method.name" not in attrs
        assert "status" not in s

    def test_canal_mcp_medido_e_span_de_servidor(self):
        (s,) = _todos_spans(
            _projetar([_span("a", metadata={"channel": "mcp", "transport": "stdio"})])
        )
        assert s["name"] == "tools/call sparkforge_judge"
        assert s["kind"] == KIND_SERVER
        attrs = _attrs(s)
        assert attrs["mcp.method.name"] == "tools/call"
        assert attrs["network.transport"] == "pipe"
        assert attrs["gen_ai.operation.name"] == "execute_tool"

    def test_canal_lido_do_metadata_json_do_disco(self):
        (s,) = _todos_spans(
            _projetar([_span("a", metadata_json='{"channel": "mcp", "transport": "http"}')])
        )
        assert _attrs(s)["network.transport"] == "tcp"

    def test_metadata_json_quebrado_e_sem_canal(self):
        (s,) = _todos_spans(_projetar([_span("a", metadata_json="{nao e json")]))
        assert s["kind"] == KIND_INTERNAL

    @pytest.mark.parametrize("desfecho", ["error", "unauthorized"])
    def test_desfecho_diferente_de_ok_e_erro_com_o_desfecho_nomeado(self, desfecho):
        (s,) = _todos_spans(_projetar([_span("a", outcome=desfecho)]))
        assert s["status"] == {"code": STATUS_ERROR, "message": desfecho}
        assert _attrs(s)["error.type"] == "tool_error"
        assert _attrs(s)["sparkforge.outcome"] == desfecho

    def test_bytes_saem_como_bytes_e_nunca_como_token(self):
        p = _projetar([_span("a")])
        texto, _ = linhas_jsonl(p)
        assert _attrs(_todos_spans(p)[0])["sparkforge.payload_bytes"] == "10"
        assert "gen_ai.usage" not in texto

    def test_spans_ordenados_por_inicio(self):
        p = _projetar([_span("b", inicio=T0 + 2, fim=T0 + 3), _span("a")])
        assert [s["startTimeUnixNano"] for s in _todos_spans(p)] == sorted(
            s["startTimeUnixNano"] for s in _todos_spans(p)
        )


class TestRecusa:
    @pytest.mark.parametrize(("inicio", "fim"), [(None, T0), (T0, None)])
    def test_span_sem_horario_vira_recusa_nomeada(self, inicio, fim):
        p = _projetar([_span("a"), _span("z", inicio=inicio, fim=fim)])
        assert p.recusados == ({"origin": "sparkforge", "id": "z", "reason": "sem_horario"},)
        assert p.counts["exported"] + p.counts["refused"] == 2

    def test_span_que_nao_e_de_tool_nao_vira_execute_tool(self):
        p = _projetar([_span("a"), _span("t", component_type="task")])
        assert p.recusados == (
            {"origin": "sparkforge", "id": "t", "reason": "componente_nao_tool"},
        )
        assert len(_todos_spans(p)) == 1

    def test_tudo_recusado_da_arquivo_vazio(self):
        p = _projetar([_span("z", fim=None)])
        assert p.traces is None
        assert linhas_jsonl(p) == ("", "")

    def test_tool_call_do_host_sem_horario_nao_sai(self):
        host = [_transcript(), _chamada("c1"), _chamada("c2", fim=None), _uso()]
        p = _projetar([_span("a")], host, provider="anthropic")
        assert {"origin": "host", "id": "c2", "reason": "host_sem_horario"} in p.recusados
        total = p.counts["sparkforge_spans"] + p.counts["host_agent"] + p.counts["host_tool_calls"]
        assert p.counts["exported"] + p.counts["refused"] == total

    def test_transcript_sem_horario_recusa_o_agente_e_os_filhos_saem_sem_pai(self):
        host = [_transcript(first_timestamp=None, last_timestamp=None), _chamada("c1")]
        p = _projetar([], host, provider="anthropic")
        assert {
            "origin": "host",
            "id": "invoke_agent",
            "reason": "transcript_sem_horario",
        } in p.recusados
        (filho,) = _todos_spans(p)
        assert "parentSpanId" not in filho
        assert p.metrics is None


class TestHost:
    def test_invoke_agent_com_usage_e_modelo(self):
        p = _projetar([], [_transcript(), _chamada("c1"), _uso()], provider="anthropic")
        agente, filho = _todos_spans(p)
        assert agente["name"] == "invoke_agent"
        attrs = _attrs(agente)
        assert attrs["gen_ai.provider.name"] == "anthropic"
        assert attrs["gen_ai.request.model"] == "claude-x"
        assert attrs["gen_ai.usage.input_tokens"] == "100"
        assert attrs["gen_ai.usage.output_tokens"] == "20"
        assert attrs["gen_ai.usage.cache_read.input_tokens"] == "5"
        assert attrs["gen_ai.usage.cache_write.input_tokens"] == "7"
        assert filho["parentSpanId"] == agente["spanId"]
        assert _attrs(filho)["gen_ai.tool.call.id"] == "c1"

    def test_host_num_trace_proprio(self):
        p = _projetar([_span("a")], [_transcript(), _chamada("c1"), _uso()], provider="anthropic")
        sf, agente, _ = _todos_spans(p)
        assert sf["traceId"] != agente["traceId"]

    def test_sem_provider_o_atributo_fica_ausente_e_a_lacuna_nomeada(self):
        p = _projetar([], [_transcript(), _uso()])
        assert "gen_ai.provider.name" not in _attrs(_todos_spans(p)[0])
        assert {"field": "gen_ai.provider.name", "reason": "provider_nao_declarado"} in p.unresolved
        assert "gen_ai.client.token.usage" not in _metricas(p)

    def test_sem_usage_nenhum_token(self):
        p = _projetar([], [_transcript()], provider="anthropic")
        texto, metricas = linhas_jsonl(p)
        assert "gen_ai.usage" not in texto
        assert "gen_ai.client.token.usage" not in metricas
        assert {"field": "gen_ai.usage", "reason": "usage_ausente"} in p.unresolved

    def test_dois_modelos_nao_escolhe_um(self):
        p = _projetar([], [_transcript(models=["a", "b"]), _uso()], provider="anthropic")
        assert "gen_ai.request.model" not in _attrs(_todos_spans(p)[0])
        assert {"field": "gen_ai.request.model", "reason": "modelos_multiplos"} in p.unresolved

    def test_arquivo_que_nao_e_transcript_nao_vira_trace(self):
        falha = {"kind": "host.transcript.unresolved", "attrs": {"reason": "host_format_unknown"}}
        p = _projetar([_span("a")], [falha])
        assert len(p.traces["resourceSpans"]) == 1
        assert {"field": "host_transcript", "reason": "host_format_unknown"} in p.unresolved

    def test_tool_call_com_erro(self):
        p = _projetar([], [_transcript(), _chamada("c1", erro=True)], provider="anthropic")
        filho = _todos_spans(p)[1]
        assert filho["status"] == {"code": STATUS_ERROR}
        assert _attrs(filho)["error.type"] == "tool_error"


class TestMetricas:
    def test_duracao_mcp_com_baldes_reais(self):
        spans = [
            _span("a", metadata={"channel": "mcp"}, fim=T0 + 0.01),
            _span("b", metadata={"channel": "mcp"}, fim=T0 + 0.3),
            _span("c", fim=T0 + 9),
        ]
        ponto = _metricas(_projetar(spans))["mcp.server.operation.duration"]["histogram"][
            "dataPoints"
        ][0]
        assert ponto["count"] == "2"
        assert ponto["explicitBounds"] == list(MCP_DURATION_BOUNDS)
        baldes = [int(b) for b in ponto["bucketCounts"]]
        assert baldes[0] == 1 and baldes[MCP_DURATION_BOUNDS.index(0.5)] == 1 and sum(baldes) == 2

    def test_sem_mcp_sem_metrica_de_duracao_mcp(self):
        assert "mcp.server.operation.duration" not in _metricas(_projetar([_span("a")]))

    def test_token_usage_com_count_e_sum_medidos_sem_distribuicao(self):
        p = _projetar([], [_transcript(), _uso()], provider="anthropic")
        pontos = _metricas(p)["gen_ai.client.token.usage"]["histogram"]["dataPoints"]
        por_tipo = {_attrs(pt)["gen_ai.token.type"]: pt for pt in pontos}
        assert por_tipo["input"]["sum"] == 100.0 and por_tipo["input"]["count"] == "3"
        assert por_tipo["output"]["sum"] == 20.0
        assert "explicitBounds" not in por_tipo["input"] and "min" not in por_tipo["input"]
        assert por_tipo["input"]["bucketCounts"] == ["3"]

    def test_duracao_do_agente(self):
        p = _projetar([], [_transcript()], provider="anthropic")
        ponto = _metricas(p)["gen_ai.invoke_agent.duration"]["histogram"]["dataPoints"][0]
        assert ponto["sum"] == 30.0
        assert ponto["explicitBounds"] == list(AGENT_DURATION_BOUNDS)


class TestFormaEDeterminismo:
    def test_mesma_entrada_mesmo_texto(self):
        host = [_transcript(), _chamada("c1"), _uso()]
        spans = [_span("a", metadata={"channel": "mcp"}), _span("b", outcome="error")]
        assert linhas_jsonl(_projetar(spans, host, "anthropic")) == linhas_jsonl(
            _projetar(list(reversed(spans)), host, "anthropic")
        )

    def test_uma_linha_por_sinal_e_forma_otlp(self):
        host = [_transcript(), _chamada("c1"), _uso()]
        traces, metrics = linhas_jsonl(
            _projetar([_span("a", metadata={"channel": "mcp"})], host, "anthropic")
        )
        for texto in (traces, metrics):
            assert texto.count("\n") == 1
            dado = json.loads(texto)
            _forma(dado)
        assert SEMCONV_GENAI_COMMIT in traces


def _forma(no: Any) -> None:
    if isinstance(no, dict):
        for chave, valor in no.items():
            assert "_" not in chave, chave
            if chave == "traceId":
                assert re.fullmatch(r"[0-9a-f]{32}", valor)
            if chave in ("spanId", "parentSpanId"):
                assert re.fullmatch(r"[0-9a-f]{16}", valor)
            if chave.endswith("UnixNano") or chave in ("count", "intValue"):
                assert isinstance(valor, str) and valor.isdigit(), chave
            if chave in ("kind", "code", "aggregationTemporality"):
                assert isinstance(valor, int), chave
            if chave == "key":
                continue
            _forma(valor)
    elif isinstance(no, list):
        for item in no:
            _forma(item)
