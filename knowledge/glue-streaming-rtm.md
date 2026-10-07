# AWS Glue Streaming e Real-Time Mode

Status: conhecimento versionado em 2026-10-03. O documento descreve claims da
documentação oficial; a análise do Forge só afirma o que o dump traz.

## Contrato observado

Um dump offline pode declarar `glue_version`, `command`, `DefaultArguments` e
um bloco `stream` com fonte, modo, operações e capacidade. O extrator preserva
esses campos em `glue.streaming.job` e pode preservar endpoints declarados em
`glue.streaming.source`/`glue.streaming.sink`; campo ausente vira
`glue.streaming.unresolved`.
Ele não chama Glue, Kafka, CloudWatch nem infere partições a partir de worker
type ou nome de serviço.

### Source e sink explícitos

O bloco `stream` pode declarar `sources`/`source` e `sinks`/`sink` como objeto
ou lista. O analyzer preserva identidade, tipo, connector, topic/stream/table,
formato, região, grupo, posição inicial, checkpoint e semântica de entrega
somente quando esses valores escalares estão presentes. Medidas aceitas são
fechadas por papel: partições/shards, lag/backlog, contadores de registros,
taxa, duração de batch e, no sink, commits e falhas.

`glue.streaming.source` e `glue.streaming.sink` são evidência do dump, não
prova de que o endpoint está ativo. Ausência de bloco, forma inválida, registro
inválido ou falta de medidas aparece em `glue.streaming.unresolved` com razão
nomeada. Campos aninhados são descartados; valores ausentes nunca viram zero.
Contadores não viram throughput sem timestamp e janela; `pending_commits` não
prova atraso de commit. Os motivos de ausência mais comuns são
`source_metrics_missing` e `sink_metrics_missing`. Nenhuma regra de saúde é
disparada por endpoint isolado.

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
sparkforge-aws analyze glue-streaming --path job.json --out glue.facts.json
sparkforge-aws analyze terraform --path infra/ --out tf.facts.json
sparkforge-aws fuse --facts glue.facts.json --facts tf.facts.json --out fused.json
sparkforge-aws judge --facts fused.json --show-skipped
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

## Definição efetiva e runs terminais

Quando também existir histórico de execução sanitizado, extraia os runs e
componha os facts com a definição efetiva:

```text
sparkforge-aws analyze glue-streaming --path job.json --out effective.facts.json
sparkforge-aws analyze glue-job-runs --path .sparkforge_aws/artifacts/glue_job_run --out runs.facts.json
sparkforge-aws fuse --facts effective.facts.json --facts runs.facts.json --out fused.facts.json
sparkforge-aws judge --facts fused.facts.json --show-skipped
```

`fuse` casa somente o nome literal de `glue.streaming.job` com o
`subject.job_name` de `glue.job_run`. `glue.streaming.runtime_link` compara
`glue_version`, `worker_type` e `worker_count`, preserva `observed_states`,
`observed_run_ids` e `source_fact_ids`, e nomeia `drifts` quando os valores não
coincidem. `SF-GLUESTREAM-006` aponta drift observado entre definição e run.

Ausência de run, identidade ambígua ou campo ausente gera
`glue.streaming.runtime.unresolved` e `SF-GLUESTREAM-007`; nunca vira igualdade.
`execution_time_s` e `DPUSeconds` continuam observações do run Glue: não são
latência de evento, saúde, throughput, custo atribuído ou prova de resultado
funcional. Essas perguntas exigem facts próprios, janela comparável e validação
funcional.

## Glue Streaming comum

Glue Streaming usa Spark Structured Streaming e documenta fontes como Kinesis,
Amazon MSK e Kafka autogerenciado, além de destinos como S3, JDBC e formatos de
tabela. Checkpoint é parte do controle de progresso do job; custo, latência e
capacidade dependem de medidas do workload e da região, portanto não são
deduzidos deste documento.

## Fonte

- [AWS Glue Streaming](https://docs.aws.amazon.com/glue/latest/dg/streaming-chapter.html)
- [Streaming ETL jobs in AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/add-job-streaming.html)
