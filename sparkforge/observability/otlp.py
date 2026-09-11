"""Os spans de tool e o transcript do host em OTLP/JSON, com `gen_ai.*` e `mcp.*`.

O QUE ESTE MODULO FAZ, E SO ISSO. Recebe o que ja foi MEDIDO -- os spans que
`adapters/tools.py:call_tool` grava por chamada (`context_ledger.spans_of`) e,
quando houver, os facts `host.*` que `facts/host_transcript.py` extrai do
transcript do host -- e devolve `TracesData` e `MetricsData` no encoding JSON do
OTLP. Nao le arquivo, nao grava, nao chama rede: quem grava e a CLI
(`sparkforge telemetry export`), e quem envia e o Collector do operador, pelo
receiver `otlp_json_file` (antes `otlpjsonfile`).

AS FONTES, E O STATUS DELAS. Nomes de atributo e de span seguem
`open-telemetry/semantic-conventions-genai` no commit `SEMCONV_GENAI_COMMIT`
(`docs/gen-ai/gen-ai-spans.md`, `gen-ai-agent-spans.md`, `gen-ai-metrics.md` e
`mcp.md`), tudo em status Development. O encoding e o do OTLP 1.11.0: ids em
hex, inteiros de 64 bits como string decimal, enum como inteiro, chaves em
lowerCamelCase. Uma semconv em Development muda nome; o commit vai junto no
escopo de cada arquivo para dizer qual versao ele segue.

O QUE NUNCA SAI. Token do lado do SparkForge (regra 24: span de tool tem byte,
e byte sai como `sparkforge.payload_bytes`, nunca como `gen_ai.usage.*`, regra
22); custo (regra 25); conteudo de mensagem ou argumento de tool; e ligacao
entre o trace do host e o do SparkForge, porque nenhum contexto e propagado
entre os dois processos e parear por ordem ou nome seria heuristica.

RECUSA TEM NOME (regra 20). Span sem horario medido nao sai com horario
inventado, e span do `traces.db` que nao e de tool (o `AgentOpsTracker` grava
`task`, `routing`, `model` no mesmo banco) nao vira `execute_tool`: os dois vao
para `recusados`, com o motivo, e `exportados + recusados`
fecha com o total. O que falta sem derrubar span -- provider nao declarado,
modelo ausente ou ambiguo, usage ausente -- vai para `unresolved`.

DETERMINISMO. Os ids sao `sha256` do id local truncado (32 hex para trace, 16
para span), e os tempos sao aritmetica inteira. O mesmo run exportado duas
vezes da o mesmo arquivo, byte a byte, e o backend nao duplica o trace.
"""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SEMCONV_GENAI_COMMIT = "0c87594975195608dc91b3f702e250a7b240c151"
OTLP_VERSION = "1.11.0"
SCOPE_NAME = "sparkforge.observability.otlp"

KIND_INTERNAL = 1
KIND_SERVER = 2
STATUS_ERROR = 2
TEMPORALITY_DELTA = 1

MCP_DURATION_BOUNDS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120, 300)
AGENT_DURATION_BOUNDS = (0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2, 102.4, 204.8, 409.6)

MOTIVOS = ("sem_horario", "componente_nao_tool", "host_sem_horario", "transcript_sem_horario")

_TRANSPORTE_DE_REDE = {"stdio": "pipe", "http": "tcp"}
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_USAGE = (
    ("gen_ai.usage.input_tokens", "input_tokens"),
    ("gen_ai.usage.output_tokens", "output_tokens"),
    ("gen_ai.usage.cache_read.input_tokens", "cache_read_tokens"),
    ("gen_ai.usage.cache_write.input_tokens", "cache_creation_tokens"),
)


@dataclass(frozen=True)
class Projecao:
    """`traces` e `metrics` sao `None` quando nao ha nada daquele sinal."""

    traces: dict[str, Any] | None
    metrics: dict[str, Any] | None
    counts: dict[str, int]
    recusados: tuple[dict[str, str], ...]
    unresolved: tuple[dict[str, str], ...]


def id_hex(semente: str, tamanho: int) -> str:
    """Id OTLP deterministico. Todo zero e invalido no OTLP, e vira `...1`."""
    valor = hashlib.sha256(semente.encode("utf-8")).hexdigest()[:tamanho]
    return valor if valor.strip("0") else valor[:-1] + "1"


def nanos_de_epoch(instante: Any) -> int | None:
    """Segundos (float de `time.time()`) em nanossegundos, com resolucao de
    microssegundo: o `float` nao carrega mais que isso."""
    if isinstance(instante, bool) or not isinstance(instante, (int, float)):
        return None
    return int(round(instante * 1_000_000)) * 1000


def nanos_de_iso(texto: Any) -> int | None:
    """ISO 8601 do transcript em nanossegundos, por aritmetica inteira.

    `Z` vira `+00:00` porque o `fromisoformat` do Python 3.10 nao o aceita.
    Sem fuso, o instante nao e ancoravel, e sai `None` como texto invalido.
    """
    if not isinstance(texto, str) or not texto:
        return None
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instante.tzinfo is None:
        return None
    delta = instante - _EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def atributo(chave: str, valor: Any) -> dict[str, Any]:
    if isinstance(valor, bool):
        return {"key": chave, "value": {"boolValue": valor}}
    if isinstance(valor, int):
        return {"key": chave, "value": {"intValue": str(valor)}}
    if isinstance(valor, float):
        return {"key": chave, "value": {"doubleValue": valor}}
    return {"key": chave, "value": {"stringValue": str(valor)}}


def _atributos(pares: Iterable[tuple[str, Any]]) -> list[dict[str, Any]]:
    return [atributo(chave, valor) for chave, valor in pares if valor is not None and valor != ""]


def _escopo(extras: Sequence[tuple[str, Any]], versao: str) -> dict[str, Any]:
    return {
        "name": SCOPE_NAME,
        "version": versao,
        "attributes": _atributos(
            [("sparkforge.semconv_genai_commit", SEMCONV_GENAI_COMMIT), *extras]
        ),
    }


def _metadata(span: Mapping[str, Any]) -> dict[str, Any]:
    bruto = span.get("metadata")
    if isinstance(bruto, dict):
        return bruto
    texto = span.get("metadata_json")
    if isinstance(texto, str) and texto:
        try:
            lido = json.loads(texto)
        except json.JSONDecodeError:
            return {}
        return lido if isinstance(lido, dict) else {}
    return {}


def _ordenados(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(spans, key=lambda s: (int(s["startTimeUnixNano"]), s["spanId"]))


def _span_sparkforge(
    span: Mapping[str, Any], trace_id: str
) -> tuple[dict[str, Any], int, int, str, str | None] | None:
    inicio = nanos_de_epoch(span.get("start_time"))
    fim = nanos_de_epoch(span.get("end_time"))
    if inicio is None or fim is None:
        return None
    ferramenta = str(span.get("name") or "")
    meta = _metadata(span)
    pelo_mcp = meta.get("channel") == "mcp"
    desfecho = str(span.get("outcome") or "ok")
    erro = "tool_error" if desfecho != "ok" else None
    pares: list[tuple[str, Any]] = [
        ("gen_ai.operation.name", "execute_tool"),
        ("gen_ai.tool.name", ferramenta),
        ("gen_ai.tool.type", "function"),
    ]
    if pelo_mcp:
        pares += [
            ("mcp.method.name", "tools/call"),
            ("network.transport", _TRANSPORTE_DE_REDE.get(str(meta.get("transport") or ""))),
        ]
    item_count = span.get("item_count")
    pares += [
        ("error.type", erro),
        ("sparkforge.outcome", desfecho),
        ("sparkforge.payload_bytes", int(span.get("payload_bytes") or 0)),
        ("sparkforge.payload_basis", span.get("payload_basis") or None),
        ("sparkforge.detail_level", span.get("detail_level") or None),
        ("sparkforge.item_count", item_count if isinstance(item_count, int) else None),
    ]
    otlp: dict[str, Any] = {
        "traceId": trace_id,
        "spanId": id_hex("sparkforge:" + str(span.get("span_id")), 16),
        "name": f"tools/call {ferramenta}" if pelo_mcp else f"execute_tool {ferramenta}",
        "kind": KIND_SERVER if pelo_mcp else KIND_INTERNAL,
        "startTimeUnixNano": str(inicio),
        "endTimeUnixNano": str(fim),
        "attributes": _atributos(pares),
    }
    if erro:
        otlp["status"] = {"code": STATUS_ERROR, "message": desfecho}
    return otlp, inicio, fim, ferramenta, erro if pelo_mcp else "_nao_mcp"


def _por_kind(facts: Iterable[Mapping[str, Any]], kind: str) -> list[Mapping[str, Any]]:
    return [f for f in facts if f.get("kind") == kind]


def _histograma(
    atributos: list[dict[str, Any]],
    valores: Sequence[float],
    inicio: int,
    fim: int,
    fronteiras: Sequence[float],
) -> dict[str, Any]:
    baldes = [0] * (len(fronteiras) + 1)
    for valor in valores:
        baldes[bisect_left(fronteiras, valor)] += 1
    return {
        "attributes": atributos,
        "startTimeUnixNano": str(inicio),
        "timeUnixNano": str(fim),
        "count": str(len(valores)),
        "sum": sum(valores),
        "bucketCounts": [str(b) for b in baldes],
        "explicitBounds": list(fronteiras),
        "min": min(valores),
        "max": max(valores),
    }


def _metrica(nome: str, unidade: str, pontos: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": nome,
        "unit": unidade,
        "histogram": {"dataPoints": pontos, "aggregationTemporality": TEMPORALITY_DELTA},
    }


def _segundos(inicio: int, fim: int) -> float:
    return (fim - inicio) / 1_000_000_000


def projetar(
    spans: Sequence[Mapping[str, Any]],
    host_facts: Sequence[Mapping[str, Any]] | None,
    *,
    run_id: str,
    provider: str | None,
    versao: str,
) -> Projecao:
    """Spans do `traces.db` e facts `host.*` em `TracesData` e `MetricsData`."""
    recusados: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    resource_spans: list[dict[str, Any]] = []
    metricas_sf: list[dict[str, Any]] = []
    metricas_host: list[dict[str, Any]] = []

    trace_sf = id_hex("sparkforge:" + run_id, 32)
    otlp_sf: list[dict[str, Any]] = []
    grupos_mcp: dict[tuple[str, str | None], list[tuple[int, int]]] = {}
    for span in spans:
        componente = span.get("component_type")
        if componente not in (None, "", "tool"):
            recusados.append(
                {
                    "origin": "sparkforge",
                    "id": str(span.get("span_id")),
                    "reason": "componente_nao_tool",
                }
            )
            continue
        montado = _span_sparkforge(span, trace_sf)
        if montado is None:
            recusados.append(
                {"origin": "sparkforge", "id": str(span.get("span_id")), "reason": "sem_horario"}
            )
            continue
        otlp, inicio, fim, ferramenta, grupo = montado
        otlp_sf.append(otlp)
        if grupo != "_nao_mcp":
            grupos_mcp.setdefault((ferramenta, grupo), []).append((inicio, fim))

    if otlp_sf:
        resource_spans.append(
            {
                "resource": {
                    "attributes": _atributos(
                        [
                            ("service.name", "sparkforge"),
                            ("service.version", versao),
                            ("sparkforge.run_id", run_id),
                        ]
                    )
                },
                "scopeSpans": [
                    {
                        "scope": _escopo([("sparkforge.duration_scope", "call_tool")], versao),
                        "spans": _ordenados(otlp_sf),
                    }
                ],
            }
        )
    for (ferramenta, erro), intervalos in sorted(
        grupos_mcp.items(), key=lambda i: (i[0][0], i[0][1] or "")
    ):
        metricas_sf.append(
            _histograma(
                _atributos(
                    [
                        ("mcp.method.name", "tools/call"),
                        ("gen_ai.tool.name", ferramenta),
                        ("error.type", erro),
                    ]
                ),
                [_segundos(i, f) for i, f in intervalos],
                min(i for i, _ in intervalos),
                max(f for _, f in intervalos),
                MCP_DURATION_BOUNDS,
            )
        )

    host_tool_calls = 0
    host_agente = 0
    if host_facts is not None:
        transcripts = _por_kind(host_facts, "host.transcript")
        if not transcripts:
            motivos = sorted(
                {
                    str((f.get("attrs") or {}).get("reason"))
                    for f in _por_kind(host_facts, "host.transcript.unresolved")
                }
            )
            unresolved.append(
                {"field": "host_transcript", "reason": ",".join(motivos) or "sem_transcript"}
            )
        else:
            host_agente = 1
            chamadas = _por_kind(host_facts, "host.tool_call")
            host_tool_calls = len(chamadas)
            montado_host = _host(
                transcripts[0],
                chamadas,
                _por_kind(host_facts, "host.usage"),
                provider=provider,
                versao=versao,
                recusados=recusados,
                unresolved=unresolved,
                metricas=metricas_host,
            )
            if montado_host is not None:
                resource_spans.append(montado_host)

    resource_metrics: list[dict[str, Any]] = []
    if metricas_sf:
        resource_metrics.append(
            {
                "resource": {
                    "attributes": _atributos(
                        [
                            ("service.name", "sparkforge"),
                            ("service.version", versao),
                            ("sparkforge.run_id", run_id),
                        ]
                    )
                },
                "scopeMetrics": [
                    {
                        "scope": _escopo([("sparkforge.duration_scope", "call_tool")], versao),
                        "metrics": [_metrica("mcp.server.operation.duration", "s", metricas_sf)],
                    }
                ],
            }
        )
    if metricas_host:
        resource_metrics.append(metricas_host[0])

    exportados = sum(len(escopo["spans"]) for rs in resource_spans for escopo in rs["scopeSpans"])
    return Projecao(
        traces={"resourceSpans": resource_spans} if resource_spans else None,
        metrics={"resourceMetrics": resource_metrics} if resource_metrics else None,
        counts={
            "sparkforge_spans": len(spans),
            "host_agent": host_agente,
            "host_tool_calls": host_tool_calls,
            "exported": exportados,
            "refused": len(recusados),
        },
        recusados=tuple(recusados),
        unresolved=tuple(unresolved),
    )


def _host(
    transcript: Mapping[str, Any],
    chamadas: Sequence[Mapping[str, Any]],
    usos: Sequence[Mapping[str, Any]],
    *,
    provider: str | None,
    versao: str,
    recusados: list[dict[str, str]],
    unresolved: list[dict[str, str]],
    metricas: list[dict[str, Any]],
) -> dict[str, Any] | None:
    attrs = transcript.get("attrs") or {}
    semente = str(
        (transcript.get("provenance") or {}).get("artifact_sha256") or transcript.get("id")
    )
    trace_host = id_hex("host:" + semente, 32)
    agente_id = id_hex("host:" + semente + ":agent", 16)
    modelos = [m for m in attrs.get("models") or [] if isinstance(m, str)]
    modelo = modelos[0] if len(modelos) == 1 else None
    if provider is None:
        unresolved.append({"field": "gen_ai.provider.name", "reason": "provider_nao_declarado"})
    if not modelos:
        unresolved.append({"field": "gen_ai.request.model", "reason": "modelo_ausente"})
    elif len(modelos) > 1:
        unresolved.append({"field": "gen_ai.request.model", "reason": "modelos_multiplos"})
    uso = (usos[0].get("measures") or {}) if usos else None
    if uso is None:
        unresolved.append({"field": "gen_ai.usage", "reason": "usage_ausente"})

    spans: list[dict[str, Any]] = []
    inicio = nanos_de_iso(attrs.get("first_timestamp"))
    fim = nanos_de_iso(attrs.get("last_timestamp"))
    agente_exportado = inicio is not None and fim is not None
    if agente_exportado:
        pares: list[tuple[str, Any]] = [
            ("gen_ai.operation.name", "invoke_agent"),
            ("gen_ai.provider.name", provider),
            ("gen_ai.request.model", modelo),
        ]
        if uso is not None:
            pares += [(chave, int(uso.get(campo) or 0)) for chave, campo in _USAGE]
        spans.append(
            {
                "traceId": trace_host,
                "spanId": agente_id,
                "name": "invoke_agent",
                "kind": KIND_INTERNAL,
                "startTimeUnixNano": str(inicio),
                "endTimeUnixNano": str(fim),
                "attributes": _atributos(pares),
            }
        )
    else:
        recusados.append(
            {"origin": "host", "id": "invoke_agent", "reason": "transcript_sem_horario"}
        )

    for chamada in chamadas:
        c_attrs = chamada.get("attrs") or {}
        call_id = str(c_attrs.get("call_id") or chamada.get("id"))
        c_inicio = nanos_de_iso(c_attrs.get("started_at"))
        c_fim = nanos_de_iso(c_attrs.get("ended_at"))
        if c_inicio is None or c_fim is None:
            recusados.append({"origin": "host", "id": call_id, "reason": "host_sem_horario"})
            continue
        erro = "tool_error" if c_attrs.get("is_error") else None
        otlp: dict[str, Any] = {
            "traceId": trace_host,
            "spanId": id_hex("host:" + semente + ":" + call_id, 16),
        }
        if agente_exportado:
            otlp["parentSpanId"] = agente_id
        otlp.update(
            {
                "name": f"execute_tool {c_attrs.get('tool')}",
                "kind": KIND_INTERNAL,
                "startTimeUnixNano": str(c_inicio),
                "endTimeUnixNano": str(c_fim),
                "attributes": _atributos(
                    [
                        ("gen_ai.operation.name", "execute_tool"),
                        ("gen_ai.tool.name", c_attrs.get("tool")),
                        ("gen_ai.tool.call.id", c_attrs.get("call_id")),
                        ("error.type", erro),
                        ("sparkforge.host_channel", c_attrs.get("channel")),
                        (
                            "sparkforge.result_bytes",
                            (chamada.get("measures") or {}).get("result_bytes"),
                        ),
                    ]
                ),
            }
        )
        if erro:
            otlp["status"] = {"code": STATUS_ERROR}
        spans.append(otlp)

    if agente_exportado:
        comuns: list[tuple[str, Any]] = [
            ("gen_ai.operation.name", "invoke_agent"),
            ("gen_ai.provider.name", provider),
        ]
        pontos = [
            (
                "gen_ai.invoke_agent.duration",
                "s",
                [
                    _histograma(
                        _atributos(comuns),
                        [_segundos(inicio, fim)],
                        inicio,
                        fim,
                        AGENT_DURATION_BOUNDS,
                    )
                ],
            )
        ]
        if provider is not None and uso is not None:
            pontos.append(
                (
                    "gen_ai.client.token.usage",
                    "{token}",
                    [
                        _ponto_de_token(
                            [
                                *comuns,
                                ("gen_ai.token.type", tipo),
                                ("gen_ai.request.model", modelo),
                            ],
                            int(uso.get(campo) or 0),
                            int(uso.get("message_count") or 0),
                            inicio,
                            fim,
                        )
                        for tipo, campo in (("input", "input_tokens"), ("output", "output_tokens"))
                    ],
                )
            )
        metricas.append(
            {
                "resource": {"attributes": _recurso_host(transcript)},
                "scopeMetrics": [
                    {
                        "scope": _escopo([], versao),
                        "metrics": [_metrica(nome, unidade, p) for nome, unidade, p in pontos],
                    }
                ],
            }
        )

    if not spans:
        return None
    return {
        "resource": {"attributes": _recurso_host(transcript)},
        "scopeSpans": [{"scope": _escopo([], versao), "spans": _ordenados(spans)}],
    }


def _ponto_de_token(
    pares: Sequence[tuple[str, Any]], total: int, mensagens: int, inicio: int, fim: int
) -> dict[str, Any]:
    """Um bucket so, sem `explicitBounds` nem `min`/`max`: `host.usage` e somado
    por transcript, e a distribuicao por mensagem nao existe na fonte."""
    return {
        "attributes": _atributos(pares),
        "startTimeUnixNano": str(inicio),
        "timeUnixNano": str(fim),
        "count": str(mensagens),
        "sum": float(total),
        "bucketCounts": [str(mensagens)],
    }


def _recurso_host(transcript: Mapping[str, Any]) -> list[dict[str, Any]]:
    attrs = transcript.get("attrs") or {}
    versoes = [v for v in attrs.get("host_versions") or [] if isinstance(v, str)]
    return _atributos(
        [
            ("service.name", attrs.get("source")),
            ("service.version", versoes[0] if len(versoes) == 1 else None),
            ("sparkforge.host_transcript", (transcript.get("subject") or {}).get("file")),
        ]
    )


def linha_jsonl(obj: Mapping[str, Any] | None) -> str:
    """Uma linha JSON Lines, ou vazio quando nao ha sinal."""
    if obj is None:
        return ""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def linhas_jsonl(projecao: Projecao) -> tuple[str, str]:
    """O texto exato dos dois arquivos: uma linha por sinal, ou vazio."""
    return linha_jsonl(projecao.traces), linha_jsonl(projecao.metrics)
