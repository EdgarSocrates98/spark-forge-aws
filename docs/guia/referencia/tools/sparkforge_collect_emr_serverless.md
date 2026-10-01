<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_emr_serverless`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa `get-application` de uma application Amazon EMR Serverless e registra a resposta no manifesto, no mesmo shape camelCase que `aws emr-serverless get-application` devolve -- coleta manual e automatica produzem o mesmo arquivo, que e o que `sparkforge_analyze_emr_serverless` le. UMA chamada, nao seis como no EMR on EC2: capacidade inicial e maxima, auto-start/stop, `runtimeConfiguration` e `monitoringConfiguration` chegam todos dentro do mesmo objeto. Job runs ficam FORA por escopo. Exige `application_id`, nunca nome: `name` e opcional na API e nenhuma fonte o declara unico, entao resolver id por nome escolheria uma entre homonimas em silencio. Mesma politica offline-first de `sparkforge_collect_event_log`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `application_id` | string | sim | 00fXXXXXXXXXXXXX |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |

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
