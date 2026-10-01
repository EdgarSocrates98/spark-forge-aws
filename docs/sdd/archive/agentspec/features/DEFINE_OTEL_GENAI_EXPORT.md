# DEFINE: OpenTelemetry GenAI export

> Um verbo `sparkforge telemetry export` que projeta os spans de tool ja gravados em `.sparkforge/traces.db` e, quando houver, o transcript do host em OTLP/JSON Lines com as convencoes `gen_ai.*` e `mcp.*`. A saida e deterministica, sem rede, sem dependencia nova e sem nenhum numero que a fonte nao mediu. A prova e um Collector real que le o arquivo.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | OTEL_GENAI_EXPORT |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O SparkForge mede cada chamada de tool (duracao, bytes e desfecho), e o extrator do host mede os tokens da sessao. Nenhuma das duas medidas sai num formato que um OTLP Collector, e por ele CloudWatch, Grafana, Datadog, Langfuse ou Jaeger, consiga ler. Por isso quem opera o agente nao ve as tools do SparkForge ao lado das chamadas de modelo, na ferramenta de tracing que ja usa.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Dono da plataforma de agentes | Opera o host (Claude Code ou outro) com o SparkForge como servidor MCP | Nao consegue colocar as tools do SparkForge no mesmo backend das chamadas de modelo |
| Engenheiro que depura uma sessao lenta | Investiga qual tool segurou a sessao | Hoje so tem `economy report`, fora da ferramenta de tracing |
| Quem avalia o consumo de uma sessao | Compara tokens do host com bytes das tools | Ve as duas unidades em lugares diferentes, sem formato padrao que preserve a separacao (regra 22) |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: `sparkforge telemetry export --run-id <id> [--host-transcript <path>] [--provider <nome>] --repo .` compoe sobre o `traces.db` e sobre os facts `host.*` extraidos do transcript (a mesma flag do `economy report`), sem rede |
| **MUST** | G2: cada span de tool do run vira um span OTLP `execute_tool {tool}` (ou `tools/call {tool}`, kind SERVER, quando o canal medido for MCP: DESIGN Decision 3) com `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.type=function`, inicio e fim medidos, e status ERROR quando `outcome` for `error` ou `unauthorized`. O desfecho sai em `sparkforge.outcome` |
| **MUST** | G3: os bytes saem em `sparkforge.payload_bytes`, com `sparkforge.payload_basis` e `sparkforge.detail_level` quando houver. **Nunca** saem em `gen_ai.usage.*` (regra 22) |
| **MUST** | G4: ids deterministicos: `traceId` = primeiros 32 hex de `sha256(run_id)` e `spanId` = primeiros 16 hex de `sha256(span_id)`. Exportar o mesmo run duas vezes da o mesmo arquivo, byte a byte |
| **MUST** | G5: a saida segue o encoding JSON do OTLP 1.11.0 (ids em hex, `*UnixNano` como string decimal, enum inteiro, chaves lowerCamelCase), em JSON Lines, gravada sob `.sparkforge/telemetry/` em dois arquivos com nome fixo derivado do `run_id` validado: `<run_id>.traces.jsonl` e `<run_id>.metrics.jsonl` |
| **MUST** | G6: nenhum span some. Span sem horario medido nao e exportado: vira recusa nomeada, e `exportados + recusados = total` sai no resultado |
| **MUST** | G7: token so com fonte. Sem `--host-transcript`, o arquivo tem **0** atributos `gen_ai.usage.*` e nenhuma metrica de token (regra 24). Custo nunca sai (regra 25) |
| **MUST** | G8: o extrator `host_transcript` passa a guardar horario: `host.transcript` ganha `first_timestamp` e `last_timestamp`, e `host.tool_call` ganha `started_at` (linha do `tool_use`) e `ended_at` (linha do `tool_result`). Quando a linha nao traz `timestamp`, o campo fica ausente, nunca zero |
| **MUST** | G9: com facts `host.*`, um trace do host com um span `invoke_agent` (inicio e fim do transcript, `gen_ai.request.model`, e os quatro `gen_ai.usage.*`: `input_tokens`, `output_tokens`, `cache_read.input_tokens`, `cache_write.input_tokens`). As tool calls do host viram spans filhos `execute_tool`, com o horario delas |
| **SHOULD** | G10: canal medido. `adapters/mcp.py` informa o canal a `call_tool`, e o `record()` o grava em `metadata` do span, sem migrar o schema do `traces.db` e sem poder derrubar a chamada (regra 27). So o span com canal `mcp` recebe `mcp.method.name=tools/call` |
| **SHOULD** | G11: metricas em `MetricsData`: `gen_ai.client.token.usage` (so do host, por `gen_ai.token.type`, com `count` = mensagens com usage e `sum` = total, sem distribuicao inventada), duracao das operacoes e `mcp.server.operation.duration` para os spans MCP |
| **SHOULD** | G12: tool MCP `sparkforge_telemetry_export`, `READ_ONLY`, que devolve o mesmo conteudo e as contagens, sem gravar |
| **SHOULD** | G13: `docs/opentelemetry.md` com o verbo, a configuracao do Collector (`otlpjsonfile`), o que nunca sai, e as fontes com o status delas: semconv GenAI em Development no commit `0c87594`, file exporter em Development e receiver em alpha |
| **COULD** | G14: job de CI com `otelcol-contrib` em versao fixa, que le os goldens com o `otlpjsonfile` (`start_at: beginning`) e confere, na saida do exporter `file`, os mesmos spans e atributos |

---

## Success Criteria

- [ ] SC1: **4** casos em `fixtures/otel/` batem byte a byte com o golden: so SparkForge, SparkForge com erro e recusa, SparkForge mais host com usage, e host sem usage. Exportar o mesmo run duas vezes da o mesmo arquivo.
- [ ] SC2: todo arquivo gerado nos testes passa no teste de forma: `traceId` com 32 hex e `spanId` com 16 hex, `startTimeUnixNano`/`endTimeUnixNano` como string de digitos, `kind` e `status.code` inteiros, e nenhuma chave em snake_case.
- [ ] SC3: nos casos sem host, **0** ocorrencias de `gen_ai.usage.` no arquivo.
- [ ] SC4: em todos os casos, `exportados + recusados` e igual ao numero de spans do run no `traces.db`.
- [ ] SC5: os **21** goldens de `fixtures/host_transcript` mudam so nos campos de horario novos, e o diff mostra isso.
- [ ] SC6: nos casos com host, a soma dos `gen_ai.usage.input_tokens` e `output_tokens` exportados e igual ao `host.usage` da mesma fonte.
- [ ] SC7 (G14): no CI, o `otelcol-contrib` le cada golden e o exporter `file` devolve o mesmo numero de spans, com os mesmos valores de `gen_ai.tool.name` e `gen_ai.usage.*`.
- [ ] SC8: a chamada de tool continua devolvendo o resultado com o `record()` falhando ao gravar o canal (teste de regra 27).
- [ ] SC9: `check_surface_lock.py --update` com o crescimento declarado; `check_vnext_claims.py`, `check_status_numbers.py --strict`, `check_evals.py` e `ruff` verdes; suite por lotes com **0** falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Tools do SparkForge | Run com 3 chamadas `ok` no `traces.db` | `telemetry export --run-id` | 3 spans `execute_tool {tool}` num trace, com `gen_ai.tool.name` e `sparkforge.payload_bytes`; nenhum `gen_ai.usage.*` |
| AT-002 | Desfecho | Um span `unauthorized` e um `error` | export | Os dois com status ERROR, e `sparkforge.outcome` distinguindo um do outro |
| AT-003 | Determinismo | O mesmo run | export duas vezes | Arquivos byte a byte iguais |
| AT-004 | Canal MCP | Chamada vinda de `adapters/mcp.py` | export | Span com `mcp.method.name=tools/call`; chamada sem canal fica sem o atributo |
| AT-005 | Host com usage | Transcript de `fixtures/host_transcript/correct_mcp` e `--provider anthropic` | export com `--host-transcript` | Trace do host com `invoke_agent`, modelo, os quatro `gen_ai.usage.*` iguais ao `host.usage`, e spans filhos das tool calls com horario |
| AT-006 | Host sem usage | Transcript de `no_usage`, sem `--provider` | export com `--host-transcript` | `invoke_agent` sem `gen_ai.usage.*` e sem `gen_ai.provider.name`; nenhuma metrica de token; `unresolved` nomeia o provider |
| AT-007 | Sem horario | Tool call do host sem `timestamp` na linha | export | O span nao sai; recusa nomeada, e a soma fecha |
| AT-008 | Extrator | Os 21 transcripts existentes | `extract_host_transcript_path` | Mesmos facts e mesmos ids de antes, mais os campos de horario em `attrs` |
| AT-009 | Metricas | Host com usage e spans MCP | export | `gen_ai.client.token.usage` por tipo, com `count` e `sum` medidos; `mcp.server.operation.duration` so para spans MCP |
| AT-010 | Tool MCP | Mesmo run e mesmos facts | `sparkforge_telemetry_export` | Mesmo conteudo da CLI; nada gravado em disco |
| AT-011 | Entrada invalida | `--run-id` fora do padrao, run sem spans, ou `--provider` fora do padrao | export | Exit 2 com mensagem acionavel |
| AT-012 | Medicao nao derruba | `record()` falhando | `call_tool` via MCP | Resultado da tool devolvido normalmente |
| AT-013 | Collector real | Os goldens no CI | `otelcol-contrib` com `otlpjsonfile` e exporter `file` | Mesmos spans e atributos do outro lado |

---

## Out of Scope

- Exporter OTLP ao vivo (HTTP ou gRPC) e qualquer rede no pacote.
- Gravar em formato OTel na origem, ou mudar o schema do `traces.db`.
- Spans de pipeline (`evidence.collect`, `rule.judge`, `debate.round`, `decision.publish`).
- Ligar o trace do host ao do SparkForge: nao ha contexto propagado entre os processos, e parear por ordem ou nome seria heuristica.
- Custo como atributo, e conteudo de mensagens (`gen_ai.input.messages`/`output.messages`).
- Logs e eventos OTel.
- Tokens por mensagem do host.
- Mudar o `economy report`.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regras 22, 24 e 25 | Byte nao vira token; token so com transcript; nenhum dolar |
| Technical | Regra 23 e perfil `offline-strict` | Nenhuma rede nem provider no pacote; o envio e do Collector do operador |
| Technical | Regra 26 e os registros manuais de tool nova, mais `NOVAS_DEPOIS_DO_GOLDEN` | `surface.lock --update`, com o crescimento declarado no commit |
| Technical | Regra 27 | O canal gravado no `record()` fica dentro do mesmo try/except da montagem do span |
| Technical | Escrita so sob `--repo`, com nome fixo | Nenhum `--out` vindo do argv |
| Technical | Dominio novo em `fixtures/` exige modulo golden (`test_fixtures_kind_coverage.py`) | `tests/test_fixtures_golden_otel.py` |
| Technical | Mudanca no extrator `host_transcript` | Versao do extrator sobe e os 21 goldens sao regenerados; `EXTRACTORS` e as listas manuais continuam coerentes |
| Technical | Semconv GenAI e file exporter em Development, receiver em alpha | O documento publica o status e o commit fixado; nada e vendido como estavel |
| Resource | O job de Collector baixa uma imagem `otelcol-contrib` | Versao fixada, e so no CI |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | Projecao em `sparkforge/observability/otlp.py` (pura, sem importar adapter); verbo em `adapters/_core.py`, `adapters/cli.py` e `adapters/tools.py`; canal em `adapters/mcp.py` e `observability/context_ledger.py`; horarios em `facts/host_transcript.py`; `fixtures/otel/`; `docs/opentelemetry.md`; um job em `.github/workflows/ci.yml` | Mesmo molde de `economy report` e `report github` |
| **KB Domains** | Observability (OpenTelemetry, OTLP, semconv GenAI e MCP), testing (golden e teste de forma), CI/CD (GitHub Actions com container) | — |
| **IaC Impact** | Modify existing (`ci.yml`, um job) | Nenhum recurso de nuvem |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `gen_ai.*` e `mcp.*` com os nomes do commit `0c87594` de `semantic-conventions-genai` (`execute_tool`, `invoke_agent`, `gen_ai.tool.name`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`, `mcp.method.name=tools/call`) | Nomes mudam numa semconv em Development; o commit fixado diz o que o arquivo segue | [x] lido na fonte em 2026-09-11 |
| A-002 | O `otlpjsonfile` le cada linha com o unmarshaler do pipeline (`ptrace` ou `pmetric`), conforme o `file.go` do receiver | Uma linha de `MetricsData` pode quebrar o pipeline de traces; o DESIGN escolhe entre um arquivo misto e dois arquivos, e o Collector no CI decide | [x] DESIGN Decision 1: dois arquivos, um por sinal |
| A-003 | `gen_ai.provider.name` (obrigatorio na metrica de token) pode ser derivado de `host.transcript.attrs.source` (`claude_code` fala com `anthropic`) | Se o host puder rodar sobre Bedrock ou Vertex sem que o transcript diga, o provider ficaria errado; nesse caso ele fica ausente e a metrica de token so sai quando houver fonte | [x] DESIGN Decision 2: `--provider` declarado; nunca deduzido |
| A-004 | Os transcripts do Claude Code trazem `timestamp` ISO 8601 por linha | Sem horario, o span do host vira recusa (G6) | [x] 7/7 em `correct_mcp` |
| A-005 | Um histograma OTLP com `count` e `sum` e um bucket so, sem `explicitBounds`, e valido e aceito pelo Collector | Teriamos de emitir a metrica de token como `Sum` em vez de histograma | [ ] (SC7) |
| A-006 | `adapters/mcp.py` e o unico chamador de `call_tool` que precisa declarar canal; os outros chamadores ficam sem canal, o que e verdade | Se a CLI tambem passar por `call_tool`, o canal `cli` pode ser acrescentado sem mudar o contrato | [x] conferido: so `adapters/mcp.py` chama `call_tool` |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | O que ja e medido, onde nao aparece, e para quem |
| Users | 3 | Tres papeis, cada um ligado a uma saida |
| Goals | 3 | MoSCoW com 14 metas, cada uma ligada a SC ou AT |
| Success | 3 | Contagens exatas (4 casos, 21 goldens, 0 `gen_ai.usage` sem host, soma que fecha) |
| Scope | 2 | Escopo claro; arquivo misto ou dois arquivos (A-002) e o provider (A-003) ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-002, A-003 e A-006 sao decididas no DESIGN; A-005 e respondida pelo Collector no CI (SC7).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versao inicial, a partir de `BRAINSTORM_OTEL_GENAI_EXPORT.md` |
| 1.1 | 2026-09-11 | design-agent | G1 com `--host-transcript` e `--provider`; G5 com dois arquivos; A-002, A-003 e A-006 decididas no DESIGN |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_OTEL_GENAI_EXPORT.md`
