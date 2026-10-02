# Streaming, Iceberg e observabilidade

Este pack descreve o contrato composto introduzido pela Wave G. O core não
consulta Spark, Kafka, Kinesis, CloudWatch ou Iceberg: ele recebe Facts já
extraídos e exige que o chamador declare a identidade do vínculo.

## Vínculo streaming → Iceberg

`streaming.iceberg.link` preserva query, tabela, ids dos Facts de progresso e
metadata Iceberg, operações de snapshot e, quando disponível, resumo de data
files. `non_append_observed` é uma observação de operação, não uma conclusão de
falha. Leitura incremental e comportamento de overwrite/delete precisam ser
validados para o runtime e consumidor presentes.

## Vínculo progresso → transporte

`streaming.observability.link` aproxima uma série `StreamingQueryProgress` de
medidas Kafka lag ou Kinesis iterator age somente quando o grupo/topic/stream é
declarado e encontrado. O resultado carrega `causal_inference: false`: lag
correlacionado a processamento abaixo da entrada orienta a coleta seguinte, mas
não escolhe source, state, sink, throttling ou capacidade como causa.

## Pontos cegos

Sem query, tabela, grupo ou stream declarados, o compositor emite
`streaming.composition.unresolved`. Zero não é usado como default para medida
ausente. Uma única amostra não é tendência; uma ausência de finding não prova
saúde.

## Fontes oficiais

- Apache Spark Structured Streaming: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- Apache Iceberg Spark Structured Streaming: https://iceberg.apache.org/docs/latest/spark-structured-streaming/
- Amazon Kinesis CloudWatch monitoring: https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html
- Amazon MSK consumer lag: https://docs.aws.amazon.com/msk/latest/developerguide/consumer-lag.html
