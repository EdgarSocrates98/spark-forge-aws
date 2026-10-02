# Streaming transport diagnostics

Esta página define o que um dump offline de Kafka, MSK ou Kinesis pode provar.
Ela não substitui collector, métrica temporal ou validação do runtime.

## Kafka

`sparkforge analyze transport --artifact kafka --path <dump.json>` aceita
descrição de topics/partitions, configs, consumer groups e offsets. Os facts
separam `kafka.topic`, `kafka.partition`, `kafka.consumer_group` e `kafka.lag`.
`replication_factor`, `isr_count`, offsets e lag são observações do dump; não são
limiares nem diagnóstico automático. Sem distribuição por partition, o Forge
deve pedir o artefato faltante antes de falar em hot partition.

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
