# Matriz de candidatos para arquitetura streaming

Esta página é uma matriz de capacidade declarada para apoiar decisões offline.
Ela não é benchmark, ranking, promessa de custo ou prova de disponibilidade.
O comando `sparkforge architecture streaming` usa somente constraints
explícitas do input; premissas ficam separadas e não eliminam candidatos.

## Candidatos e limites factuais

| Candidato | Papel | Capacidades usadas para eliminação | O que continua unresolved |
|---|---|---|---|
| Spark Structured Streaming | runtime | stateful, `foreachBatch`, modos append/update/complete, fontes conforme o conector declarado | latência, throughput, custo, versão e operação |
| Glue Streaming | runtime gerenciado | runtime Spark/Structured Streaming, fontes Kafka/Kinesis quando declaradas | worker, versão Glue, limites e custo |
| Glue Real-Time Mode | runtime gerenciado | somente constraints observadas no catálogo do produto; não assumir equivalência com Structured Streaming | state, API, source e capacidade precisam de artefato |
| Apache Flink | runtime | state, fontes e APIs Flink declaradas | versão, checkpoint/savepoint, operação e custo |
| Managed Service for Apache Flink | runtime gerenciado | state, fontes e APIs Flink declaradas | release AWS, IAM/VPC, métricas e custo |
| Kafka Streams | runtime | source Kafka, state stores e API Kafka Streams | broker, repartition, topologia, capacidade e custo |
| Iceberg lakehouse | sink | destino Iceberg declarado | engine, commit cadence, manutenção e serving |
| Redshift streaming | sink | destino Redshift declarado | latência, ingestão, schema, custo e workload analítico |

O analisador pode retornar `supported`, `unsupported` ou `unresolved` por
candidato. `supported` significa somente que nenhuma constraint fornecida o
eliminou; não significa que seja a melhor opção. Quando dois ou mais runtimes
permanecem viáveis, nenhum vencedor é fabricado.

## Requisitos versus premissas

`requirements` devem conter fatos que o dono do workload declarou: source,
sink, stateful, `for_each_batch`, output mode, API, exigência de serviço
gerenciado e outros limites verificáveis. `assumptions` documentam hipóteses
de projeto, como perfil de tráfego ou ownership. O motor não transforma uma
assumption em constraint.

## Fontes

- [Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [AWS Glue Streaming](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html)
- [AWS Glue Real-Time Data Processing](https://docs.aws.amazon.com/glue/latest/dg/glue-streaming.html)
- [Apache Flink stateful stream processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/streaming/)
- [Managed Service for Apache Flink developer guide](https://docs.aws.amazon.com/managed-flink/latest/java/what-is.html)
- [Kafka Streams introduction](https://kafka.apache.org/documentation/streams/)
- [Apache Iceberg Spark Structured Streaming](https://iceberg.apache.org/docs/latest/spark-structured-streaming/)
- [Amazon Redshift streaming ingestion](https://docs.aws.amazon.com/redshift/latest/mgmt/materialized-view-streaming-ingestion.html)
