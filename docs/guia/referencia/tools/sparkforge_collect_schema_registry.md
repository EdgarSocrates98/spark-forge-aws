<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_schema_registry`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Coleta metadata, compatibilidade declarada e latest schema version do AWS Glue Schema Registry usando somente list/get. Grava artifact local com manifesto, limite de definição e cache offline-first; nunca cria, registra, atualiza ou exclui registry/schema/version.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `max_definition_bytes` | integer | não |  |
| `max_schemas` | integer | não |  |
| `region_name` | string | não |  |
| `registry_name` | string | não |  |
| `schema_arn` | string | não |  |
| `schema_name` | string | não |  |

## Na CLI

[`sparkforge-aws collect schema-registry`](../cli/collect.md)

## Capacidade

collect Glue Schema Registry latest versions read-only

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
