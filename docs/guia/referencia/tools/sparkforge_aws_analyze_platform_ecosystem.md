<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_analyze_platform_ecosystem`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Normaliza inventário de serving/OLAP, conectores de ingestão e CDC, AI Data Engineering e radar Beam/DataHub/OpenMetadata. Preserva owner, evidence, bindings e Connector Reliability Model (idempotência, checkpoint, retry, DLQ, rate limit, schema, freshness e recovery). Radar permanece opcional; ausências ficam unresolved. Não instala nem consulta os produtos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON/YAML do inventário de ecossistema. |

## Na CLI

[`sparkforge-aws analyze platform-ecosystem`](../cli/analyze.md)

## Capacidade

inventory serving ingestion AI data and optional radar ecosystem

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
