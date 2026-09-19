<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge analyze`

Extrai facts deterministicos de codigo-fonte.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge analyze athena-workgroup`](#sparkforge-analyze-athena-workgroup) | Extrai facts de um dump JSON de workgroups do Athena. |
| [`sparkforge analyze call-graph`](#sparkforge-analyze-call-graph) | Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos. |
| [`sparkforge analyze catalog-schema`](#sparkforge-analyze-catalog-schema) | Extrai facts de um dump JSON do Glue Data Catalog. |
| [`sparkforge analyze cloudwatch`](#sparkforge-analyze-cloudwatch) | Extrai facts de um artefato de metricas do CloudWatch ja coletado. |
| [`sparkforge analyze cloudwatch-logs`](#sparkforge-analyze-cloudwatch-logs) | Extrai facts do LOG do run ja coletado do CloudWatch Logs. |
| [`sparkforge analyze consumers`](#sparkforge-analyze-consumers) | Extrai facts do inventario declarado de consumidores de tabela. |
| [`sparkforge analyze controlm-jobs`](#sparkforge-analyze-controlm-jobs) | Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, job com Type/Name/RunAs/Application, agendamento (When), dependencia por evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE versionado, nunca execucao. Com --version, cruza as capacidades observadas com a matriz do Automation API e diz quais a versao declarada nao tem. |
| [`sparkforge analyze data-quality`](#sparkforge-analyze-data-quality) | Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great Expectations e validacao artesanal): onde o check roda, se tem consequencia, e quantas passadas custa. |
| [`sparkforge analyze emr-cluster`](#sparkforge-analyze-emr-cluster) | Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os cinco dumps que o completam). |
| [`sparkforge analyze emr-eks`](#sparkforge-analyze-emr-eks) | Extrai facts de um dump JSON de execucao Amazon EMR on EKS (describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe neste dump. |
| [`sparkforge analyze emr-serverless`](#sparkforge-analyze-emr-serverless) | Extrai facts de um dump JSON de application EMR Serverless (get-application). Descreve o PADRAO da application, nunca o que um job run executou -- StartJobRun sobrepoe. |
| [`sparkforge analyze error-signatures`](#sparkforge-analyze-error-signatures) | Casa knowledge/errors/ contra os facts do case. Derivacao pura. |
| [`sparkforge analyze event-log`](#sparkforge-analyze-event-log) | Extrai facts de um Spark event log (.jsonl) ja coletado. |
| [`sparkforge analyze glue-job-runs`](#sparkforge-analyze-glue-job-runs) | Extrai facts de historico do diretorio de artefatos de run Glue. |
| [`sparkforge analyze glue-resource-link`](#sparkforge-analyze-glue-resource-link) | Extrai a topologia do catalogo ja coletada: link, alvo e nome. |
| [`sparkforge analyze graph`](#sparkforge-analyze-graph) | Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: import e versao declarada, construcao do GraphFrame e persistencia dos dois DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige checkpoint sem que o modulo o configure. |
| [`sparkforge analyze iam-access`](#sparkforge-analyze-iam-access) | Extrai a DECISAO de IAM ja simulada, com a camada que decidiu. |
| [`sparkforge analyze iceberg`](#sparkforge-analyze-iceberg) | Extrai facts de um dump JSON das metadata tables Iceberg. |
| [`sparkforge analyze lakeformation-grants`](#sparkforge-analyze-lakeformation-grants) | Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings). |
| [`sparkforge analyze parquet-footer`](#sparkforge-analyze-parquet-footer) | Extrai facts do FOOTER do Parquet ja coletado. |
| [`sparkforge analyze plan`](#sparkforge-analyze-plan) | Extrai facts do texto de um plano fisico (`df.explain("formatted")` / EXPLAIN FORMATTED). |
| [`sparkforge analyze pyspark`](#sparkforge-analyze-pyspark) | Extrai facts de PySpark via AST estatico (nunca importa o codigo). |
| [`sparkforge analyze s3-listing`](#sparkforge-analyze-s3-listing) | Extrai facts de um dump de `aws s3api list-objects-v2` (small files, compressao nao splitavel). |
| [`sparkforge analyze sql`](#sparkforge-analyze-sql) | Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark. |
| [`sparkforge analyze sql-metrics`](#sparkforge-analyze-sql-metrics) | Extrai metrica por no do plano de um Spark event log ja coletado. |
| [`sparkforge analyze step-functions`](#sparkforge-analyze-step-functions) | Extrai facts da definicao ASL de uma state machine do AWS Step Functions (`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao. |
| [`sparkforge analyze terraform`](#sparkforge-analyze-terraform) | Extrai facts de blocos aws_glue_job em HCL Terraform. |
| [`sparkforge analyze terraform-diff`](#sparkforge-analyze-terraform-diff) | Compara dois estados de um modulo Terraform e marca o que mudou. |
| [`sparkforge analyze workload`](#sparkforge-analyze-workload) | Extrai facts do inventario declarado de workload (workload.yaml: SLA e fonte primaria), que capacity, finops e workload consomem. |

## `sparkforge analyze athena-workgroup`

Extrai facts de um dump JSON de workgroups do Athena.

```bash
sparkforge analyze athena-workgroup --help
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

[`sparkforge_analyze_athena_workgroup`](../tools/sparkforge_analyze_athena_workgroup.md)

## `sparkforge analyze call-graph`

Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos.

```bash
sparkforge analyze call-graph --help
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

[`sparkforge_analyze_call_graph`](../tools/sparkforge_analyze_call_graph.md)

## `sparkforge analyze catalog-schema`

Extrai facts de um dump JSON do Glue Data Catalog.

```bash
sparkforge analyze catalog-schema --help
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

[`sparkforge_analyze_catalog_schema`](../tools/sparkforge_analyze_catalog_schema.md)

## `sparkforge analyze cloudwatch`

Extrai facts de um artefato de metricas do CloudWatch ja coletado.

```bash
sparkforge analyze cloudwatch --help
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

[`sparkforge_analyze_cloudwatch`](../tools/sparkforge_analyze_cloudwatch.md), [`sparkforge_analyze_event_log`](../tools/sparkforge_analyze_event_log.md), [`sparkforge_analyze_glue_job_runs`](../tools/sparkforge_analyze_glue_job_runs.md), [`sparkforge_analyze_sql_metrics`](../tools/sparkforge_analyze_sql_metrics.md)

## `sparkforge analyze cloudwatch-logs`

Extrai facts do LOG do run ja coletado do CloudWatch Logs.

```bash
sparkforge analyze cloudwatch-logs --help
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

[`sparkforge_analyze_cloudwatch_logs`](../tools/sparkforge_analyze_cloudwatch_logs.md), [`sparkforge_analyze_error_signatures`](../tools/sparkforge_analyze_error_signatures.md)

## `sparkforge analyze consumers`

Extrai facts do inventario declarado de consumidores de tabela.

```bash
sparkforge analyze consumers --help
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

[`sparkforge_analyze_consumers`](../tools/sparkforge_analyze_consumers.md)

## `sparkforge analyze controlm-jobs`

Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, job com Type/Name/RunAs/Application, agendamento (When), dependencia por evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE versionado, nunca execucao. Com --version, cruza as capacidades observadas com a matriz do Automation API e diz quais a versao declarada nao tem.

```bash
sparkforge analyze controlm-jobs --help
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

[`sparkforge_analyze_controlm_jobs`](../tools/sparkforge_analyze_controlm_jobs.md)

## `sparkforge analyze data-quality`

Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great Expectations e validacao artesanal): onde o check roda, se tem consequencia, e quantas passadas custa.

```bash
sparkforge analyze data-quality --help
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

[`sparkforge_analyze_data_quality`](../tools/sparkforge_analyze_data_quality.md)

## `sparkforge analyze emr-cluster`

Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os cinco dumps que o completam).

```bash
sparkforge analyze emr-cluster --help
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

[`sparkforge_analyze_emr_cluster`](../tools/sparkforge_analyze_emr_cluster.md)

## `sparkforge analyze emr-eks`

Extrai facts de um dump JSON de execucao Amazon EMR on EKS (describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe neste dump.

```bash
sparkforge analyze emr-eks --help
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

[`sparkforge_analyze_emr_eks`](../tools/sparkforge_analyze_emr_eks.md)

## `sparkforge analyze emr-serverless`

Extrai facts de um dump JSON de application EMR Serverless (get-application). Descreve o PADRAO da application, nunca o que um job run executou -- StartJobRun sobrepoe.

```bash
sparkforge analyze emr-serverless --help
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

[`sparkforge_analyze_emr_serverless`](../tools/sparkforge_analyze_emr_serverless.md)

## `sparkforge analyze error-signatures`

Casa knowledge/errors/ contra os facts do case. Derivacao pura.

```bash
sparkforge analyze error-signatures --help
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

[`sparkforge_analyze_cloudwatch_logs`](../tools/sparkforge_analyze_cloudwatch_logs.md), [`sparkforge_analyze_error_signatures`](../tools/sparkforge_analyze_error_signatures.md)

## `sparkforge analyze event-log`

Extrai facts de um Spark event log (.jsonl) ja coletado.

```bash
sparkforge analyze event-log --help
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

[`sparkforge_analyze_cloudwatch`](../tools/sparkforge_analyze_cloudwatch.md), [`sparkforge_analyze_event_log`](../tools/sparkforge_analyze_event_log.md), [`sparkforge_analyze_glue_job_runs`](../tools/sparkforge_analyze_glue_job_runs.md), [`sparkforge_analyze_sql_metrics`](../tools/sparkforge_analyze_sql_metrics.md)

## `sparkforge analyze glue-job-runs`

Extrai facts de historico do diretorio de artefatos de run Glue.

```bash
sparkforge analyze glue-job-runs --help
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

[`sparkforge_analyze_cloudwatch`](../tools/sparkforge_analyze_cloudwatch.md), [`sparkforge_analyze_event_log`](../tools/sparkforge_analyze_event_log.md), [`sparkforge_analyze_glue_job_runs`](../tools/sparkforge_analyze_glue_job_runs.md), [`sparkforge_analyze_sql_metrics`](../tools/sparkforge_analyze_sql_metrics.md)

## `sparkforge analyze glue-resource-link`

Extrai a topologia do catalogo ja coletada: link, alvo e nome.

```bash
sparkforge analyze glue-resource-link --help
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

[`sparkforge_analyze_glue_resource_link`](../tools/sparkforge_analyze_glue_resource_link.md), [`sparkforge_analyze_iam_access`](../tools/sparkforge_analyze_iam_access.md), [`sparkforge_analyze_lakeformation_grants`](../tools/sparkforge_analyze_lakeformation_grants.md)

## `sparkforge analyze graph`

Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: import e versao declarada, construcao do GraphFrame e persistencia dos dois DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige checkpoint sem que o modulo o configure.

```bash
sparkforge analyze graph --help
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

[`sparkforge_analyze_graph`](../tools/sparkforge_analyze_graph.md)

## `sparkforge analyze iam-access`

Extrai a DECISAO de IAM ja simulada, com a camada que decidiu.

```bash
sparkforge analyze iam-access --help
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

[`sparkforge_analyze_glue_resource_link`](../tools/sparkforge_analyze_glue_resource_link.md), [`sparkforge_analyze_iam_access`](../tools/sparkforge_analyze_iam_access.md), [`sparkforge_analyze_lakeformation_grants`](../tools/sparkforge_analyze_lakeformation_grants.md)

## `sparkforge analyze iceberg`

Extrai facts de um dump JSON das metadata tables Iceberg.

```bash
sparkforge analyze iceberg --help
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

[`sparkforge_analyze_iceberg`](../tools/sparkforge_analyze_iceberg.md)

## `sparkforge analyze lakeformation-grants`

Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings).

```bash
sparkforge analyze lakeformation-grants --help
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

[`sparkforge_analyze_glue_resource_link`](../tools/sparkforge_analyze_glue_resource_link.md), [`sparkforge_analyze_iam_access`](../tools/sparkforge_analyze_iam_access.md), [`sparkforge_analyze_lakeformation_grants`](../tools/sparkforge_analyze_lakeformation_grants.md)

## `sparkforge analyze parquet-footer`

Extrai facts do FOOTER do Parquet ja coletado.

```bash
sparkforge analyze parquet-footer --help
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

[`sparkforge_analyze_parquet_footer`](../tools/sparkforge_analyze_parquet_footer.md)

## `sparkforge analyze plan`

Extrai facts do texto de um plano fisico (`df.explain("formatted")` / EXPLAIN FORMATTED).

```bash
sparkforge analyze plan --help
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

[`sparkforge_analyze_plan`](../tools/sparkforge_analyze_plan.md)

## `sparkforge analyze pyspark`

Extrai facts de PySpark via AST estatico (nunca importa o codigo).

```bash
sparkforge analyze pyspark --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | Arquivo ou diretorio a analisar. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_analyze_pyspark`](../tools/sparkforge_analyze_pyspark.md)

## `sparkforge analyze s3-listing`

Extrai facts de um dump de `aws s3api list-objects-v2` (small files, compressao nao splitavel).

```bash
sparkforge analyze s3-listing --help
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

[`sparkforge_analyze_s3_listing`](../tools/sparkforge_analyze_s3_listing.md)

## `sparkforge analyze sql`

Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark.

```bash
sparkforge analyze sql --help
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

[`sparkforge_analyze_sql`](../tools/sparkforge_analyze_sql.md)

## `sparkforge analyze sql-metrics`

Extrai metrica por no do plano de um Spark event log ja coletado.

```bash
sparkforge analyze sql-metrics --help
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

[`sparkforge_analyze_cloudwatch`](../tools/sparkforge_analyze_cloudwatch.md), [`sparkforge_analyze_event_log`](../tools/sparkforge_analyze_event_log.md), [`sparkforge_analyze_glue_job_runs`](../tools/sparkforge_analyze_glue_job_runs.md), [`sparkforge_analyze_sql_metrics`](../tools/sparkforge_analyze_sql_metrics.md)

## `sparkforge analyze step-functions`

Extrai facts da definicao ASL de uma state machine do AWS Step Functions (`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao.

```bash
sparkforge analyze step-functions --help
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

[`sparkforge_analyze_step_functions`](../tools/sparkforge_analyze_step_functions.md)

## `sparkforge analyze terraform`

Extrai facts de blocos aws_glue_job em HCL Terraform.

```bash
sparkforge analyze terraform --help
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

[`sparkforge_analyze_terraform`](../tools/sparkforge_analyze_terraform.md)

## `sparkforge analyze terraform-diff`

Compara dois estados de um modulo Terraform e marca o que mudou.

```bash
sparkforge analyze terraform-diff --help
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

[`sparkforge_analyze_terraform_diff`](../tools/sparkforge_analyze_terraform_diff.md)

## `sparkforge analyze workload`

Extrai facts do inventario declarado de workload (workload.yaml: SLA e fonte primaria), que capacity, finops e workload consomem.

```bash
sparkforge analyze workload --help
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

[`sparkforge_analyze_workload`](../tools/sparkforge_analyze_workload.md)
