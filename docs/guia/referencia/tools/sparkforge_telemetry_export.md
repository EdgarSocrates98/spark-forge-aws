<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_telemetry_export`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Os spans de tool que o SparkForge mediu num run (`run_id`, o mesmo de `economy report`) e, com `host_transcript_path`, o transcript do host, em OTLP/JSON (`traces` = TracesData, `metrics` = MetricsData), com os atributos `gen_ai.*` e `mcp.*` da semconv GenAI no commit `semconv_genai_commit` (status Development). Chamada que veio pelo servidor MCP sai como span `tools/call {tool}`; sem canal medido, `execute_tool {tool}`. Bytes saem em `sparkforge.payload_bytes`, nunca como token; token so vem do transcript (span `invoke_agent`), e custo nunca sai. `provider` e DECLARADO (anthropic, aws.bedrock, gcp.vertex_ai): sem ele, `gen_ai.provider.name` vai para `unresolved` e a metrica de token nao sai. Span sem horario medido vai para `refused` com o motivo. Nada e gravado por esta tool -- a CLI `sparkforge telemetry export` grava em .sparkforge/telemetry/, para o receiver `otlp_json_file` de um OTLP Collector.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `run_id` | string | sim | O SPARKFORGE_RUN_ID do processo que chamou as tools. |
| `host_transcript_path` | string | não | Transcript JSONL do host, quando houver. |
| `provider` | string | não | Provider do host (gen_ai.provider.name), declarado. |

## Na CLI

[`sparkforge telemetry export`](../cli/telemetry.md)

## Capacidade

export tool spans and host usage to an OTLP collector

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
