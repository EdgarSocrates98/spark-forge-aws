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

## Glue efetivo e Terraform

Quando o operador possui os dois artefatos, extraia-os separadamente e passe os
facts pelo compositor já existente:

```text
sparkforge analyze glue-streaming --path job.json --out glue.facts.json
sparkforge analyze terraform --path infra/ --out tf.facts.json
sparkforge fuse --facts glue.facts.json --facts tf.facts.json --out fused.json
sparkforge judge --facts fused.json --show-skipped
```

O `fuse` casa somente `glue.streaming.job.attrs.name` com um
`tf.attribute` literal `name` de um `aws_glue_job`. O resultado
`glue.streaming.terraform_link` compara apenas quatro eixos que os dois
artefatos podem observar: `glue_version`, habilitação RTM, `language` e
`worker_count`. `source_fact_ids` mantém a trilha para reextração; o resumo não
reproduz o HCL nem o dump inteiro.

`SF-GLUESTREAM-004` aponta drift literal entre configuração efetiva e IaC.
`SF-GLUESTREAM-005` aponta identidade ou campo não resolvido. Nome de recurso,
valor interpolado, ausência de atributo e ausência de execução não são tratados
como igualdade. O link não prova `terraform apply`, runtime live, capacidade,
latência, custo ou resultado funcional.

## Glue Streaming comum

Glue Streaming usa Spark Structured Streaming e documenta fontes como Kinesis,
Amazon MSK e Kafka autogerenciado, além de destinos como S3, JDBC e formatos de
tabela. Checkpoint é parte do controle de progresso do job; custo, latência e
capacidade dependem de medidas do workload e da região, portanto não são
deduzidos deste documento.

## Fonte

- [AWS Glue Streaming](https://docs.aws.amazon.com/glue/latest/dg/streaming-chapter.html)
- [Streaming ETL jobs in AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html)
