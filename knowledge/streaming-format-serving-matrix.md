# Matriz streaming: Delta, Hudi e serving real-time

Esta página é conhecimento arquitetural P1/P2. As células indicam área de
investigação e compatibilidade declarada, não uma garantia para qualquer
combinação de versões. Sempre registrar Spark, Flink, Delta/Hudi, connector,
catalog e runtime gerenciado antes de dizer `supported`.

## Formatos lakehouse

| Formato | Streaming e evolução | Estado/CDC | Lacuna que mantém `unresolved` |
|---|---|---|---|
| Delta Lake | Structured Streaming reads/writes, checkpoint, schema evolution e merge | Change Data Feed, quando habilitado e suportado pela versão | versão Delta/Spark, protocolo da tabela, catálogo e operação de compaction |
| Apache Hudi COW | streaming writes e leitura incremental | COW, incremental query e CDC conforme tabela/configuração | versão Hudi/Spark, timeline, clustering/compaction e sink semantics |
| Apache Hudi MOR | streaming writes, leitura incremental e compaction assíncrona | MOR, CDC e Flink integration dependem do modo e release | versão Hudi/Flink, compaction, reader e consistência operacional |
| Apache Iceberg | Structured Streaming, snapshots e commit baseado em tabela | equality/position deletes e evolução conforme formato/runtime | cadência de commit, manutenção, catálogo e serving consumidor |

Não existe regra geral `Flink latest + Hudi latest = compatível`. Compatibilidade
é uma célula com versões, runtime e connector observados; sem isso, o resultado
é `unresolved`.

## Serving e analytics

| Sistema | Caminho de ingestão/query | Posicionamento | Limite para decisão |
|---|---|---|---|
| Amazon Redshift Streaming Ingestion | materialized view sobre Kinesis Data Streams ou Amazon MSK | serving analítico AWS nativo | região, modo de ingestão, refresh, schema, workload e custo |
| ClickHouse | Kafka engine/connector e materialized views | OLAP de baixa latência | versão, engine, ordenação, retenção e operação |
| Apache Pinot | realtime table com stream Kafka/Kinesis | analytics de baixa latência | schema/table config, segmentação, retenção e ingestão |
| Apache Druid | Kafka/Kinesis streaming ingestion | OLAP com ingestão contínua | supervisor, exactly-once no escopo documentado, segmentos e retenção |
| Trino Kafka connector | consulta federada sobre Kafka | query engine, não lakehouse durável | formato de mensagem, schema registry e semântica de consulta |
| Trino Iceberg connector | consulta federada sobre Iceberg | serving SQL sobre tabela lakehouse | catálogo, versão Trino/Iceberg e snapshot visibility |

## Fontes

- [Delta Lake structured streaming](https://docs.delta.io/latest/delta-streaming.html)
- [Delta Lake change data feed](https://docs.delta.io/latest/delta-change-data-feed.html)
- [Apache Hudi concepts](https://hudi.apache.org/docs/concepts/)
- [Apache Hudi incremental queries](https://hudi.apache.org/docs/querying_data/)
- [Apache Iceberg Spark Structured Streaming](https://iceberg.apache.org/docs/latest/spark-structured-streaming/)
- [Amazon Redshift streaming ingestion](https://docs.aws.amazon.com/redshift/latest/mgmt/materialized-view-streaming-ingestion.html)
- [ClickHouse Kafka engine](https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine)
- [Apache Pinot realtime ingestion](https://docs.pinot.apache.org/basics/data-import/realtime-ingestion)
- [Apache Druid streaming ingestion](https://druid.apache.org/docs/latest/ingestion/streaming/)
- [Trino Kafka connector](https://trino.io/docs/current/connector/kafka.html)
- [Trino Iceberg connector](https://trino.io/docs/current/connector/iceberg.html)
