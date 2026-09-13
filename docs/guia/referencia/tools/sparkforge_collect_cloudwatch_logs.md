<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_cloudwatch_logs`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa o LOG do run no CloudWatch Logs via `logs.filter_log_events` e registra no manifesto. E o caminho das assinaturas de `knowledge/errors/` que sao trecho de MENSAGEM e nao classe de excecao -- quatro das seis --, e do que o event log nao tem: falha de driver antes do primeiro stage, `Py4JJavaError` de codigo Python, e OOM de container morto pelo YARN. `log_group` e obrigatorio e nao tem default: `/aws-glue/jobs/error`, `/aws-glue/jobs/output` e `/aws-glue/jobs/logs-v2` (Glue 4.0+) sao grupos com conteudo diferente. Log group inexistente, permissao negada, janela vazia e credencial ausente NAO viram erro: viram `status` no artefato e `cloudwatch.logs.unresolved` no fact, com a razao. Mesma politica offline-first de `sparkforge_collect_event_log`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `end` | string | sim | Fim ISO 8601. |
| `job_name` | string | sim |  |
| `job_run_id` | string | sim |  |
| `log_group` | string | sim | Nome do log group. Sem default: grupo errado devolve vazio, e vazio se parece com 'o job nao logou nada'. |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `start` | string | sim | Inicio ISO 8601. |
| `filter_pattern` | string | não | Filtro do CloudWatch Logs, aplicado no servidor. E aqui que a RELEVANCIA e declarada -- o extrator nao adivinha linha interessante. |
| `max_events` | integer | não | Teto de eventos gravados. Quando morde, o artefato sai com `truncated: true` -- corte declarado, nunca silencioso. |

## Na CLI

[`sparkforge collect athena-workgroup`](../cli/collect.md), [`sparkforge collect cloudwatch`](../cli/collect.md), [`sparkforge collect cloudwatch-logs`](../cli/collect.md), [`sparkforge collect emr-cluster`](../cli/collect.md), [`sparkforge collect emr-eks`](../cli/collect.md), [`sparkforge collect emr-serverless`](../cli/collect.md), [`sparkforge collect event-log`](../cli/collect.md), [`sparkforge collect glue-job`](../cli/collect.md), [`sparkforge collect glue-job-runs`](../cli/collect.md), [`sparkforge collect glue-resource-link`](../cli/collect.md), [`sparkforge collect iam-access`](../cli/collect.md), [`sparkforge collect iceberg-metadata`](../cli/collect.md), [`sparkforge collect lakeformation`](../cli/collect.md), [`sparkforge collect verify`](../cli/collect.md)

## Capacidade

collect real AWS artifacts and verify the manifest

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
