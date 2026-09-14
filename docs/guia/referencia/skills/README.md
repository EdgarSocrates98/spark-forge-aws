<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Referência das skills

Uma skill é um procedimento escrito que o agente segue para uma tarefa focada. O texto integral de cada uma está na página dela.

| Skill | Quando usar |
|---|---|
| [`agentic-orchestration`](agentic-orchestration.md) | Use quando for necessario coordenar multiplos agents em fases limitadas, com handoffs, revisao e criterios de parada. |
| [`analyze-analytics`](analyze-analytics.md) | Use quando for necessario analisar dados, analytics, metricas, consultas, custos e qualidade. |
| [`analyze-batch-loop`](analyze-batch-loop.md) | Use quando o job processa dados em lotes com for/while, collect de chaves, isin(list) gigante ou filtros por batch id, ou dispara action/write/count/merge dentro de loop, e você... |
| [`analyze-functional-rules`](analyze-functional-rules.md) | Use quando for necessario estudar regras funcionais, contratos, estados, excecoes e criterios de aceite. |
| [`analyze-graph-data`](analyze-graph-data.md) | Use quando for necessario modelar, analisar ou consultar dados em grafos, caminhos, comunidades e relacionamentos. |
| [`analyze-library-call-graph`](analyze-library-call-graph.md) | Use quando o job Glue chama uma biblioteca Python com múltiplos módulos, factories, decorators ou helpers, e você precisa saber onde estão leituras, actions, caches, loops, UDFs... |
| [`analyze-spark-plan`](analyze-spark-plan.md) | Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, PartitionFilters/PushedFilters, Exchange/shuffle, estratégia de join (B... |
| [`analyze-spark-ui`](analyze-spark-ui.md) | Use quando houver um Spark event log, um job run id ou um Spark UI aberto de um job AWS Glue e for preciso achar stage dominante, skew de task, spill, GC, executor perdido ou su... |
| [`aws-billing-and-cost-management`](aws-billing-and-cost-management.md) | Use quando for analisar custos AWS, encontrar economias, gerenciar budgets, avaliar Savings Plans e Reserved Instances, right-size EC2/Lambda/RDS/EBS com Compute Optimizer, cons... |
| [`aws-database`](aws-database.md) | Use quando precisar escolher, comparar, recomendar, iniciar ou operar um banco de dados AWS — roteia para o servico correto entre Aurora, DSQL, RDS, DynamoDB, ElastiCache, Memor... |
| [`aws-iam`](aws-iam.md) | Use quando precisar corrigir comportamentos de IAM que agentes frequentemente erram — avaliação de policy, trust policies, limites de STS, Organizations, SAML/MFA — ou for criar... |
| [`aws-messaging-and-streaming`](aws-messaging-and-streaming.md) | Use quando for raciocinar sobre padrões de mensageria e streaming na AWS — escolher entre SQS, SNS, EventBridge, Amazon MQ, Kinesis Data Streams, Data Firehose, Managed Service... |
| [`aws-observability`](aws-observability.md) | Use quando for configurar, depurar ou otimizar observabilidade AWS com CloudWatch (Log Insights, Metrics, Alarms, Dashboards, EMF), X-Ray, CloudTrail e ADOT (AWS Distro for Open... |
| [`aws-sdk-python-usage`](aws-sdk-python-usage.md) | Use quando for escrever código Python que usa serviços AWS via boto3 ou botocore — criar service clients ou resources, configurar sessions e credenciais, tratar erros com Client... |
| [`aws-security`](aws-security.md) | Use quando a pergunta envolver serviços AWS de segurança — Security Hub V2 (OCSF) findings, conectores, agregadores, automation rules e resumo de postura; Security Hub CSPM (V1/... |
| [`aws-serverless`](aws-serverless.md) | Use quando precisar construir, deployar, gerenciar, debugar, configurar ou otimizar aplicacoes serverless na AWS com Lambda, API Gateway, Step Functions, EventBridge e SAM/CDK. |
| [`aws-storage`](aws-storage.md) | Use quando precisar escolher, comparar ou operar servicos de armazenamento AWS — S3 (General Purpose, Express One Zone, Tables, Vectors, Files), EFS, FSx (Lustre, ONTAP, OpenZFS... |
| [`benchmark-pyspark-job`](benchmark-pyspark-job.md) | Use quando precisar comprovar — não estimar — o efeito de uma mudança de performance num job Glue, com comparação antes/depois de duração de stage, spill, GC e executor perdido,... |
| [`compare-releases`](compare-releases.md) | Use quando precisar saber o que muda de COMPONENTE entre dois runtimes antes de uma migração — "vou de emr-6.15.0 para emr-7.5.0, que versão de Spark e de Iceberg eu passo a ter... |
| [`design-agent-systems`](design-agent-systems.md) | Use quando for necessario criar agents, skills, loops, handoffs e avaliacao. |
| [`design-airflow-pipelines`](design-airflow-pipelines.md) | Use quando for necessario projetar ou revisar Airflow e pipelines DAG. |
| [`design-data-architecture`](design-data-architecture.md) | Use quando for necessario desenhar arquiteturas de dados completas. |
| [`design-dynamodb-model`](design-dynamodb-model.md) | Use quando for necessario modelar DynamoDB, chaves, access patterns, indexes, capacity, streams e consistencia. |
| [`design-incremental-processing`](design-incremental-processing.md) | Use quando um job dito incremental continua lento mesmo com pouca entrada, faz scan global, recomputa estado histórico, ou você precisa projetar bootstrap, ciclos, backfill, lat... |
| [`design-lambda-serverless`](design-lambda-serverless.md) | Use quando for necessario projetar, analisar ou otimizar AWS Lambda, eventos, concorrencia e arquiteturas serverless. |
| [`design-neptune-graph`](design-neptune-graph.md) | Use quando for necessario projetar Amazon Neptune, Gremlin, openCypher, RDF, indices, carga e alta disponibilidade. |
| [`design-s3-data-lake`](design-s3-data-lake.md) | Use quando for necessario projetar S3, zonas, lifecycle e governanca de data lake. |
| [`design-step-functions-orchestration`](design-step-functions-orchestration.md) | Use quando for necessario desenhar, revisar ou validar AWS Step Functions, EventBridge, retries e workflows serverless. |
| [`diagnose-data-skew`](diagnose-data-skew.md) | Use quando o judge já disparou SF-UI-001 (skew de duração de task) e for preciso decidir entre skew de dados e skew de computação, tratar hot key, null ou valor sentinela, ou de... |
| [`diagnose-lakeformation-access`](diagnose-lakeformation-access.md) | Use quando um job Glue lê tabela governada e falha ao escrever, ou quando alguém pergunta "por que a leitura passa e a escrita não?", "tomo AccessDenied e já dei SELECT", "troqu... |
| [`diagnose-oom`](diagnose-oom.md) | Use quando um job Glue falha com OutOfMemory, "Container killed by YARN", "GC overhead limit exceeded", ExecutorLostFailure, estouro de Python worker/pandas_udf, ou frases como... |
| [`engineer-agent-context`](engineer-agent-context.md) | Use quando for necessaria a capacidade de montar e comprimir contexto sem perder evidencia. |
| [`engineer-agent-memory`](engineer-agent-memory.md) | Use quando for necessaria a capacidade de projetar memoria auditavel por sessao, caso e dominio. |
| [`glue-incremental-performance-architect`](glue-incremental-performance-architect.md) | Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key sobre tabela Iceberg bilionária, batching por lote, OOM q... |
| [`harden-s3-bucket`](harden-s3-bucket.md) | Use quando for proteger um bucket S3 — criar bucket novo já hardenado, auditar bucket existente contra controles de segurança, remediar finding de security hub/guardduty, config... |
| [`iceberg-v3-readiness`](iceberg-v3-readiness.md) | Use quando alguém pergunta "posso subir essa tabela para Iceberg format v3?", "o Athena lê v3?", "vale a pena o VARIANT / os deletion vectors / o row lineage?" ou quando uma que... |
| [`lakeformation-fgac-guard`](lakeformation-fgac-guard.md) | Use quando um job Glue declara `--enable-lakeformation-fine-grained-access` ou configuração de Full Table Access e alguém pergunta "posso passar um JAR extra?", "por que meu con... |
| [`migrate-glue-6`](migrate-glue-6.md) | Use quando alguém pergunta "dá para subir esse job para o Glue 6.0?", "o que quebra se eu migrar de 4.0/5.0/5.1 para 6.0?", "vale a pena migrar por causa dos 30% mais barato?" o... |
| [`optimize-athena-queries`](optimize-athena-queries.md) | Use quando for necessario otimizar consultas Athena, particionamento, Parquet, projection, federated query e custo. |
| [`optimize-iceberg-table`](optimize-iceberg-table.md) | Use quando tabelas Apache Iceberg no Glue Data Catalog degradam por excesso de data files pequenos, delete files acumulados, snapshots ou manifests crescendo sem parar, partitio... |
| [`optimize-iceberg-tables`](optimize-iceberg-tables.md) | Use quando for necessario otimizar tabelas Apache Iceberg e catalogos. |
| [`optimize-latest-per-key`](optimize-latest-per-key.md) | Use quando o job calcula o registro mais recente por chave (row_number/Window, max_by, max(struct), join-back) sobre tabelas Spark/Iceberg grandes, e suspeitar de Window global... |
| [`optimize-parquet-layout`](optimize-parquet-layout.md) | Use quando datasets Parquet no S3 (fora do Iceberg) sofrem com small files, listing lento, milhares de objetos por prefixo, arquivo por chave na escrita, ou leitura que não faz... |
| [`optimize-pyspark-code`](optimize-pyspark-code.md) | Use quando revisar, refatorar ou otimizar código PySpark/Spark SQL para AWS Glue — script, função, módulo, PR ou trecho de DataFrame — suspeito de UDF Python evitável, collect/t... |
| [`optimize-variable-volume-job`](optimize-variable-volume-job.md) | Use quando o mesmo job Glue roda de dezenas de registros a centenas de milhões e um único perfil configurado para o pior caso fica caro em microcarga e ainda inadequado no full. |
| [`propose-change-pr`](propose-change-pr.md) | Use quando o operador quiser levar ao repositório uma mudança de configuração que já passou pelo sandbox — "abre o PR dessa mudança", "propõe essa troca", "o sandbox passou, e a... |
| [`provision-s3-tables-table`](provision-s3-tables-table.md) | Use quando for criar uma tabela Iceberg gerenciada por Amazon S3 Tables (o produto `s3tables`, não o Glue Data Catalog tradicional) — table bucket, namespace, tabela, schema, pa... |
| [`review-data-validation`](review-data-validation.md) | Use quando o job PySpark valida dado e a pergunta for onde a validação está, se ela tem consequência e quanto ela custa — check artesanal (`df.filter(...).count()`), `Verificati... |
| [`review-emr-cluster`](review-emr-cluster.md) | Use quando revisar a definição de um cluster Amazon EMR on EC2 (instance fleets contra instance groups, purchasing option por papel, managed scaling com alocação dinâmica, Confi... |
| [`review-emr-eks`](review-emr-eks.md) | Use quando revisar a execução de um job Amazon EMR on EKS pelo par `describe-virtual-cluster` + `describe-job-run` do `emr-containers` (segredo em texto claro nas duas superfíci... |
| [`review-glue-terraform`](review-glue-terraform.md) | Use quando revisar o Terraform/IaC de jobs Glue (worker type, max_capacity junto com worker_type/number_of_workers, execution class, timeout, max_concurrent_runs com bookmarks,... |
| [`review-pyspark-pr`](review-pyspark-pr.md) | Use quando revisar um Pull Request PySpark/AWS Glue e precisar classificar risco de regressão de performance, custo e escala antes de aprovar — novas actions, shuffles, joins co... |
| [`review-terraform-data-platform`](review-terraform-data-platform.md) | Use quando for necessario revisar Terraform de plataformas de dados, IAM, providers, plans e drift. |
| [`run-debate`](run-debate.md) | Use quando `sparkforge arbitrate` devolver `debate.unresolved` com um `debate_plan` para um par de regras e o operador quiser conduzir o debate na sessão — "roda o debate entre... |
| [`spark4-compatibility`](spark4-compatibility.md) | Use quando o código PySpark ou o `.jar` precisa rodar sob Apache Spark 4 e alguém pergunta "o que quebra no Spark 4?", "essa config mudou de nome?", "ANSI mode vai estourar meu... |
| [`sparkforge-diagnose`](sparkforge-diagnose.md) | Use quando o pedido for genérico e amplo — "meu job Glue tá lento", "por que esse pipeline ficou caro", "não sei por onde começar" — e ainda não há gargalo isolado nem skill esp... |
| [`token-efficient-agent`](token-efficient-agent.md) | Use quando o objetivo exigir economia de tokens sem reduzir evidencia, precisao, cobertura ou verificacao. |
| [`tool-specialist-routing`](tool-specialist-routing.md) | Use quando for necessario escolher, validar ou autorizar ferramentas por especializacao, risco e contrato. |
| [`tune-glue-job`](tune-glue-job.md) | Use quando for ajustar workers, worker type, Auto Scaling, execution class ou argumentos de um job Glue depois de já ter um gargalo comprovado — não para descobri-lo. |
| [`verify-agent-evidence`](verify-agent-evidence.md) | Use quando for necessaria a capacidade de verificar evidencias, fontes, escopo e lacunas. |
