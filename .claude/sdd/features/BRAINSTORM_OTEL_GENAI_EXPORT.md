# BRAINSTORM: OpenTelemetry GenAI export

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | OTEL_GENAI_EXPORT |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente §13 de `prompt_new_evo.md`, "OpenTelemetry GenAI nativo", que e o item 2 do P0 no roadmap (§31) e o item 5 do TOP 10 (§33). A proposta: um trace por case com `agent.invoke`, `model.invoke`, `tool.execute` e os atributos `gen_ai.*`, exportavel para CloudWatch, Grafana, Datadog, Langfuse, Jaeger ou um OTLP Collector, sem acoplar o core. Branch `feat/otel-genai`, a partir da `main` (ja com #48, #49 e #50).

**Context Gathered:**
- Nenhum arquivo em `sparkforge/` cita `opentelemetry`, `otel` ou `gen_ai`.
- O que ja e medido:
  - `adapters/tools.py:call_tool` e o despacho unico, e cada chamada vira um `TraceSpan` gravado por `observability/context_ledger.py` em `.sparkforge/traces.db`: nome da tool, inicio e fim, `payload_bytes` com `payload_basis`, `detail_level`, `item_count` e `outcome` (`ok`, `error`, `unauthorized`).
  - Token e custo ficam vazios de proposito (regras 22, 24 e 25).
  - Os ids sao `run_<12 hex>` e `span_<8 hex>`, fora do formato OTel (trace de 16 bytes, span de 8).
  - O span tem `metadata` (coluna `metadata_json`), que hoje fica vazio.
- `call_tool` **nao sabe o canal**: nada registra se a chamada veio do servidor MCP.
- O extrator `facts/host_transcript.py` produz `host.transcript` (modelos e versoes do host), `host.tool_call` (tool, canal, verbo, `result_bytes`, `is_error`) e `host.usage` (tokens de entrada, saida, cache lido e cache escrito, **somados** por transcript). Nenhum deles guarda horario.
- **Medido:** o transcript `fixtures/host_transcript/correct_mcp/input/q-mcp.jsonl` tem `timestamp` em 7 de 7 linhas. O horario existe na fonte; o extrator e que o descarta.
- **Conferido na fonte T1:**
  - As convencoes GenAI se mudaram para `open-telemetry/semantic-conventions-genai` (commit `0c87594975195608dc91b3f702e250a7b240c151`, 2026-09-11). Tudo ali esta em status **Development**.
  - Pelo `docs/gen-ai/gen-ai-spans.md` desse repositorio:
    - span de tool: nome `execute_tool {gen_ai.tool.name}`, `gen_ai.operation.name` = `execute_tool`, com `gen_ai.tool.name`, `gen_ai.tool.call.id` e `gen_ai.tool.type`;
    - span de agente: `gen_ai.operation.name` = `invoke_agent`;
    - uso: `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens` e `gen_ai.usage.cache_write.input_tokens`;
    - modelo e provider: `gen_ai.request.model` e `gen_ai.provider.name`.
  - `docs/gen-ai/mcp.md`: `mcp.method.name` = `tools/call`, para o consumidor tratar a chamada MCP como qualquer tool call.
  - OTLP 1.11.0, encoding JSON:
    - `traceId` e `spanId` em hex;
    - inteiros de 64 bits como string decimal;
    - enum so como inteiro;
    - chaves em lowerCamelCase.
  - File exporter do OTLP (status Development): JSON Lines, uma `TracesData`, `MetricsData` ou `LogsData` por linha.
  - Collector contrib: receiver `otlpjsonfile` (alpha para traces), com `include` e `start_at`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/observability/otlp.py` para a projecao; `adapters/_core.py`, `adapters/cli.py` e `adapters/tools.py` para o verbo e a tool; `facts/host_transcript.py` para os horarios; `adapters/mcp.py` e `context_ledger.py` para o canal; `fixtures/otel/`; `docs/` | Verbo que compoe sobre o que ja foi medido, como `economy report` e `report github` |
| Relevant KB Domains | Observability (OpenTelemetry, OTLP, semconv GenAI), testing (golden), CI/CD (GitHub Actions) | Golden por fixture e prova por consumidor real |
| IaC Patterns | `.github/workflows/ci.yml` | Um job novo com `otelcol-contrib` fixado por versao |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual frente do `prompt_new_evo.md`? | OTel GenAI | §13 |
| 2 | Como a telemetria sai do SparkForge? | Arquivo OTLP/JSON | Nenhuma dependencia nova e nenhuma rede no pacote; quem envia e o Collector do operador |
| 3 | O que entra no trace? | Tool spans + host | Os spans do `traces.db` viram `execute_tool`; o transcript do host vira `invoke_agent` com tokens e modelo. Sem transcript, nenhum token |
| 4 | Como provar que o arquivo e OTLP? | Golden + Collector real | Golden byte a byte e um job de CI em que o `otelcol-contrib` le o arquivo |
| 5 | Amostras? | Gerar + transcripts | `traces.db` montado por tools reais sobre fixtures existentes, com relogio e uuid injetados; transcripts de `fixtures/host_transcript` |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files (lado SparkForge) | `traces.db` gerado nos testes por chamadas reais de `call_tool` sobre fixtures existentes | 3 casos | Relogio e uuid injetados para o golden ficar estavel |
| Input files (lado host) | `fixtures/host_transcript/correct_mcp`, `no_usage`, `run_full` | 21 casos existentes | `timestamp` presente em todas as linhas medidas |
| Output examples | `fixtures/otel/*/expected/` (a criar): o JSON Lines exportado e `result.json` | 4 casos | Golden |
| Ground truth | Spec OTLP 1.11.0 (encoding JSON) e `semantic-conventions-genai@0c87594` | 2 fontes | Versionadas com URL e commit |
| Related code | `observability/{tracer,context_ledger,store}.py`, `facts/host_transcript.py`, `adapters/_core.py::economy_report` | — | O que ja mede e o que ja le |

**How samples will be used:**

- Os casos de `fixtures/otel/` fixam a saida byte a byte.
- Os 21 transcripts existentes provam que o extrator ganha horario sem mudar nada alem dos campos novos.
- O Collector real prova que um consumidor aceita o arquivo.

---

## Approaches Explored

### Approach A: projecao pura sobre o que ja esta gravado ⭐ Recommended

**Description:** `sparkforge/observability/otlp.py` e uma funcao pura: spans do `traces.db` por `run_id`, mais facts `host.*` opcionais, viram `TracesData` e `MetricsData`. O verbo `sparkforge telemetry export` grava em JSON Lines, e a tool MCP devolve o mesmo sem gravar.
- **Ids deterministicos:** `traceId = sha256(run_id)[:32]` e `spanId = sha256(span_id)[:16]`. O mesmo run exportado duas vezes sai byte a byte igual.
- **Lado host:** trace proprio.
- **Correlacao:** nenhuma ligacao entre `host.tool_call` e o span do SparkForge.

**Pros:**
- Nao toca o caminho quente de `call_tool`, o schema do SQLite nem o `economy report`.
- Nenhuma dependencia nova.
- Golden simples e estavel.

**Cons:**
- O export e um passo a mais.
- O span `invoke_agent` pede horario que o extrator do host hoje descarta.

**Why Recommended:** e o mesmo padrao de `economy report` e `report github` (compor sobre o que ja foi medido, sem ler artefato), e a unica forma em que nenhum numero e inventado. Confianca 0,85: ha padrao no codigo, e a semconv esta em Development.

---

### Approach B: gravar em formato OTel na origem

**Description:** o tracer passa a gerar ids OTel e atributos `gen_ai.*` no proprio `record()`, com migracao do `traces.db`. O export vira quase uma copia.

**Pros:**
- Um formato so.

**Cons:**
- Mexe no caminho quente de toda tool e no schema, cuja migracao ja tem historia delicada em `store.py`.
- Prende o armazenamento a uma semconv em Development.

**Why not:** o risco cai no produto (regra 27) por um ganho de formato.

---

### Approach C: SDK `opentelemetry` com exporter de arquivo

**Description:** usar o SDK oficial para montar e serializar os spans.

**Cons:**
- Dependencia nova no runtime.
- Ids aleatorios, e golden instavel.
- O exporter de arquivo do SDK Python nao e estavel.

**Why not:** paga uma dependencia para serializar um JSON que o spec descreve inteiro.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11 |
| **Reasoning** | Nada inventado, nenhuma dependencia, sem tocar o caminho quente |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Verbo `sparkforge telemetry export --run-id <id> [--facts <host.json> ...]`, que compoe sobre `traces.db` e facts | Nao le artefato; o `traces.db` ja e o que `economy report` le | Instrumentar com o SDK OTel |
| 2 | Saida em JSON Lines com `TracesData` e `MetricsData`, com nome fixo sob `.sparkforge/telemetry/`, dentro de `--repo` | Nada do argv vira caminho de escrita (licao do Snyk no eval harness). Se a mesma linha pode misturar `TracesData` e `MetricsData` para o `otlpjsonfile`, ou se sao dois arquivos, o Design decide com o Collector | `--out <caminho>` |
| 3 | Ids por `sha256` do id local, truncado a 16 e 8 bytes | Deterministico; o export repetido nao duplica trace no backend | Ids aleatorios |
| 4 | Span SparkForge: `execute_tool {tool}`, `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.type=function` | Semconv GenAI | Nome proprio de span |
| 5 | `mcp.method.name=tools/call` so quando o span registrou o canal MCP. `adapters/mcp.py` passa o canal ao `call_tool`, e o `record()` o grava em `metadata`, sem migrar schema | Afirmar canal sem medida seria inventar | Assumir MCP para todo span |
| 6 | `payload_bytes` sai como `sparkforge.payload_bytes`, com `sparkforge.payload_basis` ao lado | Regra 22: byte nao e token | `gen_ai.usage.*` com bytes |
| 7 | `outcome` error ou unauthorized vira status ERROR, com `sparkforge.outcome` | O consumidor distingue "falhou" de "nao pode" | So status ERROR |
| 8 | Span `invoke_agent` do host com `gen_ai.request.model` e os quatro `gen_ai.usage.*`, e inicio e fim do primeiro e do ultimo `timestamp` do transcript | Token so com fonte (regra 24) | Tokens estimados |
| 9 | Tool calls do host viram spans filhos `execute_tool`, com horario da linha do `tool_use` e da linha do `tool_result` | Horario medido na fonte | Spans sem duracao |
| 10 | Span sem horario medido nao sai: vira recusa nomeada na contagem do `result.json`, e `exportados + recusados = total` | Regra 20; mesma disciplina do `report github` | Horario zero ou inventado |
| 11 | Metricas: `gen_ai.client.token.usage` (so do host, com `gen_ai.token.type`), `gen_ai.client.operation.duration` e `mcp.server.operation.duration` | Semconv GenAI e MCP | So spans |
| 12 | Tool MCP `sparkforge_telemetry_export`, `READ_ONLY`, que devolve o mesmo conteudo sem gravar | Gravar e da CLI; a tool so le | Tool `LOCAL_MUTATION` |
| 13 | Commit da semconv, versao do OTLP e status Development/alpha publicados no documento, ao lado do verbo | Afirmar "padrao OTel" sem dizer que e Development seria vender estabilidade que a fonte nao da | Omitir o status |
| 14 | Prova por consumidor: job de CI com `otelcol-contrib` em versao fixa, `otlpjsonfile` (`start_at: beginning`) e exporter `file`, conferindo spans e atributos na saida | Equivalente do `sarif-upload` | So golden |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Exporter OTLP ao vivo (HTTP ou gRPC) dentro do pacote | Rede e dependencia no caminho quente; o Collector do operador faz o envio a partir do arquivo | Yes, como extra opcional |
| Gravar em formato OTel na origem (abordagem B) | Risco no caminho quente e no schema | Yes |
| Spans de pipeline (`evidence.collect`, `rule.judge`, `debate.round`, `decision.publish`) | Instrumenta muitos verbos; nesta frente so o que ja e medido | Yes |
| Ligar o span do host ao span do SparkForge | Nao ha contexto propagado entre os processos; parear por ordem ou por nome seria heuristica | Yes, se o host propagar `traceparent` |
| Custo (`estimated_cost_usd`) como atributo | Regra 25: sem `cost_basis` nao ha dolar | Yes, com `cost_basis` |
| Conteudo de mensagens (`gen_ai.input.messages`, `gen_ai.output.messages`) | Privacidade, e o spec os trata como opt-in | Yes, opt-in |
| Logs/eventos OTel | Fora do nucleo | Yes |
| Tokens por mensagem do host | `host.usage` e somado por transcript; separar por mensagem e mudanca maior no extrator | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| O que o export produz (spans SparkForge e host, atributos, metricas, o que nunca sai) | ✅ | "Sim, segue" | No |
| Superficie, prova e amostras (tool MCP, horarios no extrator, `fixtures/otel/`, Collector no CI, fontes T1) | ✅ | "Sim, escreve o BRAINSTORM" | Sim: a saida com nome fixo substitui o `--out` apresentado na primeira secao, pela licao do Snyk |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O SparkForge mede cada chamada de tool (duracao, bytes, desfecho), e o extrator do host mede os tokens da sessao. Nenhuma das duas medidas sai num formato que CloudWatch, Grafana, Datadog, Langfuse, Jaeger ou um OTLP Collector leia, e por isso quem opera o agente nao ve as tools do SparkForge ao lado das chamadas de modelo.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Dono da plataforma que opera agentes | Nao consegue colocar as tools do SparkForge no mesmo backend de observabilidade das chamadas de modelo |
| Engenheiro que depura uma sessao lenta | So ve a duracao por tool rodando `economy report`, fora da ferramenta de tracing que ja usa |
| Quem avalia custo de sessao | Ve tokens do host e bytes do SparkForge em lugares diferentes, sem a separacao de unidades (regra 22) preservada num formato padrao |

### Success Criteria (Draft)
- [ ] Os casos de `fixtures/otel/` batem byte a byte com os goldens, e exportar o mesmo run duas vezes da o mesmo arquivo.
- [ ] Todo arquivo gerado nos testes segue as regras do OTLP/JSON: ids em hex com 32 e 16 caracteres, `*UnixNano` como string, enum inteiro e chaves lowerCamelCase.
- [ ] Sem transcript do host, **0** atributos `gen_ai.usage.*` no arquivo.
- [ ] `exportados + recusados = spans do run` em todos os casos.
- [ ] No CI, o `otelcol-contrib` le os casos com o `otlpjsonfile` e o exporter `file` devolve os mesmos spans, com os mesmos `gen_ai.tool.name` e `gen_ai.usage.*`.
- [ ] Os 21 goldens de `fixtures/host_transcript` mudam so nos campos de horario novos.
- [ ] `check_surface_lock.py --update` com o crescimento declarado, e os gates de lastro, status e evals verdes, com a suite por lotes.

### Constraints Identified
- Regras 22, 24 e 25: byte nao vira token, token so com transcript, dolar so com `cost_basis`.
- Regra 23: nenhuma chamada de provider, e nenhuma rede no pacote.
- Regra 26: a tool nova move o `surface.lock` e os registros manuais (lista em `tool-nova-move-registros-manuais`), mais `NOVAS_DEPOIS_DO_GOLDEN` no teste de paridade do MCP.
- Regra 27: a mudanca no `record()` (canal em `metadata`) continua sem poder derrubar a chamada.
- Um dominio novo em `fixtures/` exige modulo golden (`test_fixtures_kind_coverage.py`).
- A saida escreve so sob `--repo`, com nome fixo.

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Mudar o schema do `traces.db` ou o `economy report`.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 (5 de discovery, 1 de abordagem, 1 de YAGNI, 2 de validacao) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_OTEL_GENAI_EXPORT.md`
