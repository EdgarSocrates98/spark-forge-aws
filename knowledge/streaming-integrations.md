# Streaming integrations: checkpoints, Kafka Connect, Kafka Streams e OpenLineage

Este domínio aceita dumps JSON/JSONL sanitizados. O núcleo não abre endpoint,
não usa cliente Kafka, não chama AWS e não publica eventos de lineage. A análise
mede o que o artefato declara; coleta live é uma etapa operacional separada.

## Checkpoint e estado

Para uma query Structured Streaming, identidade mínima é `query_name`,
`path`, `storage`, `state_store` e versão/schema do estado. O dump ganha valor
diagnóstico quando traz uma série pareada de `batch_duration_ms`,
`trigger_interval_ms`, backlog, state rows e atraso de watermark. Uma amostra
isolada não sustenta tendência. Trocar localização ou reaproveitar checkpoint
sem provar compatibilidade pode alterar offsets, replay e estado; o Forge não
conclui sem identidade e contexto.

## Kafka Connect

O artefato deve separar worker `standalone`/`distributed`, connector source/sink,
classe, status, tasks, worker, converters, SMTs, offsets e error handling/DLQ.
Credenciais, tokens e passwords são redigidos. `RUNNING` de um connector não
prova que todos os tasks estão saudáveis, nem que entrega end-to-end é exactly-once.

## Kafka Streams

Comparação arquitetural exige `application_id`, processing guarantee, topology,
state stores, changelog topics, repartition topics, joins e windows. State store
persistente e changelog fazem parte da recuperação; repartition altera custo e
ordering é por partição, não global. Interactive queries só entram quando
declaradas. O analyzer documenta candidato e evidência; não converte o Forge em
runtime Kafka Streams.

## OpenLineage

Evento mínimo rastreável identifica `eventType`, producer, Job, Run, inputs e
outputs. Facets são extensões, não substitutos de identidade. Um evento parcial
não vira lineage completo e não é correlacionado com Spark/Flink/Iceberg sem
identidade declarada. O suporte é opcional: ausência de OpenLineage permanece
`unresolved`, nunca prova de ausência de lineage.

## Coleta read-only e fronteira de segurança

`sparkforge collect streaming-integrations` grava um artefato composto em
`.sparkforge/artifacts/streaming_integrations/` e registra SHA-256 no manifesto.
As fontes suportadas são:

- `--checkpoint-s3-uri`: lista limitada de objetos do diretório de checkpoint;
- `--glue-job`: snapshot de `glue.get_job`;
- `--kinesis-stream`: `describe_stream_summary` e `list_shards`;
- `--msk-cluster-arn`: `describe_cluster_v2`, com fallback explícito;
- `--dms-task-arn`: `describe_replication_tasks` filtrado por ARN.

São chamadas de leitura. Valores secret-like são redigidos antes da escrita
local. O cache só é aceito quando o arquivo local e o hash do manifesto batem.
Lag temporal, replay, throughput e reachability continuam `unresolved` porque
exigem uma janela de métricas, logs ou endpoint específico. Kafka Connect,
Kafka Streams e OpenLineage não têm uma API AWS universal: devem entrar por
export próprio, e não por uma coleta inventada.

Fontes oficiais:

- Spark Structured Streaming programming guide:
  https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- Apache Kafka Connect REST API:
  https://kafka.apache.org/documentation/#connect_rest
- Apache Kafka Streams documentation:
  https://kafka.apache.org/documentation/streams/
- OpenLineage object model:
  https://openlineage.io/docs/spec/object-model/
