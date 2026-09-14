<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_cloudwatch`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa as metricas de observabilidade Glue via `cloudwatch.get_metric_data` (skewness, uso de heap, bytes/records lidos e escritos, sucesso/erro) e registra no manifesto. Requer `--enable-observability-metrics=true` no job; sem isso o CloudWatch simplesmente nao tem as series, e a chamada grava o que veio de volta sem adivinhar. Mesma politica offline-first de `sparkforge_collect_event_log`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `end` | string | sim | Fim ISO 8601. |
| `job_name` | string | sim |  |
| `job_run_id` | string | sim |  |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `start` | string | sim | Inicio ISO 8601. |

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
