<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_streaming_integrations`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Coleta snapshots read-only para o contrato streaming_integrations: prefixo de checkpoint Spark em S3, Glue Streaming, Kinesis, MSK e DMS. O coletor grava apenas no manifesto local, redige chaves secret-like e é offline-first. Kafka Connect, Kafka Streams e OpenLineage não possuem API AWS universal; sem artefato/endpoint próprio eles permanecem unresolved no analyzer.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `checkpoint_s3_uri` | string | não |  |
| `dms_task_arn` | string | não |  |
| `glue_job_name` | string | não |  |
| `kinesis_stream_name` | string | não |  |
| `max_objects` | integer | não |  |
| `max_shards` | integer | não |  |
| `metrics_end` | string | não | Fim ISO 8601 da janela CloudWatch Kinesis. |
| `metrics_period` | integer | não | Período em segundos; múltiplo de 60. |
| `metrics_start` | string | não | Início ISO 8601 da janela CloudWatch Kinesis. |
| `msk_cluster_arn` | string | não |  |
| `region_name` | string | não |  |

## Na CLI

[`sparkforge collect streaming-integrations`](../cli/collect.md)

## Capacidade

collect read-only streaming integration snapshots

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
