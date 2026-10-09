# Streaming transport diagnostics

Esta página define o que um dump offline de Kafka, MSK ou Kinesis pode provar.
Ela não substitui collector, métrica temporal ou validação do runtime.

## Kafka

`sparkforge-aws analyze transport --artifact kafka --path <dump.json>` aceita
descrição de topics/partitions, configs, consumer groups e offsets. Os facts
separam `kafka.topic`, `kafka.partition`, `kafka.consumer_group` e `kafka.lag`.
`replication_factor`, `isr_count`, offsets e lag são observações do dump; não são
limiares nem diagnóstico automático. Sem distribuição por partition, o Forge
deve pedir o artefato faltante antes de falar em hot partition.

Quando `replication_factor > isr_count` em `kafka.partition`, o judge pode emitir
`SF-STREAMOBS-003`: replicação degradada observada naquela partição. A regra não
afirma indisponibilidade, perda de dados, causa ou violação de
`min.insync.replicas` sem esses campos.

Para tendência, o dump pode declarar uma lista top-level `lag_observations`:

```json
{
  "lag_observations": [
    {"group": "orders", "topic": "events", "partition": 0, "lag": 4,
     "observed_at": "2026-10-03T00:00:00Z"},
    {"group": "orders", "topic": "events", "partition": 0, "lag": 9,
     "observed_at": "2026-10-03T00:01:00Z"}
  ]
}
```

O analyzer emite um `kafka.lag` por observação válida e compõe um
`kafka.lag.series` por `group/topic/partition`, com `observation_count`,
`first_lag`, `last_lag`, `delta_lag`, span temporal, `monotonic_increase` e
`observation_fact_ids`. Com pelo menos duas observações em ordem e crescimento
monotônico, `SF-STREAMOBS-004` solicita baseline de backlog. Um snapshot legado
em `consumer_groups[].offsets` continua sendo uma medida pontual: não gera
série. Timestamp ausente, ingênuo, inválido ou série insuficiente permanece
`kafka.unresolved`; nenhuma tendência é inferida pela ordem do arquivo.

Um consumer group com lag observado não prova causa. É necessário correlacionar
estado do grupo, assignment, producer rate, consumer rate, backlog temporal e
progresso da engine. Kafka documenta offsets por partition e o comando de
descrição de consumer groups expõe current offset, log end offset e lag.

## MSK

MSK é uma fronteira de serviço, não sinônimo da versão upstream de Kafka. O
dump pode carregar `kafka_version`, broker type, cluster identity,
encryption/security observadas e, se presentes, métricas de lag. A ausência de
uma dessas propriedades vira `msk.unresolved`; o analyzer não infere a versão
suportada a partir do nome do broker.

A documentação do serviço explica que consumer-lag metrics dependem do estado
do grupo e podem estar ausentes em cenários específicos. Portanto ausência de
métrica não significa lag zero. A matriz de versões MSK será uma onda separada,
com data, broker type e fonte por célula.

## Kinesis Data Streams

O dump de Kinesis separa `kinesis.stream`, `kinesis.shard` e `kinesis.metric`.
`IteratorAgeMilliseconds`, bytes e records permanecem com suas unidades. A
AWS publica métricas em nível de stream e, quando habilitadas, em nível de
shard; o analyzer não transforma stream-level em shard-level nem inventa uma
distribuição.

### Janela CloudWatch read-only

`collect streaming-integrations --kinesis-stream <stream>` pode receber
`--metrics-start <ISO8601> --metrics-end <ISO8601>` e, opcionalmente,
`--metrics-period <segundos>`. Isso chama `cloudwatch.get_metric_data` com
namespace `AWS/Kinesis`, dimensão somente `StreamName`, `ScanBy=TimestampAscending`
e cinco queries bounded: `IncomingBytes` (`Sum`, `Bytes`), `IncomingRecords`
(`Sum`, `Count`), `GetRecords.IteratorAgeMilliseconds` (`Maximum`,
`Milliseconds`), `ReadProvisionedThroughputExceeded` (`Average`, `Count`) e
`WriteProvisionedThroughputExceeded` (`Average`, `Count`). O período precisa
ser múltiplo de 60 entre 60 e 86400 segundos.

O artifact grava `kinesis.metrics.observations` como pontos com nome, valor,
unidade, estatística e `observed_at`, além da janela, definições de query,
respostas brutas e `metrics_missing`. Paginação é limitada; status incompleto,
resultado ausente e shape inválido ficam `unresolved`. A coleta não habilita
enhanced shard-level metrics, não reduz ausência a zero e não cria threshold,
causa, SLO ou economia.

### Managed Flink: janela CloudWatch read-only

`collect managed-flink --application-name <nome>` aceita as mesmas pontas
`--metrics-start <ISO8601>` e `--metrics-end <ISO8601>`, além de
`--metrics-period <segundos>`. A janela chama `cloudwatch.get_metric_data` no
namespace `AWS/KinesisAnalytics`, com dimensão `Application` igual ao nome da
aplicação e `ScanBy=TimestampAscending`. O contrato consulta cinco métricas de
aplicação: `cpuUtilization`, `heapMemoryUtilization`, `lastCheckpointDuration`,
`lastCheckpointSize` e `numberOfFailedCheckpoints`, com estatística/unidade
declaradas no artifact.

O artifact composto preserva `managed_flink.metrics.observations`, definições,
respostas raw, timestamps timezone-aware quando fornecidos pelo SDK,
`metrics_missing` e `unresolved`. Ausência não é zero; o collector não julga
threshold, SLO, causa, custo ou saúde. Métricas Task/Operator/Parallelism,
custom/connector metrics, job plan, replay e benchmark exigem evidência
separada.

## SLO observado de transporte

`sparkforge-aws analyze streaming-composition --mode slo` pode avaliar um SLO
declarado sobre `kafka.lag` ou `kinesis.shard` quando o chamador fornece
`--transport-key`. O valor é a identidade de um grupo/topic Kafka ou de um
stream Kinesis; a chave não é inferida pelo nome de arquivo, e grupos, topics,
streams ou shards diferentes não são agregados.

Kafka usa `lag` em `records`; Kinesis usa `iterator_age_ms` em `ms`. Cada
observação precisa trazer `timestamp` ou `observed_at` textual com timezone,
há pelo menos duas observações e o span observado cobre a janela do contrato.
O resultado preserva `source_fact_ids`, `transport_key`, `observation_source` e
`causal_inference: false`, com status `met` ou `violated`. Identidade, métrica,
unidade, timestamp ou cobertura ausente produz `streaming.slo.unresolved` e
`SF-STREAM-012`; violação observada produz `SF-STREAM-011`.

Esse diagnóstico de transporte isolado não prova freshness, disponibilidade,
sink health, causa, custo ou estado live. A avaliação SLO separada aceita p95
nearest-rank sobre a série observada, mas `kinesis.metric` sem timestamp não
vira série por ordem do arquivo, e CloudWatch não é consultado pelo compositor.

## Blind spots e sequência operacional

1. identificar origem, instante, comando/API e unidade do dump;
2. confirmar que a versão do serviço está declarada ou coletar o cluster real;
3. conferir se há partition/shard distribution antes de investigar skew;
4. coletar uma série com timestamps antes de afirmar tendência ou backlog;
5. cruzar transporte com `StreamingQueryProgress`, runtime, sink e resultado;
6. só então abrir regra, hipótese ou experimento.

O analyzer é offline, read-only e não aciona AWS. Não prova throughput,
capacidade, custo, exactly-once, perda de dados, hot partition ou compatibilidade
de versão sem os artefatos adicionais.

## Fontes

* https://kafka.apache.org/40/operations/basic-kafka-operations/
* https://kafka.apache.org/40/implementation/distribution/
* https://docs.aws.amazon.com/msk/latest/developerguide/consumer-lag.html
* https://docs.aws.amazon.com/msk/latest/developerguide/supported-kafka-versions.html
* https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html
* https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/get_metric_data.html
