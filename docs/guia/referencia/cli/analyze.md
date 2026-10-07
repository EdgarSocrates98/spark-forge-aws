<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws analyze`

Extrai facts deterministicos de codigo-fonte.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws analyze airflow-dag`](#sparkforge-aws-analyze-airflow-dag) | Extrai facts do arquivo .py de um DAG do Apache Airflow, lido por AST e NUNCA executado: um fact por operador instanciado, com classe, task_id, os argumentos literais que as regras julgam (job_name, wait_for_completion, deferrable, stop_job_run_on_kill, retries, execution_timeout), as dependencias declaradas, e a marca do que nao e literal. |
| [`sparkforge-aws analyze athena-workgroup`](#sparkforge-aws-analyze-athena-workgroup) | Extrai facts de um dump JSON de workgroups do Athena. |
| [`sparkforge-aws analyze call-graph`](#sparkforge-aws-analyze-call-graph) | Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos. |
| [`sparkforge-aws analyze catalog-schema`](#sparkforge-aws-analyze-catalog-schema) | Extrai facts de um dump JSON do Glue Data Catalog. |
| [`sparkforge-aws analyze cdc`](#sparkforge-aws-analyze-cdc) | Extrai facts offline de dumps CDC, Debezium ou AWS DMS. |
| [`sparkforge-aws analyze cloudwatch`](#sparkforge-aws-analyze-cloudwatch) | Extrai facts de um artefato de metricas do CloudWatch ja coletado. |
| [`sparkforge-aws analyze cloudwatch-logs`](#sparkforge-aws-analyze-cloudwatch-logs) | Extrai facts do LOG do run ja coletado do CloudWatch Logs. |
| [`sparkforge-aws analyze consumers`](#sparkforge-aws-analyze-consumers) | Extrai facts do inventario declarado de consumidores de tabela. |
| [`sparkforge-aws analyze controlm-jobs`](#sparkforge-aws-analyze-controlm-jobs) | Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, job com Type/Name/RunAs/Application, agendamento (When), dependencia por evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE versionado, nunca execucao. Com --version, cruza as capacidades observadas com a matriz do Automation API e diz quais a versao declarada nao tem. |
| [`sparkforge-aws analyze data-observability`](#sparkforge-aws-analyze-data-observability) | Avalia SLI/SLO, error budget, incidentes e dependências offline. |
| [`sparkforge-aws analyze data-quality`](#sparkforge-aws-analyze-data-quality) | Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great Expectations e validacao artesanal): onde o check roda, se tem consequencia, e quantas passadas custa. |
| [`sparkforge-aws analyze dbt-artifacts`](#sparkforge-aws-analyze-dbt-artifacts) | Analisa manifest, catalog e run_results do dbt sem executar dbt. |
| [`sparkforge-aws analyze dq-ai`](#sparkforge-aws-analyze-dq-ai) | Extrai facts de manifesto Glue DQ BASIC/ADVANCED sem carregar linhas. |
| [`sparkforge-aws analyze duckdb-microscope`](#sparkforge-aws-analyze-duckdb-microscope) | Analisa bundle read-only de DuckDB/Parquet/Iceberg sem executar SQL. |
| [`sparkforge-aws analyze emr-cluster`](#sparkforge-aws-analyze-emr-cluster) | Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os cinco dumps que o completam). |
| [`sparkforge-aws analyze emr-eks`](#sparkforge-aws-analyze-emr-eks) | Extrai facts de um dump JSON de execucao Amazon EMR on EKS (describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe neste dump. |
| [`sparkforge-aws analyze emr-serverless`](#sparkforge-aws-analyze-emr-serverless) | Extrai facts de um dump JSON de application EMR Serverless (get-application). Descreve o PADRAO da application, nunca o que um job run executou -- StartJobRun sobrepoe. |
| [`sparkforge-aws analyze error-signatures`](#sparkforge-aws-analyze-error-signatures) | Casa knowledge/errors/ contra os facts do case. Derivacao pura. |
| [`sparkforge-aws analyze event-driven`](#sparkforge-aws-analyze-event-driven) | Extrai facts offline de EventBridge/Pipes, SQS e SNS. |
| [`sparkforge-aws analyze event-log`](#sparkforge-aws-analyze-event-log) | Extrai facts de um Spark event log (.jsonl) ja coletado. |
| [`sparkforge-aws analyze flink`](#sparkforge-aws-analyze-flink) | Extrai facts offline de dumps Apache Flink ou Managed Flink. |
| [`sparkforge-aws analyze forge-lab`](#sparkforge-aws-analyze-forge-lab) | Descreve topologia e cenários do Forge Lab sem executar Docker ou falhas. |
| [`sparkforge-aws analyze glue-job-runs`](#sparkforge-aws-analyze-glue-job-runs) | Extrai facts de historico do diretorio de artefatos de run Glue. |
| [`sparkforge-aws analyze glue-resource-link`](#sparkforge-aws-analyze-glue-resource-link) | Extrai a topologia do catalogo ja coletada: link, alvo e nome. |
| [`sparkforge-aws analyze glue-streaming`](#sparkforge-aws-analyze-glue-streaming) | Extrai facts offline de dumps AWS Glue Streaming/Real-Time Mode. |
| [`sparkforge-aws analyze graph`](#sparkforge-aws-analyze-graph) | Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: import e versao declarada, construcao do GraphFrame e persistencia dos dois DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige checkpoint sem que o modulo o configure. |
| [`sparkforge-aws analyze iam-access`](#sparkforge-aws-analyze-iam-access) | Extrai a DECISAO de IAM ja simulada, com a camada que decidiu. |
| [`sparkforge-aws analyze iceberg`](#sparkforge-aws-analyze-iceberg) | Extrai facts de um dump JSON das metadata tables Iceberg. |
| [`sparkforge-aws analyze lakeformation-grants`](#sparkforge-aws-analyze-lakeformation-grants) | Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings). |
| [`sparkforge-aws analyze lakehouse-catalog`](#sparkforge-aws-analyze-lakehouse-catalog) | Analisa topologia declarada de catalogs, engines, tabelas e bindings. |
| [`sparkforge-aws analyze orchestration`](#sparkforge-aws-analyze-orchestration) | Analisa mapa normalizado de Airflow, Dagster, Step Functions e Control-M. |
| [`sparkforge-aws analyze parquet-footer`](#sparkforge-aws-analyze-parquet-footer) | Extrai facts do FOOTER do Parquet ja coletado. |
| [`sparkforge-aws analyze plan`](#sparkforge-aws-analyze-plan) | Extrai facts do texto de um plano fisico (`df.explain("formatted")` / EXPLAIN FORMATTED). |
| [`sparkforge-aws analyze platform-ecosystem`](#sparkforge-aws-analyze-platform-ecosystem) | Analisa serving, ingestion, AI Data Engineering e radar opcional. |
| [`sparkforge-aws analyze platform-graph`](#sparkforge-aws-analyze-platform-graph) | Analisa Metadata Graph declarado e impacto de linhagem, sem acessar serviços externos. |
| [`sparkforge-aws analyze pyspark`](#sparkforge-aws-analyze-pyspark) | Extrai facts de PySpark via AST estatico (nunca importa o codigo). |
| [`sparkforge-aws analyze s3-listing`](#sparkforge-aws-analyze-s3-listing) | Extrai facts de um dump de `aws s3api list-objects-v2` (small files, compressao nao splitavel). |
| [`sparkforge-aws analyze schema-registry`](#sparkforge-aws-analyze-schema-registry) | Extrai facts offline de contratos e evolução de schemas. |
| [`sparkforge-aws analyze sfn-history`](#sparkforge-aws-analyze-sfn-history) | Extrai facts do HISTORICO de execucao de uma state machine do AWS Step Functions (a saida salva de `aws stepfunctions get-execution-history`): uma tentativa por par TaskScheduled/terminal, com ordem, resultado, duracao, erro e o JobRunId do Glue lido do output do TaskSubmitted. Le o que ACONTECEU, nunca a definicao. |
| [`sparkforge-aws analyze sql`](#sparkforge-aws-analyze-sql) | Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark. |
| [`sparkforge-aws analyze sql-metrics`](#sparkforge-aws-analyze-sql-metrics) | Extrai metrica por no do plano de um Spark event log ja coletado. |
| [`sparkforge-aws analyze step-functions`](#sparkforge-aws-analyze-step-functions) | Extrai facts da definicao ASL de uma state machine do AWS Step Functions (`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao. |
| [`sparkforge-aws analyze streaming`](#sparkforge-aws-analyze-streaming) | Extrai facts de fonte Structured Streaming ou StreamingQueryProgress. |
| [`sparkforge-aws analyze streaming-composition`](#sparkforge-aws-analyze-streaming-composition) | Compõe facts já extraídos de streaming, transporte e Iceberg. |
| [`sparkforge-aws analyze streaming-integrations`](#sparkforge-aws-analyze-streaming-integrations) | Extrai facts offline de checkpoints, Kafka Connect/Streams e OpenLineage. |
| [`sparkforge-aws analyze streaming-ops`](#sparkforge-aws-analyze-streaming-ops) | Extrai facts declarados de SLO, FinOps, segurança e serving streaming. |
| [`sparkforge-aws analyze terraform`](#sparkforge-aws-analyze-terraform) | Extrai facts de blocos aws_glue_job em HCL Terraform. |
| [`sparkforge-aws analyze terraform-diff`](#sparkforge-aws-analyze-terraform-diff) | Compara dois estados de um modulo Terraform e marca o que mudou. |
| [`sparkforge-aws analyze transport`](#sparkforge-aws-analyze-transport) | Extrai facts offline de dumps Kafka, MSK ou Kinesis. |
| [`sparkforge-aws analyze workload`](#sparkforge-aws-analyze-workload) | Extrai facts do inventario declarado de workload (workload.yaml: SLA e fonte primaria), que capacity, finops e workload consomem. |

## `sparkforge-aws analyze airflow-dag`

Extrai facts do arquivo .py de um DAG do Apache Airflow, lido por AST e NUNCA executado: um fact por operador instanciado, com classe, task_id, os argumentos literais que as regras julgam (job_name, wait_for_completion, deferrable, stop_job_run_on_kill, retries, execution_timeout), as dependencias declaradas, e a marca do que nao e literal.

```bash
sparkforge-aws analyze airflow-dag --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .py do DAG ou diretorio com eles (a pasta de DAGs). |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_airflow_dag`](../tools/sparkforge_aws_analyze_airflow_dag.md)

## `sparkforge-aws analyze athena-workgroup`

Extrai facts de um dump JSON de workgroups do Athena.

```bash
sparkforge-aws analyze athena-workgroup --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps de workgroups. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_athena_workgroup`](../tools/sparkforge_aws_analyze_athena_workgroup.md)

## `sparkforge-aws analyze call-graph`

Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos.

```bash
sparkforge-aws analyze call-graph --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto |  |  | Arquivo de facts gerado por `analyze pyspark --out`. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_call_graph`](../tools/sparkforge_aws_analyze_call_graph.md)

## `sparkforge-aws analyze catalog-schema`

Extrai facts de um dump JSON do Glue Data Catalog.

```bash
sparkforge-aws analyze catalog-schema --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps do catalogo. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_catalog_schema`](../tools/sparkforge_aws_analyze_catalog_schema.md)

## `sparkforge-aws analyze cdc`

Extrai facts offline de dumps CDC, Debezium ou AWS DMS.

```bash
sparkforge-aws analyze cdc --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON/JSONL. |
| `--artifact` | sim | `cdc`, `debezium`, `dms` |  |  | Vocabulário do dump: eventos CDC, Debezium ou AWS DMS. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cdc`](../tools/sparkforge_aws_analyze_cdc.md)

## `sparkforge-aws analyze cloudwatch`

Extrai facts de um artefato de metricas do CloudWatch ja coletado.

```bash
sparkforge-aws analyze cloudwatch --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON do CloudWatch. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch`](../tools/sparkforge_aws_analyze_cloudwatch.md), [`sparkforge_aws_analyze_event_log`](../tools/sparkforge_aws_analyze_event_log.md), [`sparkforge_aws_analyze_glue_job_runs`](../tools/sparkforge_aws_analyze_glue_job_runs.md), [`sparkforge_aws_analyze_sql_metrics`](../tools/sparkforge_aws_analyze_sql_metrics.md)

## `sparkforge-aws analyze cloudwatch-logs`

Extrai facts do LOG do run ja coletado do CloudWatch Logs.

```bash
sparkforge-aws analyze cloudwatch-logs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON de `collect cloudwatch-logs`, ou o DIRETORIO deles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch_logs`](../tools/sparkforge_aws_analyze_cloudwatch_logs.md), [`sparkforge_aws_analyze_error_signatures`](../tools/sparkforge_aws_analyze_error_signatures.md)

## `sparkforge-aws analyze consumers`

Extrai facts do inventario declarado de consumidores de tabela.

```bash
sparkforge-aws analyze consumers --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .yaml do inventario, ou diretorio com varios. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_consumers`](../tools/sparkforge_aws_analyze_consumers.md)

## `sparkforge-aws analyze controlm-jobs`

Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, job com Type/Name/RunAs/Application, agendamento (When), dependencia por evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE versionado, nunca execucao. Com --version, cruza as capacidades observadas com a matriz do Automation API e diz quais a versao declarada nao tem.

```bash
sparkforge-aws analyze controlm-jobs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .json ou diretorio com definicoes Jobs-as-Code. |
| `--version` | não | texto |  |  | A versao do Control-M Automation API do ambiente ALVO (9.0.21.200--9.0.22.100). E DECLARACAO do operador: o JSON de Jobs-as-Code nao a carrega, e deduzi-la do conteudo seria adivinhar. Sem ela o cruzamento com a matriz nao acontece e a regra SF-CTM-001 fica pulada por `requires_facts`. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_controlm_jobs`](../tools/sparkforge_aws_analyze_controlm_jobs.md)

## `sparkforge-aws analyze data-observability`

Avalia SLI/SLO, error budget, incidentes e dependências offline.

```bash
sparkforge-aws analyze data-observability --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON/YAML de observabilidade. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_data_observability`](../tools/sparkforge_aws_analyze_data_observability.md)

## `sparkforge-aws analyze data-quality`

Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great Expectations e validacao artesanal): onde o check roda, se tem consequencia, e quantas passadas custa.

```bash
sparkforge-aws analyze data-quality --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .py ou diretorio com codigo PySpark. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_data_quality`](../tools/sparkforge_aws_analyze_data_quality.md)

## `sparkforge-aws analyze dbt-artifacts`

Analisa manifest, catalog e run_results do dbt sem executar dbt.

```bash
sparkforge-aws analyze dbt-artifacts --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Diretório dbt ou manifest.json. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_dbt_artifacts`](../tools/sparkforge_aws_analyze_dbt_artifacts.md)

## `sparkforge-aws analyze dq-ai`

Extrai facts de manifesto Glue DQ BASIC/ADVANCED sem carregar linhas.

```bash
sparkforge-aws analyze dq-ai --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Manifesto JSON/YAML de recomendacao. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_dq_ai`](../tools/sparkforge_aws_analyze_dq_ai.md), [`sparkforge_aws_dq_ai_assess`](../tools/sparkforge_aws_dq_ai_assess.md)

## `sparkforge-aws analyze duckdb-microscope`

Analisa bundle read-only de DuckDB/Parquet/Iceberg sem executar SQL.

```bash
sparkforge-aws analyze duckdb-microscope --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON/YAML do microscópio DuckDB. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_duckdb_microscope`](../tools/sparkforge_aws_analyze_duckdb_microscope.md)

## `sparkforge-aws analyze emr-cluster`

Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os cinco dumps que o completam).

```bash
sparkforge-aws analyze emr-cluster --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps de cluster EMR. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_emr_cluster`](../tools/sparkforge_aws_analyze_emr_cluster.md)

## `sparkforge-aws analyze emr-eks`

Extrai facts de um dump JSON de execucao Amazon EMR on EKS (describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe neste dump.

```bash
sparkforge-aws analyze emr-eks --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps de execucao EMR on EKS. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_emr_eks`](../tools/sparkforge_aws_analyze_emr_eks.md)

## `sparkforge-aws analyze emr-serverless`

Extrai facts de um dump JSON de application EMR Serverless (get-application). Descreve o PADRAO da application, nunca o que um job run executou -- StartJobRun sobrepoe.

```bash
sparkforge-aws analyze emr-serverless --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps de application. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_emr_serverless`](../tools/sparkforge_aws_analyze_emr_serverless.md)

## `sparkforge-aws analyze error-signatures`

Casa knowledge/errors/ contra os facts do case. Derivacao pura.

```bash
sparkforge-aws analyze error-signatures --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto |  |  | Arquivo de facts com a UNIAO do case -- `spark.exception` do event log E `cloudwatch.log_event` do log. Metade dos facts nao produz metade das respostas: produz ponto cego que nao aparece. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch_logs`](../tools/sparkforge_aws_analyze_cloudwatch_logs.md), [`sparkforge_aws_analyze_error_signatures`](../tools/sparkforge_aws_analyze_error_signatures.md)

## `sparkforge-aws analyze event-driven`

Extrai facts offline de EventBridge/Pipes, SQS e SNS.

```bash
sparkforge-aws analyze event-driven --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_event_driven`](../tools/sparkforge_aws_analyze_event_driven.md)

## `sparkforge-aws analyze event-log`

Extrai facts de um Spark event log (.jsonl) ja coletado.

```bash
sparkforge-aws analyze event-log --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo de event log. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch`](../tools/sparkforge_aws_analyze_cloudwatch.md), [`sparkforge_aws_analyze_event_log`](../tools/sparkforge_aws_analyze_event_log.md), [`sparkforge_aws_analyze_glue_job_runs`](../tools/sparkforge_aws_analyze_glue_job_runs.md), [`sparkforge_aws_analyze_sql_metrics`](../tools/sparkforge_aws_analyze_sql_metrics.md)

## `sparkforge-aws analyze flink`

Extrai facts offline de dumps Apache Flink ou Managed Flink.

```bash
sparkforge-aws analyze flink --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON/JSONL. |
| `--artifact` | sim | `flink`, `managed_flink` |  |  | Vocabulário do dump: Flink upstream ou Managed Flink. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_flink`](../tools/sparkforge_aws_analyze_flink.md)

## `sparkforge-aws analyze forge-lab`

Descreve topologia e cenários do Forge Lab sem executar Docker ou falhas.

```bash
sparkforge-aws analyze forge-lab --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo YAML/JSON da topologia Forge Lab. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_forge_lab`](../tools/sparkforge_aws_analyze_forge_lab.md)

## `sparkforge-aws analyze glue-job-runs`

Extrai facts de historico do diretorio de artefatos de run Glue.

```bash
sparkforge-aws analyze glue-job-runs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | DIRETORIO de artefatos glue_job_run. |
| `--job-name` | sim | texto |  |  |  |
| `--cloudwatch` | não | texto |  |  | Diretorio de artefatos cloudwatch, para correlacionar por job_run_id. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch`](../tools/sparkforge_aws_analyze_cloudwatch.md), [`sparkforge_aws_analyze_event_log`](../tools/sparkforge_aws_analyze_event_log.md), [`sparkforge_aws_analyze_glue_job_runs`](../tools/sparkforge_aws_analyze_glue_job_runs.md), [`sparkforge_aws_analyze_sql_metrics`](../tools/sparkforge_aws_analyze_sql_metrics.md)

## `sparkforge-aws analyze glue-resource-link`

Extrai a topologia do catalogo ja coletada: link, alvo e nome.

```bash
sparkforge-aws analyze glue-resource-link --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON de `collect glue-resource-link`, ou o DIRETORIO deles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_glue_resource_link`](../tools/sparkforge_aws_analyze_glue_resource_link.md), [`sparkforge_aws_analyze_iam_access`](../tools/sparkforge_aws_analyze_iam_access.md), [`sparkforge_aws_analyze_lakeformation_grants`](../tools/sparkforge_aws_analyze_lakeformation_grants.md)

## `sparkforge-aws analyze glue-streaming`

Extrai facts offline de dumps AWS Glue Streaming/Real-Time Mode.

```bash
sparkforge-aws analyze glue-streaming --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON/JSONL. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_glue_streaming`](../tools/sparkforge_aws_analyze_glue_streaming.md)

## `sparkforge-aws analyze graph`

Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: import e versao declarada, construcao do GraphFrame e persistencia dos dois DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige checkpoint sem que o modulo o configure.

```bash
sparkforge-aws analyze graph --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .py ou diretorio com codigo PySpark. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_graph`](../tools/sparkforge_aws_analyze_graph.md)

## `sparkforge-aws analyze iam-access`

Extrai a DECISAO de IAM ja simulada, com a camada que decidiu.

```bash
sparkforge-aws analyze iam-access --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON de `collect iam-access`, ou o DIRETORIO deles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_glue_resource_link`](../tools/sparkforge_aws_analyze_glue_resource_link.md), [`sparkforge_aws_analyze_iam_access`](../tools/sparkforge_aws_analyze_iam_access.md), [`sparkforge_aws_analyze_lakeformation_grants`](../tools/sparkforge_aws_analyze_lakeformation_grants.md)

## `sparkforge-aws analyze iceberg`

Extrai facts de um dump JSON das metadata tables Iceberg.

```bash
sparkforge-aws analyze iceberg --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio com dumps das metadata tables. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_iceberg`](../tools/sparkforge_aws_analyze_iceberg.md)

## `sparkforge-aws analyze lakeformation-grants`

Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings).

```bash
sparkforge-aws analyze lakeformation-grants --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON de `collect lakeformation`, ou o DIRETORIO deles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_glue_resource_link`](../tools/sparkforge_aws_analyze_glue_resource_link.md), [`sparkforge_aws_analyze_iam_access`](../tools/sparkforge_aws_analyze_iam_access.md), [`sparkforge_aws_analyze_lakeformation_grants`](../tools/sparkforge_aws_analyze_lakeformation_grants.md)

## `sparkforge-aws analyze lakehouse-catalog`

Analisa topologia declarada de catalogs, engines, tabelas e bindings.

```bash
sparkforge-aws analyze lakehouse-catalog --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON/YAML da topologia de catalog. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_lakehouse_catalog`](../tools/sparkforge_aws_analyze_lakehouse_catalog.md)

## `sparkforge-aws analyze orchestration`

Analisa mapa normalizado de Airflow, Dagster, Step Functions e Control-M.

```bash
sparkforge-aws analyze orchestration --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON/YAML do control plane. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_orchestration`](../tools/sparkforge_aws_analyze_orchestration.md)

## `sparkforge-aws analyze parquet-footer`

Extrai facts do FOOTER do Parquet ja coletado.

```bash
sparkforge-aws analyze parquet-footer --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Artefato JSON de `collect parquet-footer`, ou o DIRETORIO deles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_parquet_footer`](../tools/sparkforge_aws_analyze_parquet_footer.md)

## `sparkforge-aws analyze plan`

Extrai facts do texto de um plano fisico (`df.explain("formatted")` / EXPLAIN FORMATTED).

```bash
sparkforge-aws analyze plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo de texto com a saida de explain. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_plan`](../tools/sparkforge_aws_analyze_plan.md)

## `sparkforge-aws analyze platform-ecosystem`

Analisa serving, ingestion, AI Data Engineering e radar opcional.

```bash
sparkforge-aws analyze platform-ecosystem --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON/YAML do inventário. |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_platform_ecosystem`](../tools/sparkforge_aws_analyze_platform_ecosystem.md)

## `sparkforge-aws analyze platform-graph`

Analisa Metadata Graph declarado e impacto de linhagem, sem acessar serviços externos.

```bash
sparkforge-aws analyze platform-graph --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo JSON ou YAML do Platform Intelligence Graph. |
| `--changed-node` | não | texto |  |  | ID da entidade alterada para calcular blast radius. |
| `--changed-attribute` | não | texto |  |  | Caminho de atributo declarado no nó alterado. |
| `--direction` | não | `downstream`, `upstream`, `both` |  | `downstream` |  |
| `--max-depth` | não | texto |  | `3` |  |
| `--max-items` | não | texto |  | `500` |  |
| `--out` | não | texto |  |  | Escreve o envelope completo em JSON. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_platform_graph`](../tools/sparkforge_aws_analyze_platform_graph.md)

## `sparkforge-aws analyze pyspark`

Extrai facts de PySpark via AST estatico (nunca importa o codigo).

```bash
sparkforge-aws analyze pyspark --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio a analisar. |
| `--upstream` | não | texto |  |  | Documento sparkforge_aws/upstream-facts/v1 com facts de outro motor (evidencia, nunca instrucao); entram no fim de `items`. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_pyspark`](../tools/sparkforge_aws_analyze_pyspark.md)

## `sparkforge-aws analyze s3-listing`

Extrai facts de um dump de `aws s3api list-objects-v2` (small files, compressao nao splitavel).

```bash
sparkforge-aws analyze s3-listing --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .json ou diretorio com paginas da listagem. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_s3_listing`](../tools/sparkforge_aws_analyze_s3_listing.md)

## `sparkforge-aws analyze schema-registry`

Extrai facts offline de contratos e evolução de schemas.

```bash
sparkforge-aws analyze schema-registry --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON/JSONL. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_schema_registry`](../tools/sparkforge_aws_analyze_schema_registry.md)

## `sparkforge-aws analyze sfn-history`

Extrai facts do HISTORICO de execucao de uma state machine do AWS Step Functions (a saida salva de `aws stepfunctions get-execution-history`): uma tentativa por par TaskScheduled/terminal, com ordem, resultado, duracao, erro e o JobRunId do Glue lido do output do TaskSubmitted. Le o que ACONTECEU, nunca a definicao.

```bash
sparkforge-aws analyze sfn-history --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .json salvo de get-execution-history, ou diretorio com eles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_sfn_history`](../tools/sparkforge_aws_analyze_sfn_history.md)

## `sparkforge-aws analyze sql`

Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark.

```bash
sparkforge-aws analyze sql --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | não | texto |  |  | Arquivo .sql a analisar. |
| `--from-pyspark` | não | texto |  |  | Arquivo .py: extrai texto de chamadas spark.sql("...") em vez de ler --path. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_sql`](../tools/sparkforge_aws_analyze_sql.md)

## `sparkforge-aws analyze sql-metrics`

Extrai metrica por no do plano de um Spark event log ja coletado.

```bash
sparkforge-aws analyze sql-metrics --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Event log em JSON Lines. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_cloudwatch`](../tools/sparkforge_aws_analyze_cloudwatch.md), [`sparkforge_aws_analyze_event_log`](../tools/sparkforge_aws_analyze_event_log.md), [`sparkforge_aws_analyze_glue_job_runs`](../tools/sparkforge_aws_analyze_glue_job_runs.md), [`sparkforge_aws_analyze_sql_metrics`](../tools/sparkforge_aws_analyze_sql_metrics.md)

## `sparkforge-aws analyze step-functions`

Extrai facts da definicao ASL de uma state machine do AWS Step Functions (`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao.

```bash
sparkforge-aws analyze step-functions --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo .json (ASL ou describe-state-machine) ou diretorio com eles. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_step_functions`](../tools/sparkforge_aws_analyze_step_functions.md)

## `sparkforge-aws analyze streaming`

Extrai facts de fonte Structured Streaming ou StreamingQueryProgress.

```bash
sparkforge-aws analyze streaming --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio a analisar. |
| `--artifact` | sim | `source`, `progress` |  |  | Tipo do artefato: fonte PySpark ou progresso JSON/JSONL. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_streaming`](../tools/sparkforge_aws_analyze_streaming.md)

## `sparkforge-aws analyze streaming-composition`

Compõe facts já extraídos de streaming, transporte e Iceberg.

```bash
sparkforge-aws analyze streaming-composition --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts gerado por um analyze; repetível para unir fontes. |
| `--mode` | sim | `iceberg`, `iceberg_temporal`, `observability`, `slo`, `temporal`, `pipeline` |  |  | Relação a analisar: streaming→Iceberg, janela streaming→Iceberg, progresso→transporte, SLO→progress/sink/transporte, janela temporal pareada ou contrato pipeline. |
| `--table` | não | texto |  | `` | Tabela Iceberg declarada. |
| `--query-name` | não | texto |  | `` | Query Structured Streaming declarada. |
| `--slo-name` | não | texto |  | `` | Nome do SLO declarado; obrigatório quando há mais de uma declaração. |
| `--transport-key` | não | texto |  | `` | Grupo/topic Kafka ou stream Kinesis declarado; obrigatório no mode=slo de transporte. |
| `--max-skew-seconds` | não | texto |  |  | Tolerância temporal declarada para modes temporal/iceberg_temporal; sem valor sai unresolved. |
| `--pipeline-path` | não | texto |  |  | Contrato JSON declarativo de nós/arestas; obrigatório quando mode=pipeline. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetível. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_streaming_composition`](../tools/sparkforge_aws_analyze_streaming_composition.md)

## `sparkforge-aws analyze streaming-integrations`

Extrai facts offline de checkpoints, Kafka Connect/Streams e OpenLineage.

```bash
sparkforge-aws analyze streaming-integrations --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretório JSON/JSONL. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetível. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_streaming_integrations`](../tools/sparkforge_aws_analyze_streaming_integrations.md)

## `sparkforge-aws analyze streaming-ops`

Extrai facts declarados de SLO, FinOps, segurança e serving streaming.

```bash
sparkforge-aws analyze streaming-ops --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretório JSON. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetível. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_streaming_ops`](../tools/sparkforge_aws_analyze_streaming_ops.md)

## `sparkforge-aws analyze terraform`

Extrai facts de blocos aws_glue_job em HCL Terraform.

```bash
sparkforge-aws analyze terraform --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio .tf a analisar. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_terraform`](../tools/sparkforge_aws_analyze_terraform.md)

## `sparkforge-aws analyze terraform-diff`

Compara dois estados de um modulo Terraform e marca o que mudou.

```bash
sparkforge-aws analyze terraform-diff --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--before` | sim | texto |  |  | Diretorio do estado anterior. |
| `--after` | sim | texto |  |  | Diretorio do estado proposto. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_terraform_diff`](../tools/sparkforge_aws_analyze_terraform_diff.md)

## `sparkforge-aws analyze transport`

Extrai facts offline de dumps Kafka, MSK ou Kinesis.

```bash
sparkforge-aws analyze transport --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio JSON/JSONL. |
| `--artifact` | sim | `kafka`, `msk`, `kinesis` |  |  | Vocabulário do dump: Kafka, MSK ou Kinesis. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_transport`](../tools/sparkforge_aws_analyze_transport.md)

## `sparkforge-aws analyze workload`

Extrai facts do inventario declarado de workload (workload.yaml: SLA e fonte primaria), que capacity, finops e workload consomem.

```bash
sparkforge-aws analyze workload --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo workload.yaml. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_aws_analyze_workload`](../tools/sparkforge_aws_analyze_workload.md)
