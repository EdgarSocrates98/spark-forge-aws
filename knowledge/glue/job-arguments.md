# Argumentos de job Glue que afetam performance

Default arguments da job definition (Terraform / console / API). Confirmar suporte na versão do Glue antes de usar — argumento não suportado é ignorado silenciosamente ou falha o launch.

## 1. Observabilidade — habilitar antes de diagnosticar

| Argumento | Efeito |
|---|---|
| `--enable-spark-ui` | habilita Spark UI |
| `--spark-event-logs-path` | destino S3 dos event logs (**obrigatório** para History Server) |
| `--enable-continuous-cloudwatch-log` | logs contínuos em vez de só no fim |
| `--enable-observability-metrics` | métricas de observabilidade (Glue 4.0+) |
| `--enable-metrics` | métricas de job legadas |

Sem `--enable-spark-ui` **e** `--spark-event-logs-path` válidos, não há como diagnosticar produção depois do fato. Job crítico sem esses dois é um finding de observabilidade, independente de performance.

`--enable-observability-metrics` exige `glueContext` inicializado — ver `../cross-service-constraints.md` §3.

## 2. Capacidade

| Argumento / campo | Nota |
|---|---|
| `--enable-auto-scaling` | com ele, usar `MinCapacity`/`MaxCapacity`, **não** `NumberOfWorkers` |
| `--execution-class FLEX` | capacidade não garantida, custo menor; só para workload sem SLA |
| `WorkerType` / `NumberOfWorkers` | ver `workers-and-capacity.md` |
| `Timeout` | timeout do job; curto demais mata run legítimo, longo demais queima DPU em job travado |
| `MaxRetries` | retry de job inteiro; retry de job com escrita não idempotente duplica dado |
| `MaxConcurrentRuns` | > 1 com bookmarks causa `GLUE_JOB_BOOKMARK_VERSION_MISMATCH_ERROR` |

`MaxRetries` > 0 num job que faz append sem idempotência é risco de dado duplicado disfarçado de resiliência. Verificar se a escrita é idempotente antes de aceitar retry.

## 3. Formatos de data lake

| Argumento | Efeito |
|---|---|
| `--datalake-formats iceberg` (ou `hudi`, `delta`) | Glue carrega as libs e configura o catálogo |
| `--conf spark.sql.extensions=...IcebergSparkSessionExtensions` | extensão Iceberg |
| `--conf spark.sql.catalog.<nome>=org.apache.iceberg.spark.SparkCatalog` | catálogo |
| `--user-jars-first` | JAR do usuário ganha do embarcado — ver `../cross-service-constraints.md` §6 |

Usar `--datalake-formats` **e** fornecer JAR próprio é a combinação que gera conflito de classpath.

## 4. Bookmarks

| Argumento | Efeito |
|---|---|
| `--job-bookmark-option job-bookmark-enable` | liga |
| `--job-bookmark-option job-bookmark-disable` | desliga |
| `--job-bookmark-option job-bookmark-pause` | lê sem avançar o bookmark |

Bookmark **não é** CDC nem mecanismo de incremental universal. Para Iceberg, incremental deve usar leitura por snapshot, não bookmark. Bookmark tratado como incremental universal leva a reprocessamento ou a perda silenciosa de dados.

## 5. Dependências

| Argumento | Nota |
|---|---|
| `--extra-py-files` | `.py` / `.zip` / wheel |
| `--additional-python-modules` | instala do PyPI no bootstrap — adiciona tempo de startup |
| `--extra-jars` | JARs |
| `--python-modules-installer-option` | opções do instalador |
| `--TempDir` | diretório temporário |

`--additional-python-modules` com muitos pacotes pode dominar o tempo de um job curto. Em job de minutos, medir o tempo de bootstrap antes de otimizar o processamento.

## 6. Argumentos não-sobrescrevíveis

A job definition permite marcar argumentos como non-overridable. Útil para travar observabilidade e configuração de segurança, impedindo que um run ad-hoc os desligue.

Contrapartida: argumento travado que precisa mudar exige alterar a definição do job — e é fonte de confusão quando alguém tenta sobrescrever e não entende por que não pegou.

## 7. Precedência — a causa de "mudei e nada aconteceu"

Do mais fraco ao mais forte:

1. Default do Apache Spark
2. Default do Glue para a versão
3. `--conf` em default arguments (Terraform)
4. `SparkConf` na criação da sessão no script
5. `spark.conf.set(...)` em runtime

`spark.conf.set` no código sobrescreve o Terraform, silenciosamente. Ver `../spark/config-reference.md` §6, incluindo a lista de configs que **não** podem mudar após a sessão iniciar.

Diagnóstico: comparar os default arguments do IaC com o que o Spark UI mostra na aba *Environment*. Divergência = alguém sobrescreveu no código.

## 8. Segurança

Nunca colocar segredo em default argument: eles aparecem na job definition, na API e em logs. Usar Secrets Manager ou Parameter Store, referenciados por nome.

Revisão de IaC deve checar isso explicitamente — é finding de segurança, não de performance, e tem precedência.

## 9. Checklist de revisão de IaC

1. `--enable-spark-ui` e `--spark-event-logs-path` presentes e válidos?
2. `--enable-observability-metrics` presente (Glue 4.0+) e `glueContext` inicializado no código?
3. Auto Scaling coerente: `MinCapacity`/`MaxCapacity` sem `NumberOfWorkers`?
4. `MaxConcurrentRuns` coerente com bookmarks e com o SLA?
5. `MaxRetries` coerente com idempotência da escrita?
6. `Timeout` coerente com a duração real observada?
7. Argumentos compatíveis com a `glue_version`?
8. Args contraditórios entre si?
9. Algum arg também definido no código (precedência)?
10. Segredo em argumento?
11. `--execution-class` coerente com o SLA?
12. `--datalake-formats` coerente com JARs fornecidos?

## Fontes

- Using auto scaling for AWS Glue. https://docs.aws.amazon.com/glue/latest/dg/auto-scaling.html (retrieved 2026-07-29)
- Monitoring with AWS Glue Observability metrics (`--enable-observability-metrics`, requisito de `glueContext`). https://docs.aws.amazon.com/glue/latest/dg/monitor-observability.html (retrieved 2026-07-29)
- Introducing AWS Glue Flex jobs. https://aws.amazon.com/blogs/big-data/introducing-aws-glue-flex-jobs-cost-savings-on-etl-workloads/ (retrieved 2026-07-29)
- Improving AWS Glue performance. https://docs.aws.amazon.com/glue/latest/dg/performance.html (retrieved 2026-07-29)
- Nomes exatos e disponibilidade por versão de cada argumento devem ser confirmados na documentação de Glue job parameters do runtime em uso. Esta lista orienta a revisão, não substitui a referência.
