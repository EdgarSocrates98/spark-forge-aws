# DESIGN: OpenTelemetry GenAI export

> Technical design for OTEL_GENAI_EXPORT

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | OTEL_GENAI_EXPORT |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_OTEL_GENAI_EXPORT.md](./DEFINE_OTEL_GENAI_EXPORT.md) |
| **Status** | ✅ Complete (Built) |

---

## Architecture Overview

```text
 call_tool (tools.py) ──record(channel)──> ContextLedger ──flush──> .sparkforge/traces.db
        ^                                       │
        │ partial(call_tool, channel="mcp",     │ spans_of(run_id)  (buffer + disco)
        │         transport=...)                v
   adapters/mcp.py                    ┌──────────────────────────────┐
                                      │ observability/otlp.py (pura) │
 transcript.jsonl ─extract_host_──>   │  projetar(spans, host_facts, │
   (--host-transcript)  transcript    │           provider, versao)  │
   facts host.* (com horario)  ────>  │   -> Projecao(traces,        │
                                      │      metrics, exportados,    │
                                      │      recusados, unresolved)  │
                                      └──────────────┬───────────────┘
                                                     │
                  ┌──────────────────────────────────┼─────────────────────┐
                  v                                  v                     v
   CLI `telemetry export` grava            tool MCP READ_ONLY      golden fixtures/otel
   .sparkforge/telemetry/<run>.traces.jsonl  (devolve, nao grava)   + Collector no CI
   .sparkforge/telemetry/<run>.metrics.jsonl                        (otlpjsonfile -> file)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/observability/otlp.py` | Projecao pura de spans e facts `host.*` em `TracesData`/`MetricsData` (dicts prontos para `json.dumps`) | Python stdlib (`hashlib`, `datetime`) |
| `context_ledger.record(channel=, transport=)` | Grava o canal medido em `metadata` do span, dentro do try/except existente | — |
| `tools.call_tool(..., channel="", transport="")` | Repassa o canal ao ledger; nenhum outro efeito | — |
| `adapters/mcp.py` | Passa `functools.partial(call_tool, channel="mcp", transport=transport)` a `envelope_da_chamada` | — |
| `facts/host_transcript.py` | `host.transcript.attrs.first_timestamp/last_timestamp`; `host.tool_call.attrs.call_id/started_at/ended_at` | Extrator sobe para `host_transcript@0.2.0` |
| `_core.telemetry_export(...)` | Le `shared_ledger().spans_of`, extrai o transcript, chama `projetar`, valida `run_id` e `provider` | — |
| `cli.py` `telemetry export` | Grava os dois arquivos com nome fixo sob `--repo` e imprime o resumo | argparse |
| Tool `sparkforge_telemetry_export` | `READ_ONLY`; devolve a projecao e as contagens | — |
| `fixtures/otel/` + `tests/test_fixtures_golden_otel.py` | 4 casos, golden byte a byte, teste de forma OTLP/JSON | pytest |
| Job `otel-collector` no `ci.yml` | `otelcol-contrib:0.160.0` le os goldens e o exporter `file` devolve | GitHub Actions + docker |
| `scripts/check_otel_collector.py` | Compara a saida do Collector com os goldens (spans, nomes, atributos-chave) | Python stdlib |
| `docs/opentelemetry.md` | Verbo, config do Collector, o que nunca sai, fontes e status | — |

---

## Key Decisions

### Decision 1: dois arquivos, um por sinal

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-002. O `file.go` do `otlpjsonfilereceiver` le cada linha com o unmarshaler do pipeline dele (`ptrace.JSONUnmarshaler` no de traces, `pmetric` no de metrics). Uma linha `MetricsData` no pipeline de traces vira erro contado como recusa (`EndTracesOp(..., err)`), ou traces vazio descartado.

**Choice:** `.sparkforge/telemetry/<run_id>.traces.jsonl` e `.sparkforge/telemetry/<run_id>.metrics.jsonl`. Cada pipeline do Collector aponta o `include` para o seu arquivo.

**Rationale:** nenhuma recusa espuria na observabilidade do proprio Collector, e o operador pode ligar so traces.

**Alternatives Rejected:**
1. Arquivo misto: o spec do file exporter permite, mas o receiver conta a linha do outro sinal como falha.
2. So traces: G11 pede metricas.

**Consequences:**
- Dois nomes fixos em vez de um.
- O `metrics.jsonl` existe mesmo vazio (0 linhas), para o `include` do operador nunca apontar para arquivo ausente.

---

### Decision 2: provider declarado, nunca deduzido

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-003. `gen_ai.provider.name` e `Required` no span `invoke_agent` e na metrica `gen_ai.client.token.usage`. O transcript do Claude Code guarda `model`, mas nao o provider. O mesmo host roda sobre a API da Anthropic, o Bedrock ou o Vertex, e o nome do modelo nao separa os tres com seguranca.

**Choice:** `--provider <nome>` opcional, validado por `^[a-z0-9_.]{1,64}$`. Sem ele:
- o span `invoke_agent` sai sem o atributo;
- `result.unresolved` lista `gen_ai.provider.name` com o motivo `provider_nao_declarado`;
- a metrica `gen_ai.client.token.usage` nao sai, porque o atributo e obrigatorio nela.

**Rationale:** mesmo padrao do SLA declarado em `workload.yaml`. Quem sabe o provider e o operador; deduzir pelo nome do modelo seria heuristica vestida de medida (regra 20).

**Alternatives Rejected:**
1. `anthropic` fixo para `source=claude_code`: errado sob Bedrock e Vertex.
2. Mapear pelo prefixo do modelo (`us.anthropic.` para Bedrock): nao separa a API direta do Vertex.

**Consequences:**
- Sem `--provider`, o span `invoke_agent` nao cumpre um `Required` da semconv. O documento diz isso, e o `unresolved` nomeia a lacuna.

---

### Decision 3: span do SparkForge por canal medido

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** `mcp.md` define o span de servidor MCP (nome `{mcp.method.name} {gen_ai.tool.name}`, kind `SERVER`, `mcp.method.name` obrigatorio, e `gen_ai.operation.name=execute_tool` recomendado para o consumidor tratar como tool call). `gen-ai-spans.md` define `execute_tool {gen_ai.tool.name}`, kind `INTERNAL`.

**Choice:**

| Canal medido | Nome do span | Kind | Atributos alem dos comuns |
|---|---|---|---|
| `mcp` | `tools/call {tool}` | `SERVER` (2) | `mcp.method.name=tools/call`, `network.transport` (`pipe` para stdio, `tcp` para http) |
| ausente | `execute_tool {tool}` | `INTERNAL` (1) | — |

Os atributos comuns sao `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.type=function`, `sparkforge.outcome`, `sparkforge.payload_bytes`, `sparkforge.payload_basis`, e `sparkforge.detail_level` e `sparkforge.item_count` quando houver. Com `outcome` diferente de `ok`, entram `status.code=2` (ERROR) e `error.type=tool_error`; a nota do `mcp.md` manda `tool_error` para `CallToolResult.isError`, que e o que o envelope devolve nesses casos.

**Rationale:** uma chamada vinda do MCP e, pela semconv, um span de servidor MCP. A mesma chamada sem canal medido e so execucao de tool.

**Alternatives Rejected:**
1. Sempre `execute_tool`: perde o atributo que o consumidor MCP procura.
2. Sempre `tools/call`: afirma canal sem medida.

---

### Decision 4: ids e tempos deterministicos

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:**
- **Trace do SparkForge:** `traceId = sha256("sparkforge:" + run_id)[:32]` e `spanId = sha256("sparkforge:" + span_id)[:16]`.
- **Trace do host:** `traceId = sha256("host:" + artifact_sha256)[:32]`. O `invoke_agent` e `sha256("host:" + artifact_sha256 + ":agent")[:16]`, e cada tool call e `sha256("host:" + artifact_sha256 + ":" + call_id)[:16]`.
- Um id que der tudo zero (probabilidade desprezivel, mas invalido no OTLP) troca o ultimo hex para `1`.
- **Tempo do SparkForge:** `int(round(t * 1_000_000)) * 1000`. Resolucao de microssegundo, porque o `float` de `time.time()` nao carrega mais que isso.
- **Tempo do host:** o ISO 8601 do transcript, com `Z` trocado por `+00:00` (o `fromisoformat` do Python 3.10 nao aceita `Z`), convertido em nanossegundos por aritmetica inteira sobre `timedelta`, sem `float`.
- **Ordem:** spans ordenados por `(startTimeUnixNano, spanId)`. O `get_trace` do store nao tem `ORDER BY`.

**Rationale:** o golden fica estavel. Exportar o mesmo run duas vezes nao duplica o trace no backend.

---

### Decision 5: horario no extrator, sem mudar id de fact

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** `Fact.id` e `sha1(kind + subject + measures)`. `attrs` nao entra no id.

**Choice:** os horarios e o `call_id` entram em `attrs` como strings do transcript: `first_timestamp`, `last_timestamp`, `call_id`, `started_at` e `ended_at`. Uma linha sem `timestamp` deixa o campo ausente. O extrator sobe para `host_transcript@0.2.0`.

**Rationale:** nenhum id muda. Os 21 goldens mudam so em `attrs` e na versao do extrator em `provenance`, e os gabaritos das evals, que citam ids, ficam intactos.

---

### Decision 6: `--host-transcript`, como no `economy report`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o DEFINE falava em `--facts <host.json>`. Nao existe verbo da CLI que produza facts `host.*`: `economy report` ja recebe o transcript cru por `--host-transcript` e extrai por dentro.

**Choice:** `--host-transcript <path>`, extraido por `extract_host_transcript_path`. O DEFINE G1 e os AT foram ajustados para isso.

**Rationale:** o mesmo operador usa os dois verbos com a mesma flag.

---

### Decision 7: metricas so onde ha semconv e medida

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:**

| Metrica | Fonte | Forma |
|---|---|---|
| `mcp.server.operation.duration` (s) | Spans com canal `mcp` | Histograma com as fronteiras do `mcp.md` (`0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120, 300`) e contagens reais por bucket; atributos `mcp.method.name`, `gen_ai.tool.name` e `error.type` quando houver; um ponto por combinacao de atributos |
| `gen_ai.invoke_agent.duration` (s) | `invoke_agent` do host | Um ponto, `count=1`, com as fronteiras do `gen-ai-metrics.md` |
| `gen_ai.client.token.usage` ({token}) | `host.usage`, so com `--provider` | Um ponto por `gen_ai.token.type` (`input`, `output`), `count = message_count`, `sum` = total, **sem** `explicitBounds` (um bucket so) e sem `min`/`max`; `gen_ai.operation.name=invoke_agent` |

Todos os pontos usam `aggregationTemporality` DELTA (1), com `startTimeUnixNano`/`timeUnixNano` do primeiro e do ultimo span da fonte.

**Rationale:** cada numero e contagem ou soma de medida real. A distribuicao por mensagem nao existe no `host.usage`, e por isso nao ha bucket inventado.

**Alternatives Rejected:**
1. `gen_ai.client.operation.duration` para tool sem canal: e metrica de operacao de cliente GenAI, e o SparkForge nao e cliente de modelo.

**Consequences:**
- Nota no documento: a duracao do span MCP cobre `call_tool`, e nao validacao e serializacao do envelope. Fica menor que o intervalo "recebido ate respondido" da semconv, e `sparkforge.duration_scope=call_tool` vai no atributo do escopo.
- A-005 (histograma de bucket unico) e provada pelo Collector (SC7).

---

### Decision 8: recusa nomeada e contagem que fecha

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `Projecao.recusados` e uma tupla de `{origem, id, motivo}`:

| Origem | Motivo | Quando |
|---|---|---|
| `sparkforge` | `sem_horario` | Span com `start_time` ou `end_time` ausente |
| `host` | `host_sem_horario` | Tool call sem `started_at` ou `ended_at` |
| `host` | `transcript_sem_horario` | Transcript sem `first_timestamp`/`last_timestamp`: o `invoke_agent` nao sai, e as tool calls saem sem pai |

Mais duas regras:
- `result.counts` mostra `spans_run`, `host_tool_calls`, `exportados` e `recusados`, e o teste cobra `exportados + recusados = spans_run + host_tool_calls + (1 se houver transcript)`.
- `unresolved` lista o que faltou sem derrubar span: `gen_ai.provider.name` e `gen_ai.request.model` (ausente, ou mais de um modelo no transcript).

---

### Decision 9: `run_id` validado antes de virar nome de arquivo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** o `run_id` vem do argv, ou do `SPARKFORGE_RUN_ID` de quem gravou, e vira parte do nome do arquivo.

**Choice:**
- `run_id` precisa casar `^[A-Za-z0-9_.-]{1,64}$` e nao comecar com `.`; senao, exit 2.
- O destino e `Path(repo) / ".sparkforge" / "telemetry" / f"{run_id}.traces.jsonl"`, e o teste confere que ele resolve dentro de `--repo`.
- Um run sem span nenhum (buffer e disco vazios) sai com exit 2: "run sem spans".

**Rationale:** nenhum caminho de escrita vem livre do argv (licao do Snyk).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/host_transcript.py` | Modify | Horarios e `call_id` em `attrs`; `@0.2.0` | @agentspec:python:python-developer | None |
| 2 | `fixtures/host_transcript/*/expected/*` | Regenerate | 21 goldens com os campos novos | (general) | 1 |
| 3 | `sparkforge/observability/context_ledger.py` | Modify | `record(..., channel="", transport="")` grava em `metadata` | @agentspec:python:python-developer | None |
| 4 | `sparkforge/adapters/tools.py` | Modify | `call_tool(..., channel="", transport="")`; schema e handler da tool nova | @agentspec:python:python-developer | 3, 6 |
| 5 | `sparkforge/adapters/mcp.py` | Modify | `partial(call_tool, channel="mcp", transport=transport)` | (general) | 4 |
| 6 | `sparkforge/observability/otlp.py` | Create | `projetar(...) -> Projecao`, helpers de id, tempo e atributo | @agentspec:python:python-developer | 1 |
| 7 | `sparkforge/adapters/_core.py` | Modify | `telemetry_export(...)` e `telemetry_export_textos(...)` (as linhas JSON exatas, usadas pela CLI e pelo regen) | (general) | 6 |
| 8 | `sparkforge/adapters/cli.py` | Modify | `telemetry export --run-id --host-transcript --provider --repo` | (general) | 7 |
| 9 | Registros de tool nova | Modify | `tests/test_adapters_tools.py`, `tests/test_harness_authorization.py`, `parity.yaml`, `manifest.json`, executor que a declara (`sf-context-engineer` ou `sf-cost-reviewer`) + espelhos, `NOVAS_DEPOIS_DO_GOLDEN`, `test_mcp_modern_era` | (general) | 4 |
| 10 | `tests/test_observability_otlp.py` | Create | Unidade: ids, tempo, canal, recusas, provider, metricas, forma OTLP | @agentspec:test:test-generator | 6 |
| 11 | `tests/test_context_ledger.py`, `tests/test_adapters_mcp*.py` | Modify | Canal em `metadata`; `record` falhando nao derruba (SC8); `mcp.py` passa o canal | @agentspec:test:test-generator | 3, 5 |
| 12 | `fixtures/otel/{sparkforge_ok,sparkforge_erro,com_host,host_sem_usage}/` | Create | `input/spans.json`, `input/transcript.jsonl` (quando houver), `meta.yaml`, `expected/{traces.jsonl,metrics.jsonl,result.json}` | (general) | 6, 7 |
| 13 | `scripts/regen_fixtures.py` | Modify | `saidas_otel(caso)` com a mesma funcao da CLI | (general) | 7 |
| 14 | `tests/test_fixtures_golden_otel.py` | Create | Golden, forma OTLP, soma que fecha, CLI de verdade numa copia, 0 `gen_ai.usage` sem host | (general) | 12, 13 |
| 15 | `scripts/check_otel_collector.py` + job `otel-collector` no `.github/workflows/ci.yml` | Create/Modify | Prova por consumidor real | @agentspec:cloud:ci-cd-specialist | 12 |
| 16 | `docs/opentelemetry.md`, `docs/superpowers/STATUS.md`, `CLAUDE.md` (tabela de verbos) | Create/Modify | Guia e numeros medidos | (general) | all |
| 17 | `docs/surface.lock.json`, `docs/claims.lock.json` + docs auditados | Modify (se o gate acusar) | Gates | (general) | all |
| 18 | `.claude/sdd/reports/BUILD_REPORT_OTEL_GENAI_EXPORT.md` | Create | Relatorio | (general) | all |

**Total Files:** 18 entradas.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @agentspec:python:python-developer | 1, 3, 4, 6 | Funcoes puras e mudancas pequenas em modulos com historia (ledger) |
| @agentspec:test:test-generator | 10, 11 | Pares positivo/negativo por ramo |
| @agentspec:cloud:ci-cd-specialist | 15 | Job com container e volume |
| (general) | 2, 5, 7–9, 12–14, 16–18 | Registros e fixtures deste repositorio |

**Agent Discovery:**
- Scanned: agentes do plugin agentspec e os da sessao.
- Matched by: tipo de arquivo e palavra-chave.
- Como nos PRs #50 e #51, o build pode ficar direto: cada passo depende de medida do anterior.

---

## Code Patterns

### Pattern 1: ids e tempo (`otlp.py`)

```python
import hashlib
from datetime import datetime, timezone

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _id_hex(semente: str, tamanho: int) -> str:
    valor = hashlib.sha256(semente.encode("utf-8")).hexdigest()[:tamanho]
    return valor if valor.strip("0") else valor[:-1] + "1"


def _nanos_de_epoch(t: float) -> str:
    return str(int(round(t * 1_000_000)) * 1000)


def _nanos_de_iso(texto: str) -> str | None:
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instante.tzinfo is None:
        return None
    delta = instante - _EPOCH
    return str((delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000)
```

### Pattern 2: atributo OTLP/JSON

```python
def _atributo(chave: str, valor: object) -> dict[str, object]:
    if isinstance(valor, bool):
        return {"key": chave, "value": {"boolValue": valor}}
    if isinstance(valor, int):
        return {"key": chave, "value": {"intValue": str(valor)}}
    if isinstance(valor, float):
        return {"key": chave, "value": {"doubleValue": valor}}
    return {"key": chave, "value": {"stringValue": str(valor)}}
```

### Pattern 3: canal no ledger (regra 27)

```python
def record(self, *, name, resultado, detail_level, outcome, start_time,
           channel: str = "", transport: str = "") -> None:
    if self._run_start is None:
        self._run_start = start_time
    try:
        metadata = {k: v for k, v in (("channel", channel), ("transport", transport)) if v}
        span = TraceSpan(..., metadata=metadata)
        self._buffer.append(span)
    except Exception:  # noqa: BLE001,S110 -- medir nunca derruba a chamada
        pass
```

### Pattern 4: linha JSON deterministica

```python
linha = json.dumps(traces_data, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
```

A ordem das chaves e fixada pela construcao dos dicts (ordem do proto: `resource`, `scopeSpans`, `scope`, `spans`, `traceId`, `spanId`, `parentSpanId`, `name`, `kind`, `startTimeUnixNano`, `endTimeUnixNano`, `attributes`, `status`), e nao por `sort_keys`.

---

## Data Flow

```text
1. CLI/tool recebe run_id, host_transcript?, provider?, repo
2. valida run_id (regex) e provider (regex); run sem span -> exit 2
3. spans = shared_ledger().spans_of(run_id)   (buffer + disco; metadata_json -> dict)
4. host = extract_host_transcript_path(p) se houver
5. projetar(spans, host, provider, versao) -> Projecao
6. CLI: grava traces.jsonl e metrics.jsonl (nome fixo) e imprime result
   tool: devolve {traces, metrics, counts, refused, unresolved}
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| OTLP Collector (`otelcol-contrib` 0.160.0) | Arquivo JSON Lines lido por `otlpjsonfile` | Nenhuma: arquivo local |
| CI | Job `otel-collector` com `docker run` e volume | Nenhuma |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Ids, tempo (Z, offset, invalido, sem fuso), canal, `outcome`, recusas, provider presente/ausente, modelo unico/multiplo, histogramas, forma | `tests/test_observability_otlp.py` | pytest | Todos os ramos de `otlp.py` |
| Unit | Canal em `metadata`, `record` falhando, disco e buffer dando a mesma projecao | `tests/test_context_ledger.py` | pytest | SC8 e a normalizacao de `metadata_json` |
| Golden | 4 casos byte a byte, forma OTLP, soma que fecha, CLI real numa copia do repo, 0 `gen_ai.usage` sem host | `tests/test_fixtures_golden_otel.py` | pytest | AT-001 a AT-007, AT-009, AT-011 |
| Golden | 21 transcripts com os campos novos | `tests/test_fixtures_golden_host_transcript.py` | pytest | AT-008, SC5 |
| Contract | Tool nova valida contra o proprio schema e nao grava | `tests/test_adapters_tools.py` | pytest | AT-010 |
| E2E | Collector real | job `otel-collector` + `scripts/check_otel_collector.py` | GitHub Actions | AT-013, SC7 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `run_id` fora do padrao, `provider` fora do padrao | Exit 2 com o padrao aceito na mensagem | No |
| Run sem spans | Exit 2: "run sem spans; confira `SPARKFORGE_RUN_ID` de quem gravou" | No |
| Transcript ilegivel ou de outro formato | O extrator ja devolve `host.transcript.unresolved`; o export sai sem trace do host e com `unresolved: host_transcript` | No |
| Span com `metadata_json` invalido | Tratado como sem canal | No |
| Timestamp ISO invalido ou sem fuso | Campo tratado como ausente, e o span vira recusa | No |
| Falha ao gravar o canal no `record()` | Engolida como hoje; a chamada devolve o resultado | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--provider` | str | ausente | Provider do host, declarado pelo operador |
| `SPARKFORGE_RUN_ID` | env | gerado | Ja existe; e o que liga o run gravado ao export |

---

## Security Considerations

- Nome de arquivo so a partir de `run_id` validado; destino confinado a `--repo`.
- Nenhum conteudo de mensagem ou argumento de tool entra no arquivo (os `gen_ai.tool.call.arguments`/`result` sao opt-in e ficam fora).
- Nenhuma rede nem dependencia nova no pacote. O container do Collector existe so no CI.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Resumo JSON no stdout, com contagens e caminhos gravados |
| Metrics | O proprio arquivo de metricas |
| Tracing | O proprio arquivo de traces |

---

## Build Order

| Step | Tasks | Gate para seguir |
|------|-------|------------------|
| B1 | Itens 1–2 | 21 goldens com diff so em `attrs` e na versao do extrator |
| B2 | Itens 3–5 e 11 | Canal gravado; SC8 verde; paridade MCP intacta |
| B3 | Itens 6 e 10 | Unidade verde |
| B4 | Itens 7–9 | Tool valida contra o proprio schema; registros verdes |
| B5 | Itens 12–14 | 4 goldens verdes, CLI real |
| B6 | Itens 15–17; suite, gates, Snyk | Tudo verde localmente |
| B7 | Commit, push, PR; job `otel-collector` no PR | SC7 |
| B8 | Item 18 e statuses | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versao inicial; A-002, A-003 e A-006 decididas; `--facts` do DEFINE vira `--host-transcript` (Decision 6) |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_OTEL_GENAI_EXPORT.md`
