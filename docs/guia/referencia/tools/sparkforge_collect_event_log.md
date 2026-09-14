<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_event_log`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa o Spark event log de um job run via `s3.list_objects_v2`/`get_object` e registra no manifesto (`.sparkforge/artifacts/manifest.json`). Le, nunca grava nada do lado AWS. Offline-first: uma segunda chamada com o mesmo artefato ja presente e integro localmente (`cache_hit: true`) nao toca rede nem credenciais. boto3 ausente devolve um erro com o comando `pip install` E o caminho exato para registrar uma coleta manual -- nunca deixa a ferramenta inutilizavel. NAO interpreta o log; use `sparkforge_analyze_event_log` depois.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `bucket` | string | sim |  |
| `job_run_id` | string | sim |  |
| `now` | string | sim | Timestamp ISO 8601. |
| `prefix` | string | sim |  |
| `repo` | string | sim | Raiz do repositorio analisado. |

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
