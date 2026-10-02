# AWS Glue Streaming e Real-Time Mode

Status: conhecimento versionado em 2026-10-02. O documento descreve claims da
documentação oficial; a análise do Forge só afirma o que o dump traz.

## Contrato observado

Um dump offline pode declarar `glue_version`, `command`, `DefaultArguments` e
um bloco `stream` com fonte, modo, operações e capacidade. O extrator preserva
esses campos em `glue.streaming.*`; campo ausente vira `glue.streaming.unresolved`.
Ele não chama Glue, Kafka, CloudWatch nem infere partições a partir de worker
type ou nome de serviço.

## RTM

AWS documenta Real-Time Mode como modelo de execução de Structured Streaming no
Glue 6.0, habilitado por argumento explícito. A mesma documentação lista, para
esse recorte, Scala, fonte Kafka, operações stateless, output Update, workers
fixos e incompatibilidade com auto scaling; também alerta que partições sem task
slot podem ficar sem processamento. Essas são restrições de serviço e não podem
ser transferidas para Apache Spark upstream, Glue anterior ou outro runtime sem
fonte própria.

O Forge transforma configuração observada em Finding apenas quando o artifact
contract contém o campo correspondente. Se `partition_count` ou `task_slots`
faltar, o resultado é unresolved — nunca zero, “suficiente” ou “insuficiente”.

## Glue Streaming comum

Glue Streaming usa Spark Structured Streaming e documenta fontes como Kinesis,
Amazon MSK e Kafka autogerenciado, além de destinos como S3, JDBC e formatos de
tabela. Checkpoint é parte do controle de progresso do job; custo, latência e
capacidade dependem de medidas do workload e da região, portanto não são
deduzidos deste documento.

## Fonte

- [AWS Glue Streaming](https://docs.aws.amazon.com/glue/latest/dg/streaming-chapter.html)
- [Streaming ETL jobs in AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html)
