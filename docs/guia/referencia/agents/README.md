<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Referência dos agents

Coordenadores despacham executores em ordem; especialistas respondem uma área; executores fazem uma função do loop de fase (ver `AGENT_PROTOCOL.md`).

## Coordenadores

| Agent | O que faz |
|---|---|
| [`athena-query-optimizer`](athena-query-optimizer.md) | Custo ou latencia na consulta Athena e nao no job - bytes escaneados, pruning de particao, projecao de coluna, versao do engine, workgroup, layout de armazenamento. |
| [`data-quality-reviewer`](data-quality-reviewer.md) | Validacao de dado em job PySpark - PyDeequ, Great Expectations ou artesanal - se esta no lugar certo, se tem consequencia, quanto custa em passadas sobre o dado. |
| [`emr-infra-reviewer`](emr-infra-reviewer.md) | Spark em Amazon EMR on EC2, Serverless ou on EKS com risco na infraestrutura e nao no codigo - instance fleets contra instance groups, purchasing option, managed scaling, Config... |
| [`glue-incremental-performance-architect`](glue-incremental-performance-architect.md) | Investigacao ponta a ponta de job ou biblioteca Glue PySpark com fluxos full e incremental - latest-per-key em Iceberg bilionario, batching, OOM apos horas, carga variavel. |
| [`glue-infra-reviewer`](glue-infra-reviewer.md) | Gargalo ou risco na definicao do job Glue e nao no codigo - worker type e numero, auto scaling, bookmark, retries, argumentos de job, observabilidade, Terraform. |
| [`iceberg-performance-engineer`](iceberg-performance-engineer.md) | Gargalo em tabelas Apache Iceberg no Glue Data Catalog e S3 - small files, delete files, snapshots, manifests, metadata planning, partition spec, sort order, writes, manutencao. |
| [`pyspark-code-reviewer`](pyspark-code-reviewer.md) | Revisao de codigo PySpark - PR, biblioteca ou job - correlacionando fonte, plano fisico pos-Catalyst e estrutura de chamadas. |
| [`sf-agent-builder`](sf-agent-builder.md) | Criar e avaliar agents e skills. |
| [`sf-agent-evaluation-specialist`](sf-agent-evaluation-specialist.md) | Golden cases e qualidade de agents. |
| [`sf-airflow-specialist`](sf-airflow-specialist.md) | Projetar ou revisar Airflow e DAGs. |
| [`sf-analytics-specialist`](sf-analytics-specialist.md) | Analisar dados, analytics, Athena e qualidade. |
| [`sf-athena-specialist`](sf-athena-specialist.md) | Otimizar consultas e tabelas no Athena. |
| [`sf-context-engineer`](sf-context-engineer.md) | Contexto e compressao de agents. |
| [`sf-cost-reviewer`](sf-cost-reviewer.md) | Custo de dados e de agents. |
| [`sf-data-architect`](sf-data-architect.md) | Desenhar arquiteturas de dados completas. |
| [`sf-dynamodb-specialist`](sf-dynamodb-specialist.md) | Modelar ou revisar DynamoDB. |
| [`sf-evidence-verifier`](sf-evidence-verifier.md) | Evidence e findings. |
| [`sf-functional-rules-specialist`](sf-functional-rules-specialist.md) | Regras funcionais, contratos e estados. |
| [`sf-graph-specialist`](sf-graph-specialist.md) | Analisar ou modelar dados em grafos. |
| [`sf-iceberg-specialist`](sf-iceberg-specialist.md) | Otimizar Apache Iceberg. |
| [`sf-kinesis-specialist`](sf-kinesis-specialist.md) | Kinesis e streaming. |
| [`sf-lake-formation-specialist`](sf-lake-formation-specialist.md) | Lake Formation e governanca. |
| [`sf-lambda-serverless-specialist`](sf-lambda-serverless-specialist.md) | Desenhar Lambda serverless, idempotencia e concorrencia. |
| [`sf-lineage-specialist`](sf-lineage-specialist.md) | Lineage e impacto. |
| [`sf-memory-engineer`](sf-memory-engineer.md) | Memoria auditavel de agents. |
| [`sf-neptune-specialist`](sf-neptune-specialist.md) | Projetar ou revisar Amazon Neptune. |
| [`sf-orchestrator`](sf-orchestrator.md) | Coordenar agents em fases limitadas - roteamento, handoffs, criterios de parada. |
| [`sf-parquet-specialist`](sf-parquet-specialist.md) | Otimizar Parquet e layout de arquivos. |
| [`sf-pyspark-specialist`](sf-pyspark-specialist.md) | Analisar PySpark - planos, joins, skew, memoria, benchmarks. |
| [`sf-runtime-specialist`](sf-runtime-specialist.md) | Analisar Glue, EMR, runtimes, capacidade, infraestrutura e compatibilidade entre versoes numa migracao. |
| [`sf-s3-specialist`](sf-s3-specialist.md) | Projetar ou revisar S3 e data lakes. |
| [`sf-schema-registry-specialist`](sf-schema-registry-specialist.md) | Schema e contratos. |
| [`sf-security-reviewer`](sf-security-reviewer.md) | IAM, KMS, S3 e exfiltracao. |
| [`sf-step-functions-specialist`](sf-step-functions-specialist.md) | Desenhar Step Functions, EventBridge e retries. |
| [`sf-storage-specialist`](sf-storage-specialist.md) | Analisar Iceberg, Parquet, catalogo, particionamento e layout. |
| [`sf-terraform-specialist`](sf-terraform-specialist.md) | Revisar ou construir Terraform para plataformas de dados. |
| [`sf-token-verifier`](sf-token-verifier.md) | Verificar qualidade, cobertura de evidencia e economia de tokens. |
| [`spark-performance-architect`](spark-performance-architect.md) | Coordena diagnostico e otimizacao de job PySpark no AWS Glue - correlaciona codigo, plano fisico, Spark UI, Parquet e Iceberg para achar o gargalo dominante antes de recomendar... |

## Executors

| Agent | O que faz |
|---|---|
| [`sf-extractor`](sf-extractor.md) |  |
| [`sf-inventory`](sf-inventory.md) |  |
| [`sf-judge`](sf-judge.md) |  |
| [`sf-synthesizer`](sf-synthesizer.md) |  |
| [`sf-verifier`](sf-verifier.md) |  |
