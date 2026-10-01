# Observabilidade AWS Glue — métricas exatas

Disponível em **AWS Glue 4.0 e superior**. Habilitar com o default argument:

```
--enable-observability-metrics = true
```

Requisito: `glueContext` precisa estar inicializado para as métricas serem publicadas. Job PySpark puro que nunca cria `glueContext` **não emite** essas métricas — armadilha comum em jobs escritos como Spark puro.

Namespace CloudWatch: `Glue`. Dimensões: `JobName`, `JobRunId` (ou `ALL`), `Type` (`gauge`/`count`), `ObservabilityGroup`. Publicação a cada 30 s.

## 1. Performance

| Métrica | Unidade | O que prova |
|---|---|---|
| `glue.driver.skewness.stage` | Count | Razão entre duração máxima e mediana de task no stage, normalizada pelo fator de skew. `0` = razão abaixo do fator. `1` = razão é 2× o fator |
| `glue.driver.skewness.job` | Count | Máximo das skewness de stage **ponderadas pela duração do stage** |

Fator de skew default: **5**. Override:

```
spark.metrics.conf.driver.source.glue.jobPerformance.skewnessFactor
```

`skewness.job` ponderar pela duração é o detalhe que importa: um stage muito skewed mas curtíssimo não polui a métrica. Se `skewness.job` está alto, o skew é economicamente relevante — não é ruído.

`skewness.stage` atualiza a cada 30 s; o valor no fim do stage é o final.

## 2. Resource utilization

| Métrica | Unidade |
|---|---|
| `glue.driver.workerUtilization` | Percentage |
| `glue.driver.memory.heap.[available\|used]` | Bytes |
| `glue.driver.memory.heap.used.percentage` | Percentage |
| `glue.driver.memory.non-heap.[available\|used]` | Bytes |
| `glue.driver.memory.non-heap.used.percentage` | Percentage |
| `glue.driver.memory.total.[available\|used]` | Bytes |
| `glue.driver.memory.total.used.percentage` | Percentage |
| `glue.ALL.memory.heap.[available\|used]` | Bytes |
| `glue.ALL.memory.heap.used.percentage` | Percentage |
| `glue.ALL.memory.non-heap.[available\|used]` | Bytes |
| `glue.ALL.memory.non-heap.used.percentage` | Percentage |
| `glue.ALL.memory.total.[available\|used]` | Bytes |
| `glue.ALL.memory.total.used.percentage` | Percentage |
| `glue.driver.disk.[available_GB\|used_GB]` | Gigabytes |
| `glue.driver.disk.used.percentage` | Percentage |
| `glue.ALL.disk.[available_GB\|used_GB]` | Gigabytes |
| `glue.ALL.disk.used.percentage` | Percentage |

`ALL` = todos os executores. A existência de `heap`, `non-heap` **e** `total` separados é o que permite distinguir OOM de heap de OOM de container/overhead sem ler log — ver `../spark/memory-and-oom.md` §2.

`workerUtilization` baixo com runtime alto é o sinal mais direto de superprovisão. É o candidato número um a Auto Scaling.

## 3. Throughput

| Métrica | Dimensão extra | Unidade |
|---|---|---|
| `glue.driver.bytesRead` | `Source` | Bytes |
| `glue.driver.recordsRead` | `Source` | Count |
| `glue.driver.filesRead` | `Source` | Count |
| `glue.driver.partitionsRead` | `Source` | Count |
| `glue.driver.bytesWrittten` | `Sink` | Bytes |
| `glue.driver.recordsWritten` | `Sink` | Count |
| `glue.driver.filesWritten` | `Sink` | Count |

`bytesWrittten` tem grafia com três `t` na documentação da AWS. Reproduzir exatamente assim em query CloudWatch — não "corrigir".

`filesRead` e `filesWritten` são a métrica de small files mais direta que existe: `filesWritten` alto com `bytesWritten` modesto é fragmentação sendo criada agora.

`partitionsRead` alto para uma query que deveria ser seletiva prova falha de partition pruning.

### Limitações de throughput

- DataFrame e DynamicFrame baseado em DataFrame (JDBC, Parquet em S3) são suportados. DynamicFrame baseado em RDD (CSV, JSON em S3) **não**. Regra: o que aparece no Spark UI é suportado.
- `recordsRead` só é emitido quando a fonte é tabela do catálogo e o formato é JSON, CSV, text ou **Iceberg**.
- `recordsWritten`, `bytesWritten` e `filesWritten` **não** estão disponíveis para JDBC e **tabelas Iceberg**.
- Job que termina em ~1 minuto pode não ter métrica de throughput no CloudWatch.

A terceira limitação é séria para este projeto: **em pipeline Iceberg não é possível medir escrita por essas métricas.** Para Iceberg, medir escrita pelas metadata tables (`files`, `snapshots`) — ver `../storage/iceberg-performance.md`.

## 4. Reliability — categorias de erro

`glue.succeed.ALL` e `glue.error.ALL` (Count, SUM). Além disso, `glue.error.[categoria]` é setado em 1 quando o run falha. 28 categorias:

| Categoria | Quando |
|---|---|
| `OUT_OF_MEMORY_ERROR` | sem memória no driver **ou** executor |
| `DISK_NO_SPACE_ERROR` | sem espaço em disco no driver ou executor |
| `THROTTLING_ERROR` | limite de concorrência ou quota de serviço |
| `DATA_LAKE_FRAMEWORK_ERROR` | erro vindo de Hudi, Iceberg, etc. |
| `GLUE_JOB_BOOKMARK_VERSION_MISMATCH_ERROR` | mesmo job concorrente sobre a mesma origem |
| `TIMEOUT_ERROR` / `GLUE_OPERATION_TIMEOUT_ERROR` | timeout genérico / de operação Glue |
| `QUERY_ERROR` | execução de Spark SQL |
| `SYNTAX_ERROR` / `COMPILATION_ERROR` | sintaxe no script / compilação Scala |
| `IMPORT_ERROR` | import de dependência |
| `INVALID_ARGUMENT_ERROR` | argumento inválido |
| `PERMISSION_ERROR` | falta de permissão |
| `RESOURCE_NOT_FOUND_ERROR` | dado ou location inexistente |
| `RESOURCES_ALREADY_EXISTS_ERROR` | recurso já existe |
| `CONNECTION_ERROR` | conexão a serviço/host/banco |
| `UNSUPPORTED_OPERATION_ERROR` | operação não suportada |
| `LAUNCH_ERROR` | fase de lançamento do job |
| `SYSTEM_EXIT_ERROR` | exit de sistema |
| `S3_ERROR`, `DYNAMODB_ERROR`, `REDSHIFT_ERROR`, `LAKEFORMATION_ERROR`, `GLUE_ERROR` | erros genéricos por serviço |
| `GLUE_INTERNAL_SERVICE_ERROR`, `GLUE_VALIDATION_ERROR` | serviço Glue |
| `UNCLASSIFIED_SPARK_ERROR`, `UNCLASSIFIED_ERROR` | não classificado |

Notas de diagnóstico:

- `OUT_OF_MEMORY_ERROR` **não** distingue driver de executor. Para separar, cruzar com `glue.driver.memory.*` vs `glue.ALL.memory.*`.
- `DISK_NO_SPACE_ERROR` sendo categoria separada confirma que disco é falha distinta de OOM — não tratar como sinônimo.
- `GLUE_JOB_BOOKMARK_VERSION_MISMATCH_ERROR` é sinal de concorrência indevida: `max concurrent runs` > 1 sobre a mesma origem.
- Ausência de OOM na categoria com executor desaparecendo aponta para overhead/container.

## 5. Análise longitudinal

O valor real dessas métricas não é o run isolado — é a série. Com `JobRunId = ALL`, dá para ver: tendência de `workerUtilization` (superprovisão crescendo), tendência de `filesWritten` (fragmentação acumulando), tendência de heap do driver run a run (vazamento), e distribuição de categoria de erro ao longo do tempo (qual falha vale corrigir primeiro).

Um job que falha por OOM "depois de horas" (`../spark/memory-and-oom.md` §3) só se diagnostica assim: heap do driver **ao longo** do run, não o pico.

## 6. Retenção de métrica por período

A granularidade do ponto decide por quanto tempo o CloudWatch o guarda. A tabela está em
[`observability.yaml`](observability.yaml), legível por máquina e carregada por
`sparkforge/facts/cloudwatch_retention.py` — não é repetida aqui de propósito: duas cópias do
mesmo número divergem, e a que o código lê é a do YAML.

Consequência prática: consultar um run antigo com período curto devolve série vazia. Vazio por
expiração e vazio por observabilidade desligada no job têm remédios opostos, e a saída precisa
dizer qual dos dois é.

## Fontes

- Monitoring with AWS Glue Observability metrics — todos os nomes de métrica, dimensões, unidades, limitações e as 28 categorias de erro. https://docs.aws.amazon.com/glue/latest/dg/monitor-observability.html (retrieved 2026-07-29)
- Enhance monitoring and debugging for AWS Glue jobs using new job observability metrics. https://aws.amazon.com/blogs/big-data/enhance-monitoring-and-debugging-for-aws-glue-jobs-using-new-job-observability-metrics/ (retrieved 2026-07-29)
- Amazon CloudWatch concepts — retenção de dados de métrica por granularidade. https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html (retrieved 2026-08-26)
- Seção 5 é prática de campo, não documentação.
