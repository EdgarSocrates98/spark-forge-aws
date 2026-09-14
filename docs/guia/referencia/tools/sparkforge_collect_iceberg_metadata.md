<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_iceberg_metadata`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Consulta as cinco metadata tables Iceberg de uma tabela via Athena (`SELECT * FROM "db"."tabela$secao"`) e registra no manifesto. AccessDeniedException numa metadata table quase sempre e Lake Formation (filtro de linha/celula), nao IAM -- o erro aponta para o lugar certo. Mesma politica offline-first de `sparkforge_collect_event_log`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Timestamp ISO 8601. |
| `output_location` | string | sim |  |
| `repo` | string | sim |  |
| `table` | string | sim | db.tabela |
| `workgroup` | string | sim |  |

## Na CLI

[`sparkforge collect athena-workgroup`](../cli/collect.md), [`sparkforge collect cloudwatch`](../cli/collect.md), [`sparkforge collect cloudwatch-logs`](../cli/collect.md), [`sparkforge collect emr-cluster`](../cli/collect.md), [`sparkforge collect emr-eks`](../cli/collect.md), [`sparkforge collect emr-serverless`](../cli/collect.md), [`sparkforge collect event-log`](../cli/collect.md), [`sparkforge collect glue-job`](../cli/collect.md), [`sparkforge collect glue-job-runs`](../cli/collect.md), [`sparkforge collect glue-resource-link`](../cli/collect.md), [`sparkforge collect iam-access`](../cli/collect.md), [`sparkforge collect iceberg-metadata`](../cli/collect.md), [`sparkforge collect lakeformation`](../cli/collect.md), [`sparkforge collect parquet-footer`](../cli/collect.md), [`sparkforge collect verify`](../cli/collect.md)

## Capacidade

collect real AWS artifacts and verify the manifest

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
