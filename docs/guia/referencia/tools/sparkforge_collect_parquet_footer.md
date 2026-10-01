<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_parquet_footer`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Le so o FOOTER dos primeiros `max_files` arquivos Parquet de um prefixo (diretorio local ou `s3://`) -- schema, row groups, estatistica min/max por coluna -- e registra o artefato no manifesto com `kind: parquet_footer`, que `sparkforge_analyze_parquet_footer` e o `sparkforge_scan` leem. Nenhuma linha de dado e lida. A amostra e DECLARADA (os N primeiros pelo nome, teto 500) e sai no artefato. Exige pyarrow (`pip install 'sparkforge-aws[parquet]'`); S3 usa a cadeia padrao de credencial. Prefixo inexistente, vazio ou sem permissao vira `status` no artefato, nao erro.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Timestamp ISO 8601. |
| `prefix` | string | sim | Diretorio local com .parquet, ou s3://bucket/prefixo/. |
| `repo` | string | sim |  |
| `max_files` | integer | não |  |

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
