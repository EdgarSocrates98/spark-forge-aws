# SparkForge no OpenTelemetry: tools e sessao do host em OTLP

`sparkforge telemetry export` pega o que ja foi medido e grava em OTLP/JSON, o
formato que um OTLP Collector le. De la, o Collector envia para CloudWatch,
Grafana, Datadog, Langfuse, Jaeger ou o backend que o time ja usa. Duas fontes
entram no arquivo:

- **as chamadas de tool do SparkForge**: cada chamada que passa por
  `call_tool` ja vira um span em `.sparkforge/traces.db` (o mesmo que
  `economy report` le), com nome, duracao, bytes e desfecho;
- **a sessao do host**, quando voce aponta o transcript
  (`--host-transcript`): um span `invoke_agent` com modelo e tokens, e um span
  filho por tool que o agente chamou.

O verbo nao chama rede, nao instala dependencia e nao chama provider (regra 23):
quem envia e o Collector.

## Uso

```bash
# o processo que chama as tools grava com um run_id conhecido
export SPARKFORGE_RUN_ID=run_sessao_42
python -m sparkforge.adapters.mcp --transport stdio   # ou qualquer chamada a call_tool

# depois, no mesmo diretorio
sparkforge telemetry export --run-id run_sessao_42 \
    --host-transcript ~/.claude/projects/<projeto>/<sessao>.jsonl \
    --provider anthropic --repo .
```

A saida tem nome fixo, sob `--repo`:

- `.sparkforge/telemetry/<run_id>.traces.jsonl` (uma linha `TracesData`)
- `.sparkforge/telemetry/<run_id>.metrics.jsonl` (uma linha `MetricsData`, ou
  vazio)

O stdout traz as contagens, as recusas e as lacunas. Exportar o mesmo run duas
vezes da o mesmo arquivo, byte a byte: os ids sao `sha256` do id local, e o
backend nao duplica o trace.

A tool MCP `sparkforge_telemetry_export` devolve o mesmo conteudo e **nao
grava**: gravar e da CLI.

## Collector

```yaml
receivers:
  otlpjsonfile/traces:
    include: [/caminho/do/repo/.sparkforge/telemetry/*.traces.jsonl]
    start_at: beginning
  otlpjsonfile/metrics:
    include: [/caminho/do/repo/.sparkforge/telemetry/*.metrics.jsonl]
    start_at: beginning
exporters:
  otlphttp:
    endpoint: https://seu-backend
service:
  pipelines:
    traces:  {receivers: [otlpjsonfile/traces],  exporters: [otlphttp]}
    metrics: {receivers: [otlpjsonfile/metrics], exporters: [otlphttp]}
```

Traces e metricas ficam em **arquivos separados** porque o `otlpjsonfile` le
cada linha com o leitor do seu pipeline: uma linha de metrica no pipeline de
traces conta como falha do receiver.

## O que sai

| Origem | Span | Kind | Atributos |
|---|---|---|---|
| Chamada que veio pelo servidor MCP | `tools/call {tool}` | SERVER | `mcp.method.name=tools/call`, `network.transport` (`pipe` no stdio, `tcp` no http), `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name` |
| Chamada sem canal medido | `execute_tool {tool}` | INTERNAL | `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.type=function` |
| Sessao do host | `invoke_agent` | INTERNAL | `gen_ai.request.model`, `gen_ai.provider.name` (declarado), `gen_ai.usage.input_tokens`, `output_tokens`, `cache_read.input_tokens`, `cache_write.input_tokens` |
| Tool chamada pelo host | `execute_tool {tool}`, filho do `invoke_agent` | INTERNAL | `gen_ai.tool.name`, `gen_ai.tool.call.id` |

Detalhes de cada atributo:

- **Canal:** so a chamada que entrou pelo servidor MCP recebe
  `mcp.method.name`. O canal e gravado no span no momento da chamada
  (`adapters/mcp.py`); nada e deduzido depois.
- **Bytes:** a resposta de tool sai em `sparkforge.payload_bytes`, com a
  formula em `sparkforge.payload_basis`, e **nunca** como token (regra 22).
- **Erro:** desfecho `error` ou `unauthorized` sai com status ERROR,
  `error.type=tool_error` e o desfecho em `sparkforge.outcome`.
- **Duracao:** a de um span do SparkForge cobre `call_tool`, e nao a
  validacao e a serializacao do envelope MCP. O escopo diz isso em
  `sparkforge.duration_scope=call_tool`.

Metricas, cada uma so onde ha semconv e medida:

| Metrica | Fonte | Forma |
|---|---|---|
| `mcp.server.operation.duration` | Spans que vieram pelo MCP | Histograma com as fronteiras do `mcp.md` e contagens reais |
| `gen_ai.invoke_agent.duration` | Sessao do host | Um ponto |
| `gen_ai.client.token.usage` | `host.usage`, so com `--provider` | Um ponto por `gen_ai.token.type`, com `count` = mensagens com usage e `sum` = total, **sem** distribuicao: o transcript so da o total |

## O que nunca sai, e as recusas

- **Token sem transcript.** Sem `--host-transcript` nao ha `gen_ai.usage.*`
  nem metrica de token (regra 24). Span de tool tem byte, nao token.
- **Custo.** Nenhum atributo de dolar (regra 25).
- **Conteudo.** Nem mensagem, nem argumento ou resultado de tool.
- **Ligacao entre host e SparkForge.** Os dois viram traces separados: nenhum
  contexto e propagado entre os processos, e parear por ordem ou nome seria
  heuristica.

Todo span entra na conta: `exported + refused` fecha com o total, e a recusa
tem nome (regra 20):

| Motivo | Quando |
|---|---|
| `sem_horario` | Span do `traces.db` sem inicio ou fim |
| `componente_nao_tool` | Span do `traces.db` que nao e de tool (o `AgentOpsTracker` grava `task`, `routing` e `model` no mesmo banco) |
| `host_sem_horario` | Tool call do host sem `timestamp` na linha do `tool_use` ou do `tool_result` |
| `transcript_sem_horario` | Transcript sem `timestamp`: o `invoke_agent` nao sai, e as tool calls saem sem pai |

O que falta sem derrubar span vai para `unresolved`:

- `gen_ai.provider.name` sem `--provider`;
- `gen_ai.request.model` ausente, ou com mais de um modelo no transcript;
- `gen_ai.usage` quando o transcript nao traz usage.

**O provider e declarado, nunca deduzido.** O transcript do Claude Code guarda
o modelo, e o mesmo host roda sobre a API da Anthropic, o Bedrock ou o Vertex.
Sem `--provider`, o span `invoke_agent` sai sem um atributo que a semconv marca
como obrigatorio, e a lacuna fica nomeada em vez de preenchida por palpite.

## Fontes, e o status delas

| Fonte | Versao | Status |
|---|---|---|
| `open-telemetry/semantic-conventions-genai`: `gen-ai-spans.md`, `gen-ai-agent-spans.md`, `gen-ai-metrics.md` e `mcp.md` | commit `0c87594975195608dc91b3f702e250a7b240c151` (2026-09-11) | **Development** |
| OTLP, encoding JSON (ids em hex, int64 como string decimal, enum inteiro, lowerCamelCase) | 1.11.0 | — |
| OTLP file exporter (JSON Lines, uma `TracesData`/`MetricsData` por linha) | — | Development |
| Receiver `otlpjsonfile` do Collector contrib | 0.160.0 | alpha para traces |

Uma semconv em Development muda nome de atributo. O commit seguido sai no
escopo de cada arquivo (`sparkforge.semconv_genai_commit`) e no stdout do verbo.

## Prova

- **Golden:** `fixtures/otel/` tem 4 casos (so SparkForge, SparkForge com erro
  e recusa, SparkForge mais host com usage, e host sem usage), com os spans de
  chamadas reais de `call_tool`. A CLI de verdade, lendo de um `traces.db` real,
  bate byte a byte com o golden.
- **Consumidor real:** o job `otel-collector` do CI sobe o `otelcol-contrib`
  0.160.0 com o `otlpjsonfile` sobre os goldens e o exporter `file`, e
  `scripts/check_otel_collector.py` confere, do outro lado, os mesmos spans,
  atributos e pontos de metrica.
