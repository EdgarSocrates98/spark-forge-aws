<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_glue_job_runs`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa o historico de execucoes de um job via `glue.get_job_runs` e grava UM artefato por run em estado terminal. Run ainda em execucao nao vira artefato: seu conteudo mudaria depois e o sha256 do manifesto divergiria. Coleta incremental de graca -- run ja em disco com hash integro e no-op. `max_runs` e teto de paginacao, nao filtro de data: a API devolve do mais recente para tras.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `job_name` | string | sim |  |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `max_runs` | integer | não |  |

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
