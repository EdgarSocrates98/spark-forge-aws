"""Golden de `sparkforge telemetry export` sobre o corpus `fixtures/otel/`.

Cada caso traz `input/spans.json` (os spans como `context_ledger.spans_of` os
devolve, de chamadas REAIS de `call_tool`, com `span_id` e horario
normalizados), `input/transcript.jsonl` quando ha host, e `meta.yaml` com
`run_id`, `provider` e `host_transcript`. O golden e o que a CLI grava:
`traces.jsonl`, `metrics.jsonl` e `result.json` (contagens, recusas e lacunas).
`scripts/regen_fixtures.py::saidas_otel` produz os tres pelo mesmo
`_core.telemetry_payload` e pelo mesmo `telemetry_export_textos` da CLI.

A prova de que um consumidor aceita o arquivo e o job `otel-collector` do CI,
com `scripts/check_otel_collector.py`. Aqui fica a forma do OTLP/JSON 1.11.0
(ids em hex, int64 como string, enum inteiro, lowerCamelCase), a soma que fecha
e a regra de que token so vem do transcript.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "otel"
SAIDAS = ("traces.jsonl", "metrics.jsonl", "result.json")


def _regen() -> Any:
    """`scripts/regen_fixtures.py` pelo caminho, sem por a raiz no `sys.path`:
    no gate de wheel isso faria o `sparkforge` do repositorio vencer o instalado."""
    spec = importlib.util.spec_from_file_location(
        "regen_fixtures", ROOT / "scripts" / "regen_fixtures.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _casos() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir() and not p.name.startswith("_"))


def _texto(caminho: Path) -> str:
    return caminho.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _meta(caso: Path) -> dict[str, Any]:
    return yaml.safe_load(_texto(caso / "meta.yaml"))


def _linhas(caso: Path, nome: str) -> list[dict[str, Any]]:
    return [json.loads(linha) for linha in _texto(caso / "expected" / nome).splitlines()]


def _spans(caso: Path) -> list[dict[str, Any]]:
    return [
        span
        for dado in _linhas(caso, "traces.jsonl")
        for rs in dado["resourceSpans"]
        for escopo in rs["scopeSpans"]
        for span in escopo["spans"]
    ]


def _attrs(no: dict[str, Any]) -> dict[str, Any]:
    return {a["key"]: next(iter(a["value"].values())) for a in no.get("attributes", [])}


def _forma(no: Any) -> None:
    if isinstance(no, dict):
        for chave, valor in no.items():
            assert "_" not in chave, chave
            if chave == "traceId":
                assert re.fullmatch(r"[0-9a-f]{32}", valor), valor
            if chave in ("spanId", "parentSpanId"):
                assert re.fullmatch(r"[0-9a-f]{16}", valor), valor
            if chave.endswith("UnixNano") or chave in ("count", "intValue"):
                assert isinstance(valor, str) and valor.isdigit(), chave
            if chave == "bucketCounts":
                assert all(isinstance(v, str) and v.isdigit() for v in valor)
            if chave in ("kind", "code", "aggregationTemporality"):
                assert isinstance(valor, int), chave
            if chave == "key":
                continue
            _forma(valor)
    elif isinstance(no, list):
        for item in no:
            _forma(item)


def test_o_corpus_tem_os_quatro_casos():
    assert [p.name for p in _casos()] == [
        "com_host",
        "host_sem_usage",
        "sparkforge_erro",
        "sparkforge_ok",
    ]


@pytest.mark.parametrize("caso", _casos(), ids=lambda p: p.name)
class TestCaso:
    def test_saidas_batem_com_o_golden(self, caso):
        saidas = _regen().saidas_otel(caso)
        for nome in SAIDAS:
            assert saidas[nome] == _texto(caso / "expected" / nome), nome

    def test_exportar_de_novo_da_o_mesmo_texto(self, caso):
        regen = _regen()
        assert regen.saidas_otel(caso) == regen.saidas_otel(caso)

    def test_uma_linha_por_sinal_e_forma_otlp(self, caso):
        for nome in ("traces.jsonl", "metrics.jsonl"):
            texto = _texto(caso / "expected" / nome)
            assert texto.count("\n") <= 1
            for dado in _linhas(caso, nome):
                _forma(dado)

    def test_nenhum_span_some(self, caso):
        resultado = json.loads(_texto(caso / "expected" / "result.json"))
        contagem = resultado["counts"]
        total = contagem["sparkforge_spans"] + contagem["host_agent"] + contagem["host_tool_calls"]
        assert contagem["exported"] + contagem["refused"] == total
        assert contagem["exported"] == len(_spans(caso))
        assert contagem["refused"] == len(resultado["refused"])
        assert contagem["sparkforge_spans"] == len(
            json.loads(_texto(caso / "input" / "spans.json"))
        )

    def test_token_so_com_transcript(self, caso):
        if _meta(caso).get("host_transcript"):
            return
        for nome in ("traces.jsonl", "metrics.jsonl"):
            assert "gen_ai.usage" not in _texto(caso / "expected" / nome)
            assert "gen_ai.client.token.usage" not in _texto(caso / "expected" / nome)

    def test_so_quem_veio_pelo_mcp_tem_mcp_method_name(self, caso):
        from sparkforge.observability.otlp import id_hex

        por_id = {
            id_hex("sparkforge:" + s["span_id"], 16): s
            for s in json.loads(_texto(caso / "input" / "spans.json"))
        }
        vistos = 0
        for span in _spans(caso):
            entrada = por_id.get(span["spanId"])
            if entrada is None:
                continue
            vistos += 1
            pelo_mcp = entrada["metadata"].get("channel") == "mcp"
            assert ("mcp.method.name" in _attrs(span)) is pelo_mcp
            assert span["name"].startswith("tools/call " if pelo_mcp else "execute_tool ")
        assert vistos

    def test_a_cli_grava_como_o_golden(self, caso, tmp_path, monkeypatch, capsys):
        """A CLI de verdade, lendo os spans de um `traces.db` real (o caminho do
        disco, com `metadata_json`), e nao do `spans.json` direto."""
        from sparkforge.adapters import _core, cli
        from sparkforge.observability import context_ledger
        from sparkforge.observability.store import SQLiteTraceStore
        from sparkforge.observability.tracer import ExecutionTrace, TraceSpan

        regen = _regen()
        monkeypatch.setattr(_core, "_versao_sparkforge", lambda: regen.SARIF_GOLDEN_VERSION)
        meta = _meta(caso)
        run_id = meta["run_id"]
        db = tmp_path / ".sparkforge" / "traces.db"
        db.parent.mkdir()
        spans = [TraceSpan(**s) for s in json.loads(_texto(caso / "input" / "spans.json"))]
        SQLiteTraceStore(db_path=db).save_trace(
            ExecutionTrace(
                run_id=run_id,
                task_description="fixture",
                start_time=min(s.start_time for s in spans),
                end_time=max(s.end_time for s in spans if s.end_time),
                status="completed",
                spans=spans,
            )
        )
        monkeypatch.setattr(
            context_ledger, "_SHARED_LEDGER", context_ledger.ContextLedger(db_path=db)
        )
        argv = ["telemetry", "export", "--run-id", run_id, "--repo", str(tmp_path)]
        if meta.get("host_transcript"):
            argv += ["--host-transcript", str(caso / meta["host_transcript"])]
        if meta.get("provider"):
            argv += ["--provider", meta["provider"]]

        assert cli.main(argv) == 0
        resumo = json.loads(capsys.readouterr().out)
        esperado = json.loads(_texto(caso / "expected" / "result.json"))
        assert resumo["counts"] == esperado["counts"]
        gravado = tmp_path / ".sparkforge" / "telemetry"
        for nome in ("traces.jsonl", "metrics.jsonl"):
            assert _texto(gravado / f"{run_id}.{nome}") == _texto(caso / "expected" / nome), nome


def test_com_host_os_tokens_sao_os_do_host_usage():
    """SC6: os `gen_ai.usage.*` exportados sao os que o extrator mediu."""
    from sparkforge.facts.host_transcript import extract_host_transcript_path

    caso = FIXTURES / "com_host"
    (uso,) = [
        f
        for f in extract_host_transcript_path(caso / "input" / "transcript.jsonl")
        if f.kind == "host.usage"
    ]
    (agente,) = [s for s in _spans(caso) if s["name"] == "invoke_agent"]
    attrs = _attrs(agente)
    assert int(attrs["gen_ai.usage.input_tokens"]) == uso.measures["input_tokens"]
    assert int(attrs["gen_ai.usage.output_tokens"]) == uso.measures["output_tokens"]
    assert attrs["gen_ai.provider.name"] == "anthropic"


def test_todo_motivo_de_recusa_aparece_ou_esta_na_unidade():
    """`sem_horario` e `transcript_sem_horario` sao cobertos em
    `tests/test_observability_otlp.py`: span de tool sem horario so aparece em
    linha estranha ao `record()`, e transcript sem horario nenhum nao e caso
    que o corpus de host tenha."""
    from sparkforge.observability.otlp import MOTIVOS

    vistos = set()
    for caso in _casos():
        vistos |= {
            r["reason"] for r in json.loads(_texto(caso / "expected" / "result.json"))["refused"]
        }
    assert vistos == set(MOTIVOS) - {"sem_horario", "transcript_sem_horario"}
