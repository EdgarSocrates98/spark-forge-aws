<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_analyze_platform_graph`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Analisa um Metadata Graph de plataforma declarado em JSON/YAML e calcula lineage impact bounded. Suporta entidades de dataset, job, run, producer, consumer, contract, owner, SLO, schema, dashboard, metric, model, service, topic, stream, catalog, orchestrator, feature e vector index. IDs são a única chave de junção; arestas não são inferidas por label. Conflitos, endpoints ausentes e atributo não observado permanecem em unresolved. Opera offline e read-only; não consulta AWS, Kafka, Flink, dbt ou catálogo.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON ou YAML do grafo. |
| `changed_attribute` | string | não |  |
| `changed_node` | string | não |  |
| `direction` | string: `downstream`, `upstream`, `both` | não |  |
| `max_depth` | integer | não |  |
| `max_items` | integer | não |  |

## Na CLI

[`sparkforge-aws analyze platform-graph`](../cli/analyze.md)

## Capacidade

analyze explicit Data Platform metadata graph and bounded lineage impact

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
