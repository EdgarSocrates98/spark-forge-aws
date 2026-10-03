# Matriz de runtime para streaming

Esta matriz separa release upstream, serviço gerenciado e runtime observado.
Ela é evidência de pesquisa, não autorização para usar uma feature: regras só
podem julgar um caso quando o artefato fornece o runtime efetivo e o guard da
regra o aceita.

Data da revalidação: 2026-10-02.

## Releases revalidadas

| Produto | Escopo | Estado | Versão/referência revalidada | Limite que permanece |
|---|---|---|---|---|
| Apache Spark | upstream | `VERIFIED` | 4.2.0 estável; 4.1.3 e 4.0.4 também aparecem como releases estáveis | O runtime gerenciado pode carregar fork, patch ou versão diferente; `Trigger.RealTime` não é transferido automaticamente |
| Apache Kafka | upstream | `VERIFIED` | 4.3.1 é release suportada; 4.2.2 e 4.1.2 também estão na lista suportada | Compatibilidade de clientes, brokers e conectores depende da combinação efetiva |
| Amazon MSK | serviço gerenciado | `UNRESOLVED` | A AWS mantém tabela própria de versões suportadas e datas de fim de suporte | Este checkout não contém snapshot regional/broker-type da tabela; coletar `describe-cluster` e conferir a página atual antes de aplicar guard |
| Apache Flink | upstream | `VERIFIED` | 2.3.0 é a release estável mais recente | Conector, Java, state backend e deployment precisam ser observados no job |
| Managed Service for Apache Flink | serviço gerenciado | `UNRESOLVED` | Não derivar release do Flink upstream | A aplicação e a região precisam fornecer runtime, configuração, IAM/VPC e métricas; não há matriz AWS local suficiente |
| AWS Glue Streaming | serviço gerenciado | `VERIFIED` | Glue 6.0 documenta Structured Streaming e RTM | Workers, partições e runtime efetivo continuam dependentes do job/run |
| AWS Glue Real-Time Mode | capability gerenciada | `VERIFIED` com escopo | Glue 6.0; Kafka; Scala; stateless; output `Update`; sem auto scaling | Kinesis e operações stateful não devem ser presumidos como compatíveis; capacidade exige partições e task slots observados |
| Kinesis Data Streams | serviço | `N/A + motivo` | Não possui release de engine equivalente; é serviço regional | Capacidade, resharding, KCL/EFO e série longa exigem coleta temporal; o collector SparkForge cobre somente cinco métricas stream-level bounded do CloudWatch quando a janela é declarada |
| Apache Iceberg | formato/sink | `N/A + motivo` | Compatibilidade é por engine, catálogo e versão do formato | A combinação Spark/Glue/Iceberg deve vir do runtime e metadata observados |

## Regras de leitura

1. `VERIFIED` aqui significa que a fonte oficial foi reconsultada na data
   acima. Não significa que o caso local roda nessa versão.
2. `UNRESOLVED` preserva uma lacuna de serviço/região que não pode ser
   preenchida por uma release upstream.
3. `N/A + motivo` significa que o conceito de release não se aplica; métricas
   e capacidade continuam aplicáveis por artefatos próprios.
4. Divergência entre este documento, o dump de runtime e o event log deve virar
   divergência de ambiente, nunca escolha silenciosa de uma fonte.

## Fontes

- https://spark.apache.org/releases/
- https://spark.apache.org/news/
- https://kafka.apache.org/community/downloads/
- https://flink.apache.org/downloads/
- https://flink.apache.org/2026/06/25/apache-flink-2.3.0-release-announcement/
- https://docs.aws.amazon.com/en_en/msk/latest/developerguide/version-support.html
- https://docs.aws.amazon.com/glue/latest/dg/streaming-chapter.html
- https://docs.aws.amazon.com/managed-flink/latest/java/what-is.html
- https://iceberg.apache.org/docs/latest/spark-structured-streaming/
