<!-- Gerado por scripts/gen_agentic_catalog.py a partir dos canonicos. Nao edite a mao: rode `python scripts/gen_agentic_catalog.py`. -->

# Catálogo agentic — Spark Forge AWS

Ficha §11 de cada coordenador, executor e skill, gerada dos canônicos.
O valor de cada recurso está no campo — este arquivo não é uma lista
de nomes.

Superfície: **14 coordenadores**, **5 executores**, **60 skills**.

## Coordenadores

### `athena-query-optimizer`

| Campo | Valor |
|---|---|
| NAME | `athena-query-optimizer` |
| PURPOSE | Custo ou latencia na consulta Athena e nao no job - bytes escaneados, pruning de particao, projecao de coluna, versao do engine, workgroup, layout de armazenamento |
| DOMAIN | SF-ATH, SF-PQ |
| WHEN_TO_USE | custo ou latência na consulta Athena, não no job — bytes escaneados, pruning de partição, engine, workgroup |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_athena_workgroup`, `sparkforge_aws_analyze_catalog_schema`, `sparkforge_aws_analyze_consumers`, `sparkforge_aws_analyze_s3_listing`, `sparkforge_aws_analyze_sql`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_fuse`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “A consulta Athena ficou cara. Use athena-query-optimizer para medir bytes escaneados, pruning de partição e workgroup.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `cdc-contract-reviewer`

| Campo | Valor |
|---|---|
| NAME | `cdc-contract-reviewer` |
| PURPOSE | Especialista em CDC, Debezium/Kafka Connect, AWS DMS e contratos de mudança, separando posição, chave, snapshot/CDC seam, schema history, tombstone, mappings e unresolved sem declarar exatamente-once… |
| DOMAIN | SF-CDC, SF-DEBEZIUM, SF-DMS, SF-SCHEMA |
| WHEN_TO_USE | revisão de eventos CDC, Debezium/Kafka Connect, AWS DMS e contratos de mudança com posição, chave, seam, tombstone, schema history e mappings |
| WHEN_NOT_TO_USE | Toda manutenção destrutiva exige confirmação explícita do operador.; Não conecta em banco, Kafka Connect, Debezium, DMS, Glue Schema Registry ou AWS.; Não declara exactly-once, idempotência, ausência de perda ou compatibilidade sem evidência. |
| TRIGGERS | skills: `review-cdc-replication`, `aws-messaging-and-streaming` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-cdc-replication`, `aws-messaging-and-streaming` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_cdc`, `sparkforge_aws_judge` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Revise estes eventos CDC/Debezium com cdc-contract-reviewer: chaves, seam snapshot/CDC, deletes e tombstones.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `data-quality-reviewer`

| Campo | Valor |
|---|---|
| NAME | `data-quality-reviewer` |
| PURPOSE | Validacao de dado em job PySpark - PyDeequ, Great Expectations ou artesanal - se esta no lugar certo, se tem consequencia, quanto custa em passadas sobre o dado |
| DOMAIN | SF-DQ, SF-DQ-AI |
| WHEN_TO_USE | o job valida dado e a pergunta é se a validação está no lugar certo, se tem consequência e quanto custa |
| WHEN_NOT_TO_USE | **Se o check reprova, quem responde é a ferramenta de DQ.** O relatório do Deequ ou do; **Você não decide qual regra de negócio deveria existir.** Quais colunas precisam de; **Você não estima quantas linhas violam.** Nenhum fact desta área tem cardinalidade do |
| TRIGGERS | skills: `review-data-validation`, `review-pyspark-pr`, `analyze-library-call-graph`, `analyze-functional-rules` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-data-validation`, `review-pyspark-pr`, `analyze-library-call-graph`, `analyze-functional-rules` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_data_quality`, `sparkforge_aws_analyze_dq_ai`, `sparkforge_aws_analyze_pyspark`, `sparkforge_aws_dq_ai_assess`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Este job valida dado — a validação está no lugar certo e custa quanto? Use data-quality-reviewer.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `emr-infra-reviewer`

| Campo | Valor |
|---|---|
| NAME | `emr-infra-reviewer` |
| PURPOSE | Spark em Amazon EMR on EC2, Serverless ou on EKS com risco na infraestrutura e nao no codigo - instance fleets contra instance groups, purchasing option, managed scaling, Configurations em dois niveis… |
| DOMAIN | SF-EMR, SF-EMRS, SF-EMRK, SF-ENV |
| WHEN_TO_USE | risco na definição de um cluster Amazon EMR on EC2 **ou** de uma application EMR Serverless |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `review-emr-cluster`, `review-emr-eks`, `analyze-spark-ui`, `benchmark-pyspark-job` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-emr-cluster`, `review-emr-eks`, `analyze-spark-ui`, `benchmark-pyspark-job` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_emr_cluster`, `sparkforge_aws_analyze_emr_eks`, `sparkforge_aws_analyze_emr_serverless`, `sparkforge_aws_analyze_event_log`, `sparkforge_aws_collect_emr_cluster`, `sparkforge_aws_collect_emr_eks`, `sparkforge_aws_collect_emr_serverless`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Revise a definição deste cluster EMR com emr-infra-reviewer: fleets, managed scaling, logs, segredo em configuração.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `glue-incremental-performance-architect`

| Campo | Valor |
|---|---|
| NAME | `glue-incremental-performance-architect` |
| PURPOSE | Investigacao ponta a ponta de job ou biblioteca Glue PySpark com fluxos full e incremental - latest-per-key em Iceberg bilionario, batching, OOM apos horas, carga variavel… |
| DOMAIN | SF-PY, SF-ICE, SF-UI, SF-ENV |
| WHEN_TO_USE | fluxo full + incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `glue-incremental-performance-architect`, `sparkforge-aws-diagnose`, `analyze-library-call-graph`, `design-incremental-processing`, `optimize-latest-per-key`, `analyze-batch-loop`, `diagnose-oom`, `optimize-variable-volume-job`, `review-glue-terraform`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-spark-ui`, `diagnose-data-skew`, `tune-glue-job`, `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `glue-incremental-performance-architect`, `sparkforge-aws-diagnose`, `analyze-library-call-graph`, `design-incremental-processing`, `optimize-latest-per-key`, `analyze-batch-loop`, `diagnose-oom`, `optimize-variable-volume-job`, `review-glue-terraform`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-spark-ui`, `diagnose-data-skew`, `tune-glue-job`, `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_next_step`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Meu job incremental está tão lento quanto o full. Use glue-incremental-performance-architect para mapear os dois fluxos antes de qualquer tuning.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `glue-infra-reviewer`

| Campo | Valor |
|---|---|
| NAME | `glue-infra-reviewer` |
| PURPOSE | Gargalo ou risco na definicao do job Glue e nao no codigo - worker type e numero, auto scaling, bookmark, retries, argumentos de job, observabilidade, Terraform, e como o job e disparado de fora - a s… |
| DOMAIN | SF-GLUE, SF-ENV, SF-SFN, SF-SFNX, SF-AIRFLOW |
| WHEN_TO_USE | gargalo ou risco na definição do job Glue, não no código — worker, auto scaling, bookmark, retries, Terraform |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `review-glue-terraform`, `tune-glue-job`, `optimize-variable-volume-job` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-glue-terraform`, `tune-glue-job`, `optimize-variable-volume-job` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_airflow_dag`, `sparkforge_aws_analyze_cloudwatch`, `sparkforge_aws_analyze_cloudwatch_logs`, `sparkforge_aws_analyze_glue_job_runs`, `sparkforge_aws_analyze_sfn_history`, `sparkforge_aws_analyze_step_functions`, `sparkforge_aws_analyze_terraform`, `sparkforge_aws_analyze_terraform_diff`, `sparkforge_aws_collect_cloudwatch`, `sparkforge_aws_collect_glue_job`, `sparkforge_aws_finops`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_fuse`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Revise a definição Terraform deste job Glue com o perfil glue-infra-reviewer: workers, bookmark, retries, observabilidade.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `iceberg-performance-engineer`

| Campo | Valor |
|---|---|
| NAME | `iceberg-performance-engineer` |
| PURPOSE | Gargalo em tabelas Apache Iceberg no Glue Data Catalog e S3 - small files, delete files, snapshots, manifests, metadata planning, partition spec, sort order, writes, manutencao |
| DOMAIN | SF-ICE, SF-PQ |
| WHEN_TO_USE | dívida de data files, delete files, manifests, snapshots e manutenção de tabela Iceberg |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `optimize-iceberg-table`, `optimize-parquet-layout`, `benchmark-pyspark-job`, `iceberg-v3-readiness` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `optimize-iceberg-table`, `optimize-parquet-layout`, `benchmark-pyspark-job`, `iceberg-v3-readiness` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_iceberg_assess_upgrade`, `sparkforge_aws_next_step`, `sparkforge_aws_playbook`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_runtime_detect` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Esta tabela Iceberg está lenta para consultar. Use iceberg-performance-engineer para medir a dívida de data files, delete files e snapshots.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `pyspark-code-reviewer`

| Campo | Valor |
|---|---|
| NAME | `pyspark-code-reviewer` |
| PURPOSE | Revisao de codigo PySpark - PR, biblioteca ou job - correlacionando fonte, plano fisico pos-Catalyst e estrutura de chamadas… |
| DOMAIN | SF-PY, SF-PLAN, SF-CG, SF-GRAPH |
| WHEN_TO_USE | revisar código PySpark — PR, biblioteca ou job — correlacionando fonte, plano físico e call graph; **e** job de grafo com GraphFrames |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `review-pyspark-pr`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-library-call-graph`, `analyze-batch-loop` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-pyspark-pr`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-library-call-graph`, `analyze-batch-loop` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_call_graph`, `sparkforge_aws_analyze_data_quality`, `sparkforge_aws_analyze_dbt_artifacts`, `sparkforge_aws_analyze_duckdb_microscope`, `sparkforge_aws_analyze_graph`, `sparkforge_aws_analyze_lakehouse_catalog`, `sparkforge_aws_analyze_plan`, `sparkforge_aws_analyze_pyspark`, `sparkforge_aws_code_context`, `sparkforge_aws_code_export`, `sparkforge_aws_code_path`, `sparkforge_aws_code_read`, `sparkforge_aws_code_search`, `sparkforge_aws_code_shape`, `sparkforge_aws_code_status`, `sparkforge_aws_code_symbol`, `sparkforge_aws_code_sync`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_graph_status`, `sparkforge_aws_graph_view`, `sparkforge_aws_playbook` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Revise jobs/etl.py com o perfil pyspark-code-reviewer: fonte, plano físico e call graph, com evidência ancora por linha.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `sf-lake-formation-specialist`

| Campo | Valor |
|---|---|
| NAME | `sf-lake-formation-specialist` |
| PURPOSE | Lake Formation e governanca |
| DOMAIN | SF-LF, SF-XACC |
| WHEN_TO_USE | Lake Formation e governanca |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `design-data-architecture`, `design-s3-data-lake`, `review-terraform-data-platform`, `lakeformation-fgac-guard`, `lakeformation-architecture` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `design-data-architecture`, `design-s3-data-lake`, `review-terraform-data-platform`, `lakeformation-fgac-guard`, `lakeformation-architecture` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_collect_glue_resource_link`, `sparkforge_aws_lakeformation_access_graph`, `sparkforge_aws_lakeformation_matrix`, `sparkforge_aws_root_cause` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Diagnostique por que este job lê e não escreve na tabela governada: use sf-lake-formation-specialist.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `sf-runtime-specialist`

| Campo | Valor |
|---|---|
| NAME | `sf-runtime-specialist` |
| PURPOSE | Analisar Glue, EMR, runtimes, capacidade, infraestrutura e compatibilidade entre versoes numa migracao |
| DOMAIN | SF-GLUE, SF-EMR, SF-ENV, SF-MIG, SF-SPARK4, SF-CTM, SF-ERR |
| WHEN_TO_USE | Analisar Glue, EMR, runtimes, capacidade, infraestrutura e compatibilidade entre versoes numa migracao |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `tool-specialist-routing`, `compare-releases`, `migrate-glue-6`, `spark4-compatibility`, `lakeformation-architecture` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `tool-specialist-routing`, `compare-releases`, `migrate-glue-6`, `spark4-compatibility`, `lakeformation-architecture` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_controlm_jobs`, `sparkforge_aws_analyze_orchestration`, `sparkforge_aws_analyze_platform_ecosystem`, `sparkforge_aws_controlm_describe`, `sparkforge_aws_glue_dependency_audit`, `sparkforge_aws_migration_assess`, `sparkforge_aws_release_describe` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Confira a compatibilidade de versão deste job com sf-runtime-specialist: Glue, Spark, Python e Iceberg observados.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `sf-security-reviewer`

| Campo | Valor |
|---|---|
| NAME | `sf-security-reviewer` |
| PURPOSE | IAM, KMS, S3 e exfiltracao |
| DOMAIN | SF-KMS, SF-IAM, SF-DQ-AI |
| WHEN_TO_USE | IAM, KMS, S3 e exfiltracao |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `review-terraform-data-platform`, `design-s3-data-lake`, `design-data-architecture` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-terraform-data-platform`, `design-s3-data-lake`, `design-data-architecture` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_policy_explain` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Faça a revisão de segurança deste job com sf-security-reviewer: segredos, permissões e superfície exposta.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `sf-terraform-specialist`

| Campo | Valor |
|---|---|
| NAME | `sf-terraform-specialist` |
| PURPOSE | Revisar ou construir Terraform para plataformas de dados |
| DOMAIN | SF-NET |
| WHEN_TO_USE | Revisar ou construir Terraform para plataformas de dados |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `review-terraform-data-platform` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `review-terraform-data-platform` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | — |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Revise este módulo Terraform de plataforma de dados com sf-terraform-specialist.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `spark-performance-architect`

| Campo | Valor |
|---|---|
| NAME | `spark-performance-architect` |
| PURPOSE | Coordena diagnostico e otimizacao de job PySpark no AWS Glue - correlaciona codigo, plano fisico, Spark UI, Parquet e Iceberg para achar o gargalo dominante antes de recomendar mudancas |
| DOMAIN | SF-PY, SF-UI, SF-PLAN, SF-BENCH, SF-FVAL, SF-TIMEOUT, SF-WASTE, SF-BRIDGE, SF-STREAM |
| WHEN_TO_USE | diagnóstico geral de um job PySpark no Glue, gargalo dominante ainda não localizado; e comprovar o ganho de uma mudança comparando dois runs — pelo tempo **e** pelo resultado |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | skills: `sparkforge-aws-diagnose`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-spark-ui`, `diagnose-data-skew`, `tune-glue-job`, `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job`, `review-pyspark-pr` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `sparkforge-aws-diagnose`, `optimize-pyspark-code`, `analyze-spark-plan`, `analyze-spark-ui`, `diagnose-data-skew`, `tune-glue-job`, `optimize-parquet-layout`, `optimize-iceberg-table`, `benchmark-pyspark-job`, `review-pyspark-pr` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_agentops_baseline`, `sparkforge_aws_agentops_compare`, `sparkforge_aws_agentops_critical_path`, `sparkforge_aws_agentops_inspect`, `sparkforge_aws_agentops_timeline`, `sparkforge_aws_analyze_data_observability`, `sparkforge_aws_analyze_platform_graph`, `sparkforge_aws_analyze_pyspark`, `sparkforge_aws_analyze_streaming`, `sparkforge_aws_arbitrate`, `sparkforge_aws_benchmark`, `sparkforge_aws_case_get`, `sparkforge_aws_case_open`, `sparkforge_aws_change_plan`, `sparkforge_aws_change_sandbox`, `sparkforge_aws_collect_parquet_footer`, `sparkforge_aws_context_expand`, `sparkforge_aws_context_inspect`, `sparkforge_aws_context_start`, `sparkforge_aws_debate_next`, `sparkforge_aws_debate_referee`, `sparkforge_aws_debate_start`, `sparkforge_aws_debate_submit`, `sparkforge_aws_decision_evaluate`, `sparkforge_aws_doctor_agentic`, `sparkforge_aws_economy_report`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_judge`, `sparkforge_aws_migration_assess`, `sparkforge_aws_next_step`, `sparkforge_aws_pack_list`, `sparkforge_aws_playbook`, `sparkforge_aws_root_cause`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_runtime_detect`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp`, `sparkforge_aws_sdd_status`, `sparkforge_aws_simulate`, `sparkforge_aws_tune`, `sparkforge_aws_validate_output` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Investigue este job Glue de ponta a ponta com o perfil spark-performance-architect: encontre o gargalo dominante e diga o próximo passo com evidência.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

### `streaming-realtime-architect`

| Campo | Valor |
|---|---|
| NAME | `streaming-realtime-architect` |
| PURPOSE | Especialista em plataformas streaming Apache Flink, Managed Flink, Structured Streaming e AWS Glue Streaming/RTM, correlacionando transporte, checkpoint, state, backpressure, observabilidade e resulta… |
| DOMAIN | SF-STREAM, SF-FLINK, SF-GLUESTREAM, SF-STREAMICE, SF-STREAMOBS, SF-EVENT |
| WHEN_TO_USE | diagnóstico de plataformas Flink, Managed Flink e Structured Streaming com transporte, checkpoint, state e observabilidade |
| WHEN_NOT_TO_USE | Não executa mutação em AWS, Flink, Managed Flink, broker ou tabela.; Não declara exatamente-once por checkpoint configurado.; Não transforma ausência de métrica em zero. |
| TRIGGERS | skills: `analyze-flink-job`, `review-structured-streaming`, `analyze-streaming-composition`, `review-glue-streaming`, `analyze-spark-ui`, `aws-messaging-and-streaming`, `review-event-driven-architecture`, `design-realtime-data-architecture`, `review-streaming-operations` |
| SUPPORTED_HOSTS | subagente em **Claude Code** e **Devin** (espelhos `.claude/`, `.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, e piso nas demais quando o despacho está desligado |
| REQUIRED_SKILLS | `analyze-flink-job`, `review-structured-streaming`, `analyze-streaming-composition`, `review-glue-streaming`, `analyze-spark-ui`, `aws-messaging-and-streaming`, `review-event-driven-architecture`, `design-realtime-data-architecture`, `review-streaming-operations` |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash, Edit, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_event_driven`, `sparkforge_aws_analyze_forge_lab`, `sparkforge_aws_analyze_glue_streaming`, `sparkforge_aws_analyze_streaming_composition`, `sparkforge_aws_analyze_streaming_integrations`, `sparkforge_aws_analyze_streaming_ops`, `sparkforge_aws_analyze_transport`, `sparkforge_aws_collect_managed_flink`, `sparkforge_aws_collect_schema_registry`, `sparkforge_aws_collect_streaming_integrations`, `sparkforge_aws_judge`, `sparkforge_aws_next_step` |
| INPUTS | case aberto, artifacts coletados, findings do `judge` |
| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |
| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |
| EXAMPLE_PROMPT | “Avalie esta plataforma streaming (Flink + Kafka + Iceberg) com streaming-realtime-architect: transporte, checkpoint, backlog.” |
| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |

## Executores

### `sf-extractor`

| Campo | Valor |
|---|---|
| NAME | `sf-extractor` |
| PURPOSE | executor `extract` — ver fonte |
| DOMAIN | pipeline determinístico (`extract`) |
| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |
| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |
| REQUIRED_SKILLS | — |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_athena_workgroup`, `sparkforge_aws_analyze_call_graph`, `sparkforge_aws_analyze_catalog_schema`, `sparkforge_aws_analyze_cloudwatch_logs`, `sparkforge_aws_analyze_consumers`, `sparkforge_aws_analyze_emr_serverless`, `sparkforge_aws_analyze_error_signatures`, `sparkforge_aws_analyze_event_log`, `sparkforge_aws_analyze_graph`, `sparkforge_aws_analyze_iceberg`, `sparkforge_aws_analyze_parquet_footer`, `sparkforge_aws_analyze_plan`, `sparkforge_aws_analyze_pyspark`, `sparkforge_aws_analyze_s3_listing`, `sparkforge_aws_analyze_sql`, `sparkforge_aws_analyze_sql_metrics`, `sparkforge_aws_analyze_terraform`, `sparkforge_aws_analyze_terraform_diff`, `sparkforge_aws_analyze_workload`, `sparkforge_aws_capacity`, `sparkforge_aws_finops`, `sparkforge_aws_fuse`, `sparkforge_aws_workload` |
| INPUTS | ver `## Pressupõe` na fonte |
| EXPECTED_OUTPUT | `case.facts_index` — caminho, contagem e `by_kind`; `case.open_questions` — atualizado com os pontos cegos que sobraram |
| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |
| EXAMPLE_PROMPT | via coordenador — o `sf-extractor` roda como passo |
| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |

### `sf-inventory`

| Campo | Valor |
|---|---|
| NAME | `sf-inventory` |
| PURPOSE | executor `inventory` — ver fonte |
| DOMAIN | pipeline determinístico (`inventory`) |
| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |
| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |
| REQUIRED_SKILLS | — |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_ai`, `sparkforge_aws_case_get`, `sparkforge_aws_case_open`, `sparkforge_aws_case_update`, `sparkforge_aws_collect_athena_workgroup`, `sparkforge_aws_collect_cloudwatch`, `sparkforge_aws_collect_cloudwatch_logs`, `sparkforge_aws_collect_emr_serverless`, `sparkforge_aws_collect_event_log`, `sparkforge_aws_collect_glue_job`, `sparkforge_aws_collect_glue_job_runs`, `sparkforge_aws_collect_iceberg_metadata`, `sparkforge_aws_collect_parquet_footer`, `sparkforge_aws_collect_verify`, `sparkforge_aws_doctor`, `sparkforge_aws_runtime_detect`, `sparkforge_aws_scan` |
| INPUTS | ver `## Pressupõe` na fonte |
| EXPECTED_OUTPUT | `case.runtime` — versões confirmadas e `detected_from`; `case.runtime.divergences` — vazio, ou o conflito entre fontes; `case.artifacts` — o que existe, com sha256 e origem |
| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |
| EXAMPLE_PROMPT | via coordenador — o `sf-inventory` roda como passo |
| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |

### `sf-judge`

| Campo | Valor |
|---|---|
| NAME | `sf-judge` |
| PURPOSE | executor `judge` — ver fonte |
| DOMAIN | pipeline determinístico (`judge`) |
| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |
| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |
| REQUIRED_SKILLS | — |
| AVAILABLE_TOOLS | Read, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_case_update`, `sparkforge_aws_judge`, `sparkforge_aws_knowledge_path`, `sparkforge_aws_rules_lookup` |
| INPUTS | ver `## Pressupõe` na fonte |
| EXPECTED_OUTPUT | `case.findings_index` — caminho, contagem e `by_severity`; `case.skills_used` — a skill aplicada e o resultado |
| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |
| EXAMPLE_PROMPT | via coordenador — o `sf-judge` roda como passo |
| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |

### `sf-synthesizer`

| Campo | Valor |
|---|---|
| NAME | `sf-synthesizer` |
| PURPOSE | executor `synthesize` — ver fonte |
| DOMAIN | pipeline determinístico (`synthesize`) |
| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |
| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |
| REQUIRED_SKILLS | — |
| AVAILABLE_TOOLS | Read, Bash, Write |
| MCP_DEPENDENCIES | `sparkforge_aws_case_get`, `sparkforge_aws_case_update`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_next_step`, `sparkforge_aws_receipt_emit`, `sparkforge_aws_receipt_verify`, `sparkforge_aws_report_github`, `sparkforge_aws_report_sign`, `sparkforge_aws_report_verify`, `sparkforge_aws_resume`, `sparkforge_aws_telemetry_export`, `sparkforge_aws_validate_output` |
| INPUTS | ver `## Pressupõe` na fonte |
| EXPECTED_OUTPUT | `case.phase` — avançada; `case.gates` — o que foi satisfeito; `case.skills_used` — fechado com o desfecho |
| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |
| EXAMPLE_PROMPT | via coordenador — o `sf-synthesizer` roda como passo |
| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |

### `sf-verifier`

| Campo | Valor |
|---|---|
| NAME | `sf-verifier` |
| PURPOSE | executor `verify` — ver fonte |
| DOMAIN | pipeline determinístico (`verify`) |
| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |
| WHEN_NOT_TO_USE | ver `## Não faz` na fonte |
| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |
| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |
| REQUIRED_SKILLS | — |
| AVAILABLE_TOOLS | Read, Grep, Glob, Bash |
| MCP_DEPENDENCIES | `sparkforge_aws_analyze_call_graph`, `sparkforge_aws_change_plan`, `sparkforge_aws_change_propose`, `sparkforge_aws_change_sandbox`, `sparkforge_aws_gain`, `sparkforge_aws_knowledge_drift`, `sparkforge_aws_proof`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_runtime_detect` |
| INPUTS | ver `## Pressupõe` na fonte |
| EXPECTED_OUTPUT | `case.hypotheses` — um por achado P0/P1, com `status: rejected` quando refutado |
| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |
| EXAMPLE_PROMPT | via coordenador — o `sf-verifier` roda como passo |
| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |

## Skills

### `analyze-batch-loop`

| Campo | Valor |
|---|---|
| NAME | `analyze-batch-loop` |
| PURPOSE | Use quando o job processa dados em lotes com for/while, collect de chaves, isin(list) gigante ou filtros por batch id, ou dispara action/write/count/merge dentro de loop, e você suspeita de recomputaç… |
| TRIGGERS | Use quando o job processa dados em lotes com for/while, collect de chaves, isin(list) gigante ou filtros por batch id, ou dispara action/write/count/merge dentro de loop, e você suspeita de recomputação do DAG, lineage crescente, múltiplos commits Iceberg ou OOM acumulado por iteração. Use também quando perguntarem "por que esse batch demora mais a cada lote", "por que tem tantos commits/snapshots" ou "o job cresce com o número de lotes", mesmo sem mencionar loop explicitamente. Se você está prestes a contar iterações e estimar custo acumulado de cabeça, rode `sparkforge-aws analyze pyspark` e filtre por `pyspark.loop` em vez disso — cada ocorrência já vem marcada com se contém action, write e a profundidade de aninhamento. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai o loop do codigo e julga; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `pyspark-code-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que esse batch demora mais a cada lote” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-flink-job`

| Campo | Valor |
|---|---|
| NAME | `analyze-flink-job` |
| PURPOSE | Use quando houver dump JSON/JSONL de job Apache Flink ou Managed Flink e for preciso separar checkpoint, backpressure, state, configuração e métricas observadas sem inventar capacidade, limiar ou exat… |
| TRIGGERS | Use quando houver dump JSON/JSONL de job Apache Flink ou Managed Flink e for preciso separar checkpoint, backpressure, state, configuração e métricas observadas sem inventar capacidade, limiar ou exatamente-once. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai dumps Flink/Managed Flink e julga; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_analyze_flink`, `sparkforge_aws_analyze_transport`, `sparkforge_aws_next_step`, `sparkforge_aws_rules_lookup` |
| EXAMPLE | “pedido que case a descrição de `analyze-flink-job`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-functional-rules`

| Campo | Valor |
|---|---|
| NAME | `analyze-functional-rules` |
| PURPOSE | Use quando for necessario estudar regras funcionais, contratos, estados, excecoes e criterios de aceite |
| TRIGGERS | Use quando for necessario estudar regras funcionais, contratos, estados, excecoes e criterios de aceite. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — Especialista de dominio; despacho por coordenador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `data-quality-reviewer` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `analyze-functional-rules`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-library-call-graph`

| Campo | Valor |
|---|---|
| NAME | `analyze-library-call-graph` |
| PURPOSE | Use quando o job Glue chama uma biblioteca Python com múltiplos módulos, factories, decorators ou helpers, e você precisa saber onde estão leituras, actions, caches, loops, UDFs, mudanças de Spark con… |
| TRIGGERS | Use quando o job Glue chama uma biblioteca Python com múltiplos módulos, factories, decorators ou helpers, e você precisa saber onde estão leituras, actions, caches, loops, UDFs, mudanças de Spark config e writes que não aparecem ao olhar só o entrypoint — count() escondido em logger, persist sem unpersist, write dentro de helper três chamadas abaixo. Use também quando perguntarem "essa lib tem algum job escondido", "de onde vem essa action extra", "até onde essa função chega" ou "isso é seguro de chamar", mesmo sem mencionar grafo de chamadas. Se você está prestes a seguir import por import manualmente para responder isso, rode `sparkforge-aws analyze pyspark` e depois `sparkforge-aws analyze call-graph` em vez disso — ele devolve a profundidade mínima e o caminho até cada trabalho Spark alcançável, o que uma lista de arestas sozinha não responde. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — varre a biblioteca e devolve o grafo; leitura fechada |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `data-quality-reviewer`, `glue-incremental-performance-architect`, `pyspark-code-reviewer` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “essa lib tem algum job escondido” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-spark-plan`

| Campo | Valor |
|---|---|
| NAME | `analyze-spark-plan` |
| PURPOSE | Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, PartitionFilters/PushedFilters, Exchange/shuffle, estratégia de join (BroadcastHashJoin, SortM… |
| TRIGGERS | Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, PartitionFilters/PushedFilters, Exchange/shuffle, estratégia de join (BroadcastHashJoin, SortMergeJoin, ShuffledHashJoin, BroadcastNestedLoopJoin, CartesianProduct), Sort, Window, HashAggregate, Generate/explode, UDF Python no plano (BatchEvalPython/ArrowEvalPython) e o antes/depois do AQE — inclusive sob Photon (Databricks), via `plan.photon`. Use também quando a pergunta for "por que não usa broadcast", "por que lê a tabela inteira", "o filtro não desceu pro scan" ou "quantos shuffles esse job tem", sem citar explain. Salve o `explain` num arquivo e rode `sparkforge-aws analyze plan`: ele emite `plan.file_scan`, `plan.join`, `plan.python_udf`, `plan.aqe`, `plan.exchange` e `plan.photon`, sob SF-PLAN-001..004 e SF-PQ-002/004. Para causa (skew, spill, OOM), junte `analyze pyspark` e o `analyze event-log` da execução: o plano diz o que foi declarado, não o que cu... |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — interpreta um plano fisico ja salvo; nao pede nada a ninguem |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `pyspark-code-reviewer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “por que não usa broadcast” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-spark-ui`

| Campo | Valor |
|---|---|
| NAME | `analyze-spark-ui` |
| PURPOSE | Use quando houver um Spark event log, um job run id ou um Spark UI aberto de um job AWS Glue e for preciso achar stage dominante, skew de task, spill, GC, executor perdido ou subparalelismo… |
| TRIGGERS | Use quando houver um Spark event log, um job run id ou um Spark UI aberto de um job AWS Glue e for preciso achar stage dominante, skew de task, spill, GC, executor perdido ou subparalelismo. Use também quando a pergunta for "por que este stage demora", "por que uma task não termina", "o executor sumiu" ou "está com spill", mesmo que ninguém fale em event log. Se você está prestes a ler métrica de execução de Spark no olho, rode `sparkforge-aws collect event-log` e `sparkforge-aws analyze event-log` em vez disso — o extrator calcula p50/p95/max, spill e GC por stage, e o catálogo aplica os limiares versionados. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — coleta e julga o event log de um run identificado no pedido |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `emr-infra-reviewer`, `glue-incremental-performance-architect`, `spark-performance-architect`, `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “por que este stage demora” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `analyze-streaming-composition`

| Campo | Valor |
|---|---|
| NAME | `analyze-streaming-composition` |
| PURPOSE | Use quando houver facts já extraídos de Structured Streaming e de Iceberg, Kafka ou Kinesis e for preciso correlacionar progresso, snapshots ou backlog sem escolher causa por intuição |
| TRIGGERS | Use quando houver facts já extraídos de Structured Streaming e de Iceberg, Kafka ou Kinesis e for preciso correlacionar progresso, snapshots ou backlog sem escolher causa por intuição. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — compoe facts declarados de streaming, transporte e Iceberg; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `analyze-streaming-composition`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-billing-and-cost-management`

| Campo | Valor |
|---|---|
| NAME | `aws-billing-and-cost-management` |
| PURPOSE | Use quando for analisar custos AWS, encontrar economias, gerenciar budgets, avaliar Savings Plans e Reserved Instances, right-size EC2/Lambda/RDS/EBS com Compute Optimizer, consultar pricing de serviç… |
| TRIGGERS | Use quando for analisar custos AWS, encontrar economias, gerenciar budgets, avaliar Savings Plans e Reserved Instances, right-size EC2/Lambda/RDS/EBS com Compute Optimizer, consultar pricing de serviço, query CUR com Athena, detectar anomalias de custo, escopar custos a billing views, ou monitorar Free Tier. Gatilhos: conta AWS, análise de custo, reduzir spend, savings plan, reserved instance, right-size, budget alert, cost optimization, pricing, free tier, cost anomaly, CUR, cost audit, billing view. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — analise de custo AWS (CUR, Savings Plans); pode mutar budget e alerta ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-billing-and-cost-management`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-database`

| Campo | Valor |
|---|---|
| NAME | `aws-database` |
| PURPOSE | Use quando precisar escolher, comparar, recomendar, iniciar ou operar um banco de dados AWS — roteia para o servico correto entre Aurora, DSQL, RDS, DynamoDB, ElastiCache, MemoryDB, DocumentDB, Keyspa… |
| TRIGGERS | Use quando precisar escolher, comparar, recomendar, iniciar ou operar um banco de dados AWS — roteia para o servico correto entre Aurora, DSQL, RDS, DynamoDB, ElastiCache, MemoryDB, DocumentDB, Keyspaces, Timestream, Neptune. Aplica quando alguem descreve uma aplicacao que vai armazenar, recuperar ou gerenciar dados na AWS, mesmo sem mencionar "banco de dados" explicitamente. Cobre relacional (Aurora, DSQL, RDS PostgreSQL/MySQL/MariaDB/Oracle/SQL Server/Db2), key-value (DynamoDB), wide-column (Keyspaces), documento (DocumentDB), grafo (Neptune), serie temporal (Timestream) e em-memory/cache (ElastiCache, MemoryDB). NAO use para armazenamento de objeto/arquivo (S3, EFS, FSx — use aws-storage) nem para analytics query engines (Athena, Redshift). |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — roteia para skill de database AWS (Aurora, RDS, DynamoDB, etc); pode mutar configuracao de instancia ao vivo, fronteira exige confirmacao |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “banco de dados” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-iam`

| Campo | Valor |
|---|---|
| NAME | `aws-iam` |
| PURPOSE | Use quando precisar corrigir comportamentos de IAM que agentes frequentemente erram — avaliação de policy, trust policies, limites de STS, Organizations, SAML/MFA — ou for criar roles de serviço, gera… |
| TRIGGERS | Use quando precisar corrigir comportamentos de IAM que agentes frequentemente erram — avaliação de policy, trust policies, limites de STS, Organizations, SAML/MFA — ou for criar roles de serviço, gerar policies baseline a partir de código-fonte ou Terraform plan JSON, configurar confused deputy protection, ou escrever policies com condition operators (ForAnyValue/ForAllValues com Null checks). Aplica-se a criação de roles IAM, escrita de IAM/bucket policies, trabalho com STS, Organizations ou condition operators. NÃO use para autorização não-IAM (Cognito user-pool policies, RBAC app-level). |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — referencia de IAM (policies, roles, trust); pode mutar policy e role ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-iam`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-messaging-and-streaming`

| Campo | Valor |
|---|---|
| NAME | `aws-messaging-and-streaming` |
| PURPOSE | Use quando for raciocinar sobre padrões de mensageria e streaming na AWS — escolher entre SQS, SNS, EventBridge, Amazon MQ, Kinesis Data Streams, Data Firehose, Managed Service for Apache Flink e MSK,… |
| TRIGGERS | Use quando for raciocinar sobre padrões de mensageria e streaming na AWS — escolher entre SQS, SNS, EventBridge, Amazon MQ, Kinesis Data Streams, Data Firehose, Managed Service for Apache Flink e MSK, ou decidir qual padrão (mensageria vs. streaming) cabe a um workload. Use também para identificar qual serviço AWS possui cada canal de comunicação com cliente (e-mail via SES; WhatsApp, SMS, MMS, RCS, voice e mobile push via AWS End User Messaging) e rotear à skill especializada. NÃO use para perguntas detalhadas de MSK ou Managed Service for Apache Flink — prefira skills específicas. Não configura canais de comunicação com cliente; adia às skills especializadas. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — referencia de SQS, SNS, EventBridge, Kinesis, MSK; pode mutar fila, topico e stream ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `cdc-contract-reviewer`, `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-messaging-and-streaming`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-observability`

| Campo | Valor |
|---|---|
| NAME | `aws-observability` |
| PURPOSE | Use quando for configurar, depurar ou otimizar observabilidade AWS com CloudWatch (Log Insights, Metrics, Alarms, Dashboards, EMF), X-Ray, CloudTrail e ADOT (AWS Distro for OpenTelemetry), ou habilita… |
| TRIGGERS | Use quando for configurar, depurar ou otimizar observabilidade AWS com CloudWatch (Log Insights, Metrics, Alarms, Dashboards, EMF), X-Ray, CloudTrail e ADOT (AWS Distro for OpenTelemetry), ou habilitar/onboardar um serviço em Application Signals via ADOT auto-instrumentation SDKs. Aplica-se a alarms (métrico, composto, anomalia), dashboards, custom metrics/EMF, tracing e sampling, config de ADOT collector, CloudTrail auditing, synthetics/canaries e Dynamic Instrumentation. NÃO use para logging de aplicação ou detecção de ameaças de segurança. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — procedimento de CloudWatch, X-Ray, CloudTrail; pode mutar alarme, dashboard e trail ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-observability`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-sdk-python-usage`

| Campo | Valor |
|---|---|
| NAME | `aws-sdk-python-usage` |
| PURPOSE | Use quando for escrever código Python que usa serviços AWS via boto3 ou botocore — criar service clients ou resources, configurar sessions e credenciais, tratar erros com ClientError, usar paginators… |
| TRIGGERS | Use quando for escrever código Python que usa serviços AWS via boto3 ou botocore — criar service clients ou resources, configurar sessions e credenciais, tratar erros com ClientError, usar paginators e waiters, transferências S3 e presigned URLs, operações de tabela DynamoDB, ou qualquer configuração de client boto3/botocore. Use sempre que código Python importar boto3 ou botocore, ou quando o usuário perguntar sobre operações AWS em Python. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — padroes de boto3/botocore; e referencia de uso de SDK, nao muta infra por si, mas pode executar chamadas AWS se o operador pedir |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-sdk-python-usage`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-security`

| Campo | Valor |
|---|---|
| NAME | `aws-security` |
| PURPOSE | Use quando a pergunta envolver serviços AWS de segurança — Security Hub V2 (OCSF) findings, conectores, agregadores, automation rules e resumo de postura; Security Hub CSPM (V1/ASFF) controles e padrõ… |
| TRIGGERS | Use quando a pergunta envolver serviços AWS de segurança — Security Hub V2 (OCSF) findings, conectores, agregadores, automation rules e resumo de postura; Security Hub CSPM (V1/ASFF) controles e padrões de compliance; GuardDuty threat findings; Inspector vulnerability findings; Macie sensitive data findings; Detective investigation; e Security Lake. Use para postura de segurança, Exposure findings, controles CSPM falhados, threat findings, vulnerability findings, sensitive data findings, automation rules ou configuração cross-service de segurança em ambientes AWS. Procedimentos usam sintaxe AWS CLI padrão e funcionam com ou sem o AWS MCP server. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — procedimento de Security Hub, GuardDuty, Inspector; pode mutar finding e detector ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-security`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-serverless`

| Campo | Valor |
|---|---|
| NAME | `aws-serverless` |
| PURPOSE | Use quando precisar construir, deployar, gerenciar, debugar, configurar ou otimizar aplicacoes serverless na AWS com Lambda, API Gateway, Step Functions, EventBridge e SAM/CDK… |
| TRIGGERS | Use quando precisar construir, deployar, gerenciar, debugar, configurar ou otimizar aplicacoes serverless na AWS com Lambda, API Gateway, Step Functions, EventBridge e SAM/CDK. Cobre cold starts, CORS, event source mappings, troubleshooting, concorrencia, SnapStart, Powertools, Function URLs, EventBridge Scheduler, Lambda layers e production readiness. Aplica quando alguem menciona Lambda, API Gateway, Step Functions, SAM templates, CDK serverless stacks, triggers de DynamoDB Stream, SQS event sources, cold starts, timeouts, erros 502/504, throttling, concorrencia, CORS, Powertools ou qualquer arquitetura event-driven na AWS, mesmo sem a palavra "serverless". NAO use para EC2, containers ECS/Fargate ou Amplify hosting. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — procedimento de Lambda, Step Functions, EventBridge; pode mutar funcao e state machine ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “serverless” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `aws-storage`

| Campo | Valor |
|---|---|
| NAME | `aws-storage` |
| PURPOSE | Use quando precisar escolher, comparar ou operar servicos de armazenamento AWS — S3 (General Purpose, Express One Zone, Tables, Vectors, Files), EFS, FSx (Lustre, ONTAP, OpenZFS, Windows), EBS, DataSy… |
| TRIGGERS | Use quando precisar escolher, comparar ou operar servicos de armazenamento AWS — S3 (General Purpose, Express One Zone, Tables, Vectors, Files), EFS, FSx (Lustre, ONTAP, OpenZFS, Windows), EBS, DataSync, Transfer Family, Storage Gateway, AWS Backup. Cobre selecao de servico por workload, custo, performance, configuracao, seguranca, troubleshooting e migracao de dados. Aplica quando alguem pergunta onde armazenar ou arquivar dados, qual servico de storage escolher, como comparar dois, como migrar de on-premises ou entre servicos AWS, como proteger/replicar/recuperar dados, como otimizar custo de storage, onde deployar NFS/SMB/POSIX compartilhado, onde guardar vector embeddings ou dados tabulares, ou como um servico de storage AWS funciona. NAO use para motores de consulta SQL (Athena, Spark, Redshift, EMR), ETL (Glue), streaming (Kafka, MSK, Kinesis) ou bancos gerenciados (RDS, Aurora, DynamoDB). |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — referencia de storage AWS (S3, EFS, FSx, EBS); pode mutar configuracao de bucket e lifecycle ao vivo, fronteira exige confirmacao do operador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `aws-storage`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `benchmark-pyspark-job`

| Campo | Valor |
|---|---|
| NAME | `benchmark-pyspark-job` |
| PURPOSE | Use quando precisar comprovar — não estimar — o efeito de uma mudança de performance num job Glue, com comparação antes/depois de duração de stage, spill, GC e executor perdido, isolando uma variável… |
| TRIGGERS | Use quando precisar comprovar — não estimar — o efeito de uma mudança de performance num job Glue, com comparação antes/depois de duração de stage, spill, GC e executor perdido, isolando uma variável por vez. Use também quando for escrever "X% mais rápido", "reduziu o shuffle pela metade", "resolveu o OOM" ou qualquer alegação quantificada de ganho. Se você está prestes a escrever um percentual de ganho sem rodar `sparkforge-aws validate --findings`, pare — o schema rejeita `expected_effect` quantificado (%, x, vezes) sem `benchmark_ref`, e ganho previsto sem benchmark é invenção, não resultado. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — o passo 2 e `aplique a mudanca` entre as duas coletas: exige um run novo e o id dele, que so aparece depois de alguem publicar a mudanca |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `athena-query-optimizer`, `emr-infra-reviewer`, `glue-incremental-performance-architect`, `iceberg-performance-engineer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_benchmark`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “X% mais rápido” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `compare-releases`

| Campo | Valor |
|---|---|
| NAME | `compare-releases` |
| PURPOSE | Use quando precisar saber o que muda de COMPONENTE entre dois runtimes antes de uma migração — "vou de emr-6.15.0 para emr-7.5.0, que versão de Spark e de Iceberg eu passo a ter", "o mesmo emr-7.7.0 n… |
| TRIGGERS | Use quando precisar saber o que muda de COMPONENTE entre dois runtimes antes de uma migração — "vou de emr-6.15.0 para emr-7.5.0, que versão de Spark e de Iceberg eu passo a ter", "o mesmo emr-7.7.0 no EC2 e no EKS é a mesma coisa?", "que versão de Python o Glue 5.1 publica" — e também quando alguém já escreveu um número de versão num plano de migração e ninguém conferiu de onde ele veio. Rode `sparkforge-aws release describe` e `sparkforge-aws release diff` em vez de ler a página da AWS no olho. Esta skill NÃO responde se algo quebra: diff de versão não é avaliação de compatibilidade, e essa pergunta é do MigrationAssessment (`sparkforge-aws migrate glue` e `sparkforge-aws migrate emr`, que hoje cobrem as quatro plataformas). Para julgar a migração de um job Glue degrau a degrau, a skill é `migrate-glue-6`. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — le as quatro matrizes de versao e devolve o diff com o eixo declarado; nao le artefato do operador e nao julga |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-runtime-specialist` |
| RELATED_MCP_TOOLS | `sparkforge_aws_migration_assess`, `sparkforge_aws_release_describe`, `sparkforge_aws_release_diff` |
| EXAMPLE | “vou de emr-6.15.0 para emr-7.5.0, que versão de Spark e de Iceberg eu passo a ter” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `design-data-architecture`

| Campo | Valor |
|---|---|
| NAME | `design-data-architecture` |
| PURPOSE | Use quando for necessario desenhar arquiteturas de dados completas |
| TRIGGERS | Use quando for necessario desenhar arquiteturas de dados completas. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — Especialista de dominio; despacho por coordenador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-lake-formation-specialist`, `sf-security-reviewer` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `design-data-architecture`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `design-incremental-processing`

| Campo | Valor |
|---|---|
| NAME | `design-incremental-processing` |
| PURPOSE | Use quando um job dito incremental continua lento mesmo com pouca entrada, faz scan global, recomputa estado histórico, ou você precisa projetar bootstrap, ciclos, backfill, late data, deletes e idemp… |
| TRIGGERS | Use quando um job dito incremental continua lento mesmo com pouca entrada, faz scan global, recomputa estado histórico, ou você precisa projetar bootstrap, ciclos, backfill, late data, deletes e idempotência de forma que a entrada pequena realmente reduza bytes e arquivos lidos. Use também quando perguntarem "por que o incremental demora igual ao full", "isso é realmente incremental" ou "como eu desenho o reprocessamento disso", mesmo sem citar watermark ou bookmark. Se você está prestes a comparar full e incremental lendo os dois caminhos de código de cabeça, rode `sparkforge-aws analyze pyspark` nos dois e compare os facts — mas saiba de antemão que o extrator mostra a forma do código, não se o volume lido caiu de fato: isso só o event log confirma. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — o contrato de saida tem dezesseis campos de desenho que nenhum extrator preenche; a propria skill os chama de perguntas |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que o incremental demora igual ao full” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `design-realtime-data-architecture`

| Campo | Valor |
|---|---|
| NAME | `design-realtime-data-architecture` |
| PURPOSE | Use quando houver requisitos de workload streaming e for necessário comparar candidatos por constraints, preservando assumptions, unresolved e ADR sem fabricar vencedor |
| TRIGGERS | Use quando houver requisitos de workload streaming e for necessário comparar candidatos por constraints, preservando assumptions, unresolved e ADR sem fabricar vencedor. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — compara candidatos streaming por constraints declaradas; recusa vencedor sem evidencia |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `design-realtime-data-architecture`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `design-s3-data-lake`

| Campo | Valor |
|---|---|
| NAME | `design-s3-data-lake` |
| PURPOSE | Use quando for necessario projetar S3, zonas, lifecycle e governanca de data lake |
| TRIGGERS | Use quando for necessario projetar S3, zonas, lifecycle e governanca de data lake. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — Especialista de dominio; despacho por coordenador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-lake-formation-specialist`, `sf-security-reviewer` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `design-s3-data-lake`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `diagnose-data-skew`

| Campo | Valor |
|---|---|
| NAME | `diagnose-data-skew` |
| PURPOSE | Use quando o judge já disparou SF-UI-001 (skew de duração de task) e for preciso decidir entre skew de dados e skew de computação, tratar hot key, null ou valor sentinela, ou desenhar o experimento de… |
| TRIGGERS | Use quando o judge já disparou SF-UI-001 (skew de duração de task) e for preciso decidir entre skew de dados e skew de computação, tratar hot key, null ou valor sentinela, ou desenhar o experimento de mitigação (broadcast, AQE skew join, salting). Use também quando a pergunta for "uma task não termina", "uma chave concentra tudo", "o job trava numa partição só" ou "uma partição ficou gigante", mesmo sem citar SF-UI-001. Se você está prestes a aplicar salting ou repartition por instinto, rode `sparkforge-aws collect event-log`, `sparkforge-aws analyze event-log` e `sparkforge-aws judge --show-skipped` em vez disso — cruzar SF-UI-001 com SF-UI-002 diz se é skew de dados (tratável na chave) ou de computação (repartition não muda nada, e é o erro mais caro desta análise). |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — cruza SF-UI-001 com SF-UI-002 sobre o event log que ela mesma coleta |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “uma task não termina” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `diagnose-lakeformation-access`

| Campo | Valor |
|---|---|
| NAME | `diagnose-lakeformation-access` |
| PURPOSE | Use quando um job Glue lê tabela governada e falha ao escrever, ou quando alguém pergunta "por que a leitura passa e a escrita não?", "tomo AccessDenied e já dei SELECT", "troquei writeTo/insertInto/I… |
| TRIGGERS | Use quando um job Glue lê tabela governada e falha ao escrever, ou quando alguém pergunta "por que a leitura passa e a escrita não?", "tomo AccessDenied e já dei SELECT", "troquei writeTo/insertInto/INSERT INTO e continua igual", "migrei de Glue 4.0 e nada funciona", ou quando é preciso descobrir QUAL permissão falta em vez de em qual plano a operação parou. É o procedimento que ORDENA os quatro coletores de governança de acesso; para a pergunta "esta configuração é suportada?" isolada, use `lakeformation-fgac-guard`. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — coleta da AWS ao vivo e recomenda mudanca de permissao; a decisao sobe a quem responde pela governanca, e um subagente nao pode perguntar |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “por que a leitura passa e a escrita não?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `diagnose-oom`

| Campo | Valor |
|---|---|
| NAME | `diagnose-oom` |
| PURPOSE | Use quando um job Glue falha com OutOfMemory, "Container killed by YARN", "GC overhead limit exceeded", ExecutorLostFailure, estouro de Python worker/pandas_udf, ou frases como "o job morreu depois de… |
| TRIGGERS | Use quando um job Glue falha com OutOfMemory, "Container killed by YARN", "GC overhead limit exceeded", ExecutorLostFailure, estouro de Python worker/pandas_udf, ou frases como "o job morreu depois de 3 horas" e "aumentei a memória e continuou". Use para classificar se é heap de driver, heap de executor, overhead de container, broadcast, metadata/plan explosion ou Python worker antes de mitigar. Se você está prestes a estimar heap e GC no olho, rode `sparkforge-aws collect event-log`, `sparkforge-aws analyze event-log` e `sparkforge-aws judge` em vez disso — o fact `spark.executor.lost` já vem com `heap_oom_in_log`: executor removido sem OOM de heap no log é estouro de container fora do heap (a correção é `memoryOverhead`, não `memory`), e é o OOM mais mal diagnosticado que existe. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — classifica o OOM por `heap_oom_in_log`; discriminador esta no artefato |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “Container killed by YARN” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `glue-incremental-performance-architect`

| Campo | Valor |
|---|---|
| NAME | `glue-incremental-performance-architect` |
| PURPOSE | Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key sobre tabela Iceberg bilionária, batching por lote, OOM que só aparece depois de… |
| TRIGGERS | Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key sobre tabela Iceberg bilionária, batching por lote, OOM que só aparece depois de horas, ou carga que varia de dezenas a milhões de registros — e for preciso orquestrar as skills especializadas em vez de mexer isoladamente num sintoma. Use também quando a pergunta for "o job incremental tá tão lento quanto o full", "o job só morre de memória depois de um bom tempo rodando" ou "esse job tem dois jeitos de rodar e não sei qual tá causando o problema", mesmo que ninguém fale em full/incremental. Se você está prestes a mexer em workers, shuffle partitions ou cache antes de mapear a biblioteca inteira, pare — é exatamente isso que este documento existe para evitar. Leia `PROMPT_INICIAL_MESTRE.md` primeiro. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — orquestra as skills especializadas por `next-step` e le PROMPT_INICIAL_MESTRE.md; subagente nao gera subagente por default |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “o job incremental tá tão lento quanto o full” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `harden-s3-bucket`

| Campo | Valor |
|---|---|
| NAME | `harden-s3-bucket` |
| PURPOSE | Use quando for proteger um bucket S3 — criar bucket novo já hardenado, auditar bucket existente contra controles de segurança, remediar finding de security hub/guardduty, configurar encriptação (SSE-S… |
| TRIGGERS | Use quando for proteger um bucket S3 — criar bucket novo já hardenado, auditar bucket existente contra controles de segurança, remediar finding de security hub/guardduty, configurar encriptação (SSE-S3 com Bucket Keys, SSE-KMS com chave gerenciada pelo cliente), ou habilitar logging/monitoramento (server access logging, CloudTrail data events, GuardDuty, Config rules). Use também quando a pergunta for "esse bucket está seguro", "por que o finding de bucket público", "qual a diferença entre SSE-S3 e SSE-KMS aqui" ou "como bloqueio SSE-C", mesmo sem citar "harden". NÃO use para operações de dado S3 (upload/download/list), setup de S3 Tables (use `provision-s3-tables-table`), descoberta de assets existentes, ou hardening de serviços que não S3. Se você está prestes a rodar `put-bucket-policy` sem back up da policy atual, pare — `put-bucket-policy` substitui a policy inteira e descarta statements existentes em silêncio. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — executa `put-bucket-policy`, `put-bucket-encryption`, `create-detector` ao vivo; a fronteira `## Nao faz` exige confirmacao do operador por comando de escrita, inalcancavel em subagente |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “esse bucket está seguro” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `iceberg-v3-readiness`

| Campo | Valor |
|---|---|
| NAME | `iceberg-v3-readiness` |
| PURPOSE | Use quando alguém pergunta "posso subir essa tabela para Iceberg format v3?", "o Athena lê v3?", "vale a pena o VARIANT / os deletion vectors / o row lineage?" ou quando uma query em Athena passou a f… |
| TRIGGERS | Use quando alguém pergunta "posso subir essa tabela para Iceberg format v3?", "o Athena lê v3?", "vale a pena o VARIANT / os deletion vectors / o row lineage?" ou quando uma query em Athena passou a falhar com `Cannot read unsupported version 3` depois de uma migração de runtime. Use antes de qualquer recomendação de mudar `format-version`. Se você está prestes a responder de memória o que cada engine suporta, rode `sparkforge-aws iceberg assess-upgrade dir --from 2 --to 3` — a matriz de suporte tem uma célula por par engine/feature, cada uma com fonte, e a maioria é `UNKNOWN`, que é o resultado honesto e não uma lacuna a preencher por inferência. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — subir `format-version` e decisao de IDA, e a skill exige o inventario de consumidores -- que e conhecimento da organizacao, escrito por uma pessoa, nao derivavel de artefato. Dentro de subagente a pergunta 'quem mais le esta tabela?' e inalcancavel, e a resposta errada quebra o consumidor dias depois |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `iceberg-performance-engineer` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “posso subir essa tabela para Iceberg format v3?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `lakeformation-architecture`

| Campo | Valor |
|---|---|
| NAME | `lakeformation-architecture` |
| PURPOSE | Use quando avaliar arquitetura AWS Lake Formation antes de recomendar FGAC, Full Table Access, migração Glue 4/5, EMR EC2/Serverless ou acesso cross-account… |
| TRIGGERS | Use quando avaliar arquitetura AWS Lake Formation antes de recomendar FGAC, Full Table Access, migração Glue 4/5, EMR EC2/Serverless ou acesso cross-account. Exige separar engine/runtime, formato, operação, ownership de catálogo, RAM/resource link, credential vending e permissões; falha fechado quando capability ou evidência não está declarada. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — avalia declaracao offline de release, modelo, formato, operacao e ownership; nao chama AWS nem altera governanca |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-lake-formation-specialist`, `sf-runtime-specialist` |
| RELATED_MCP_TOOLS | `sparkforge_aws_lakeformation_architect` |
| EXAMPLE | “pedido que case a descrição de `lakeformation-architecture`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `lakeformation-fgac-guard`

| Campo | Valor |
|---|---|
| NAME | `lakeformation-fgac-guard` |
| PURPOSE | Use quando um job Glue declara `--enable-lakeformation-fine-grained-access` ou configuração de Full Table Access e alguém pergunta "posso passar um JAR extra?", "por que meu conector parou de funciona… |
| TRIGGERS | Use quando um job Glue declara `--enable-lakeformation-fine-grained-access` ou configuração de Full Table Access e alguém pergunta "posso passar um JAR extra?", "por que meu conector parou de funcionar sob FGAC?", "por que a leitura funciona e a escrita não?", "troquei `writeTo` por `INSERT INTO` e continua dando erro de Lake Formation", "dá para usar UDF Java / HiveUDF / data source customizado com controle de acesso fino?" ou quando é preciso decidir entre FGAC e Full Table Access, ou entre manter FGAC e manter uma dependência. Use antes de recomendar `--extra-jars` em qualquer job com FGAC ligado, e antes de trocar a API de escrita de um job que falha sob Lake Formation. Se você está prestes a ler o Terraform no olho procurando os argumentos, rode `sparkforge-aws migrate glue dir --from 5.1 --to 6.0` — a área `SF-LF` correlaciona o que precisa ser correlacionado, e é isso que separa a regra de um gerador de acusação falsa. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — correlaciona FGAC e classpath no .tf que ja esta em disco |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-lake-formation-specialist` |
| RELATED_MCP_TOOLS | `sparkforge_aws_analyze_glue_resource_link`, `sparkforge_aws_analyze_iam_access`, `sparkforge_aws_analyze_lakeformation_grants`, `sparkforge_aws_collect_glue_resource_link`, `sparkforge_aws_collect_iam_access`, `sparkforge_aws_collect_lakeformation` |
| EXAMPLE | “posso passar um JAR extra?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `migrate-glue-6`

| Campo | Valor |
|---|---|
| NAME | `migrate-glue-6` |
| PURPOSE | Use quando alguém pergunta "dá para subir esse job para o Glue 6.0?", "o que quebra se eu migrar de 4.0/5.0/5.1 para 6.0?", "vale a pena migrar por causa dos 30% mais barato?" ou precisa de um plano d… |
| TRIGGERS | Use quando alguém pergunta "dá para subir esse job para o Glue 6.0?", "o que quebra se eu migrar de 4.0/5.0/5.1 para 6.0?", "vale a pena migrar por causa dos 30% mais barato?" ou precisa de um plano de migração entre versões de runtime do AWS Glue. Use também quando o job já foi migrado e passou a falhar com `NoSuchMethodError`, `NoSuchFieldError` ou erro de ANSI mode. Se você está prestes a ler o guia de migração da AWS e comparar com o código no olho, rode `sparkforge-aws migrate glue dir --from X --to Y` em vez disso — o motor expande o par em degraus, julga cada um com o catálogo versionado e devolve os eixos que **não** foram avaliados em vez de deixá-los passar como aprovados. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai a arvore do job e julga degrau a degrau; leitura fechada |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-runtime-specialist` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “dá para subir esse job para o Glue 6.0?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `optimize-iceberg-table`

| Campo | Valor |
|---|---|
| NAME | `optimize-iceberg-table` |
| PURPOSE | Use quando tabelas Apache Iceberg no Glue Data Catalog degradam por excesso de data files pequenos, delete files acumulados, snapshots ou manifests crescendo sem parar, partition spec inadequado ou wr… |
| TRIGGERS | Use quando tabelas Apache Iceberg no Glue Data Catalog degradam por excesso de data files pequenos, delete files acumulados, snapshots ou manifests crescendo sem parar, partition spec inadequado ou write.distribution-mode incoerente com particionamento — e for preciso decidir entre compaction, rewrite manifests e expire snapshots com evidência, não por rotina. Use também quando a pergunta for "essa tabela Iceberg tá lenta para consultar", "o Athena demora para planejar essa tabela" ou "quantos snapshots essa tabela já acumulou", mesmo que ninguém fale em metadata table. Se você está prestes a rodar `SELECT * FROM db.tabela.files` no olho para contar arquivo pequeno, rode `sparkforge-aws collect iceberg-metadata` e `sparkforge-aws analyze iceberg` em vez disso — o extrator resume files, delete files, snapshots, manifests e partições deterministicamente, e o catálogo aplica os limiares versionados. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — `expire_snapshots` e `remove_orphan_files` nao tem desfazer, e a propria skill exige que a retencao venha do dono dos dados. Dentro de subagente essa confirmacao e inalcancavel |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `athena-query-optimizer`, `glue-incremental-performance-architect`, `iceberg-performance-engineer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “essa tabela Iceberg tá lenta para consultar” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `optimize-latest-per-key`

| Campo | Valor |
|---|---|
| NAME | `optimize-latest-per-key` |
| PURPOSE | Use quando o job calcula o registro mais recente por chave (row_number/Window, max_by, max(struct), join-back) sobre tabelas Spark/Iceberg grandes, e suspeitar de Window global sem partitionBy, sort/s… |
| TRIGGERS | Use quando o job calcula o registro mais recente por chave (row_number/Window, max_by, max(struct), join-back) sobre tabelas Spark/Iceberg grandes, e suspeitar de Window global sem partitionBy, sort/shuffle de todo o histórico, empates por timestamp mal tratados, late data ou recomputação a cada ciclo. Use também quando perguntarem "por que o latest demora tanto", "isso escala com o histórico inteiro" ou "o resultado muda entre execuções", mesmo sem citar Window ou row_number. Se você está prestes a inspecionar a chamada de Window de cabeça, rode `sparkforge-aws analyze pyspark` e filtre por `pyspark.window` e `pyspark.chain` em vez disso — eles dizem se a Window tem partitionBy e onde o join entra na cadeia, mas não decidem se a chave escolhida é a correta: isso é julgamento seu. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — a secao `Perguntas que o extrator nao faz por voce` sao quatro perguntas de semantica de negocio -- desempate, timezone, correcao retroativa |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que o latest demora tanto” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `optimize-parquet-layout`

| Campo | Valor |
|---|---|
| NAME | `optimize-parquet-layout` |
| PURPOSE | Use quando datasets Parquet no S3 (fora do Iceberg) sofrem com small files, listing lento, milhares de objetos por prefixo, arquivo por chave na escrita, ou leitura que não faz partition/predicate pus… |
| TRIGGERS | Use quando datasets Parquet no S3 (fora do Iceberg) sofrem com small files, listing lento, milhares de objetos por prefixo, arquivo por chave na escrita, ou leitura que não faz partition/predicate pushdown. Use também quando a pergunta for "o S3 tá cheio de arquivinho", "a leitura desse dataset demora antes mesmo da primeira task rodar" ou "cada execução gera um arquivo por cliente", mesmo que ninguém fale em Parquet. Se você está prestes a contar arquivo com `aws s3 ls` no olho, salve `aws s3api list-objects-v2` num arquivo e rode `sparkforge-aws analyze s3-listing` — ele emite `s3.prefix_summary` e o `judge` aplica `SF-PQ-001`, `SF-PQ-003` e `SF-PQ-005`. Para o lado da leitura, `sparkforge-aws analyze plan` emite `plan.file_scan` e cobre `SF-PQ-002` e `SF-PQ-004`; `analyze pyspark` e `analyze catalog-schema` fecham escrita e cardinalidade. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — junta listagem, plano e catalogo, todos coletaveis so lendo |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `athena-query-optimizer`, `glue-incremental-performance-architect`, `iceberg-performance-engineer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “o S3 tá cheio de arquivinho” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `optimize-pyspark-code`

| Campo | Valor |
|---|---|
| NAME | `optimize-pyspark-code` |
| PURPOSE | Use quando revisar, refatorar ou otimizar código PySpark/Spark SQL para AWS Glue — script, função, módulo, PR ou trecho de DataFrame — suspeito de UDF Python evitável, collect/toPandas, join sem reduç… |
| TRIGGERS | Use quando revisar, refatorar ou otimizar código PySpark/Spark SQL para AWS Glue — script, função, módulo, PR ou trecho de DataFrame — suspeito de UDF Python evitável, collect/toPandas, join sem redução prévia, cache indevido, coalesce(1), repartition arbitrário, explode sem controle, sequência longa de withColumn, dropDuplicates sem chave explícita ou spark.conf.set em runtime. Use também quando a pergunta for "por que esse código está lento", "isso vai escalar", "tem algo errado nesse DataFrame" ou "como eu melhoro isso", mesmo que ninguém cite UDF, shuffle ou cardinalidade pelo nome. Use também quando o job constrói `GraphFrame` e chama `connectedComponents`, `pageRank`, `aggregateMessages` ou `pregel` — é o mesmo `.py`, lido por `sparkforge-aws analyze graph`. Se você está prestes a ler o arquivo linha a linha procurando esses padrões, rode `sparkforge-aws analyze pyspark` em vez disso — ele varre a árvore inteira, não uma amostra, e ancora cada achado em file:line:col. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — mesma forma de `review-pyspark-pr`: extrai, julga, propoe diff |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `pyspark-code-reviewer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que esse código está lento” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `optimize-variable-volume-job`

| Campo | Valor |
|---|---|
| NAME | `optimize-variable-volume-job` |
| PURPOSE | Use quando o mesmo job Glue roda de dezenas de registros a centenas de milhões e um único perfil configurado para o pior caso fica caro em microcarga e ainda inadequado no full… |
| TRIGGERS | Use quando o mesmo job Glue roda de dezenas de registros a centenas de milhões e um único perfil configurado para o pior caso fica caro em microcarga e ainda inadequado no full. Use também quando a pergunta for "por que a carga vazia demora 5 minutos", "o job de teste custa quase igual ao de produção" ou "ficou mais lento essa semana" num job cujo volume varia muito entre execuções. Se você está prestes a comparar runs de volumes diferentes só de cabeça, rode `sparkforge-aws analyze event-log` em cada run e `sparkforge-aws analyze pyspark` no código em vez disso — subparalelismo (SF-UI-006) que é esperado numa carga micro é sintoma real numa carga full, e o catálogo não distingue os dois perfis sozinho; quem separa é você. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — classificar execucoes por perfil parte do volume observado no workload, e compara N runs que o operador escolhe |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `glue-infra-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que a carga vazia demora 5 minutos” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `propose-change-pr`

| Campo | Valor |
|---|---|
| NAME | `propose-change-pr` |
| PURPOSE | Use quando o operador quiser levar ao repositório uma mudança de configuração que já passou pelo sandbox — "abre o PR dessa mudança", "propõe essa troca", "o sandbox passou, e agora?"… |
| TRIGGERS | Use quando o operador quiser levar ao repositório uma mudança de configuração que já passou pelo sandbox — "abre o PR dessa mudança", "propõe essa troca", "o sandbox passou, e agora?". A sessão monta o pacote com `sparkforge_aws_change_propose` e roda os comandos git/gh do `commands.md` passo a passo, PARANDO para confirmação explícita antes de `git push` e de `gh pr create`. O pacote nunca roda git; quem roda é a sessão, com aprovação humana. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — roda git/gh na arvore do operador e para para confirmacao humana antes de push e de abrir o PR; despachada, ninguem estaria la para confirmar |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_change_plan`, `sparkforge_aws_change_propose`, `sparkforge_aws_change_sandbox`, `sparkforge_aws_report_verify`, `sparkforge_aws_tune` |
| EXAMPLE | “abre o PR dessa mudança” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `provision-s3-tables-table`

| Campo | Valor |
|---|---|
| NAME | `provision-s3-tables-table` |
| PURPOSE | Use quando for criar uma tabela Iceberg gerenciada por Amazon S3 Tables (o produto `s3tables`, não o Glue Data Catalog tradicional) — table bucket, namespace, tabela, schema, particionamento, integraç… |
| TRIGGERS | Use quando for criar uma tabela Iceberg gerenciada por Amazon S3 Tables (o produto `s3tables`, não o Glue Data Catalog tradicional) — table bucket, namespace, tabela, schema, particionamento, integração com o catálogo `s3tablescatalog` e IAM no namespace `s3tables:*`. Use também quando a pergunta for "como crio uma tabela Iceberg sem gerenciar compaction", "S3 Tables vale vs Glue Data Catalog" ou "por que `s3:*` não funciona no S3 Tables", mesmo sem citar o produto pelo nome. NÃO use para criar tabela no Glue Data Catalog tradicional (esse caminho não está aqui — use `design-s3-data-lake` para o design e `optimize-iceberg-table` para a manutenção), nem para ingerir dado (procedimento de carga é outro), nem para consultar tabela existente (agent `athena-query-optimizer`). Se você está prestes a rodar `aws s3tables create-table-bucket` sem checar tabelas existentes, pare — o passo 1 exige o inventário, e criar sobre nome existente é silencioso. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — cria table bucket, namespace, tabela e catalog integration S3 Tables via `aws s3tables`/`aws glue` ao vivo; a fronteira `## Nao faz` exige confirmacao do operador por comando de escrita, inalcancavel em subagente |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “como crio uma tabela Iceberg sem gerenciar compaction” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-cdc-replication`

| Campo | Valor |
|---|---|
| NAME | `review-cdc-replication` |
| PURPOSE | Use quando houver dump local de eventos CDC, Debezium/Kafka Connect, AWS DMS ou Schema Registry e for preciso revisar chaves, posições, transações, snapshot/CDC seam, deletes, tombstones, schema histo… |
| TRIGGERS | Use quando houver dump local de eventos CDC, Debezium/Kafka Connect, AWS DMS ou Schema Registry e for preciso revisar chaves, posições, transações, snapshot/CDC seam, deletes, tombstones, schema history, compatibilidade, contratos e pontos cegos sem chamar serviços externos. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai dumps CDC, Debezium/DMS e julga contratos observados; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `cdc-contract-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_analyze_cdc`, `sparkforge_aws_analyze_schema_registry`, `sparkforge_aws_next_step`, `sparkforge_aws_rules_lookup` |
| EXAMPLE | “pedido que case a descrição de `review-cdc-replication`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-data-validation`

| Campo | Valor |
|---|---|
| NAME | `review-data-validation` |
| PURPOSE | Use quando o job PySpark valida dado e a pergunta for onde a validação está, se ela tem consequência e quanto ela custa — check artesanal (`df.filter(...).count()`), `VerificationSuite` do PyDeequ ou… |
| TRIGGERS | Use quando o job PySpark valida dado e a pergunta for onde a validação está, se ela tem consequência e quanto ela custa — check artesanal (`df.filter(...).count()`), `VerificationSuite` do PyDeequ ou Great Expectations por `batch_parameters`. Use também quando a pergunta for "esse job valida alguma coisa?", "por que o job termina verde com dado ruim?", "essa suíte protege alguém?" ou "por que validar dobrou o tempo do job?", mesmo que ninguém fale em regra. Se você está prestes a ler o `.py` no olho procurando `count()`, rode `sparkforge-aws analyze data-quality` e `sparkforge-aws judge` em vez disso — o extrator decide a posição relativa ao write, a persistência do alvo e quantos checks pesam sobre o mesmo DataFrame, e o catálogo aplica as regras SF-DQ sobre o que ele achou. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa a validacao declarada no codigo e devolve achados |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `data-quality-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “esse job valida alguma coisa?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-emr-cluster`

| Campo | Valor |
|---|---|
| NAME | `review-emr-cluster` |
| PURPOSE | Use quando revisar a definição de um cluster Amazon EMR on EC2 (instance fleets contra instance groups, purchasing option por papel, managed scaling com alocação dinâmica, Configurations de cluster so… |
| TRIGGERS | Use quando revisar a definição de um cluster Amazon EMR on EC2 (instance fleets contra instance groups, purchasing option por papel, managed scaling com alocação dinâmica, Configurations de cluster sobrepostas por grupo, maximizeResourceAllocation, partitionOverwriteMode, LogUri, bootstrap actions, segredo em texto claro) em busca de contradição de dimensionamento, custo sem trabalho correspondente ou perda de capacidade de diagnóstico. Use também quando a pergunta for "por que esse cluster custa isso", "o cluster subiu e não desce", "esse cluster morreu no bootstrap" ou "cadê os logs do cluster que terminou", mesmo sem falar em regra. Em vez de ler `describe-cluster` no olho, rode `sparkforge-aws analyze emr-cluster` e `sparkforge-aws judge`: o extrator normaliza grupos e frotas num kind só e o catálogo aplica SF-EMR. Cobre também EMR Serverless: se o dump é `get-application`, o verbo é `sparkforge-aws analyze emr-serverless` e a área é SF-EMRS. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa a definicao do cluster que ja esta em disco |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `emr-infra-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “por que esse cluster custa isso” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-emr-eks`

| Campo | Valor |
|---|---|
| NAME | `review-emr-eks` |
| PURPOSE | Use quando revisar a execução de um job Amazon EMR on EKS pelo par `describe-virtual-cluster` + `describe-job-run` do `emr-containers` (segredo em texto claro nas duas superfícies de configuração, des… |
| TRIGGERS | Use quando revisar a execução de um job Amazon EMR on EKS pelo par `describe-virtual-cluster` + `describe-job-run` do `emr-containers` (segredo em texto claro nas duas superfícies de configuração, destino de log ausente, `persistentAppUI` desligado, alocação dinâmica sem `shuffleTracking` no Kubernetes). Use também quando a pergunta for "cadê os logs desse job run", "por que não tem Spark UI", "esse job rodou com qual configuração" ou "quem submeteu isso com senha na linha de submit", mesmo que ninguém fale em regra. Se você está prestes a ler `describe-job-run` no olho, rode `sparkforge-aws analyze emr-eks` e `sparkforge-aws judge` em vez disso. Esta skill NÃO julga capacidade de nó, pod pendente nem pod template — nada disso está no `emr-containers`, e supor que está é inventar. Para EMR on EC2 e EMR Serverless a skill é `review-emr-cluster`. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa o job run do emr-containers que ja esta em disco |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `emr-infra-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_analyze_emr_eks`, `sparkforge_aws_collect_emr_eks`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “cadê os logs desse job run” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-event-driven-architecture`

| Campo | Valor |
|---|---|
| NAME | `review-event-driven-architecture` |
| PURPOSE | Use quando houver dump de EventBridge, EventBridge Pipes, SQS ou SNS e for preciso revisar entrega, retry, DLQ, redrive e pontos cegos sem confundir configuração com prova de execução |
| TRIGGERS | Use quando houver dump de EventBridge, EventBridge Pipes, SQS ou SNS e for preciso revisar entrega, retry, DLQ, redrive e pontos cegos sem confundir configuração com prova de execução. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai e julga EventBridge, Pipes, SQS e SNS; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `review-event-driven-architecture`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-glue-streaming`

| Campo | Valor |
|---|---|
| NAME | `review-glue-streaming` |
| PURPOSE | Use quando houver dump JSON/JSONL de AWS Glue Streaming ou Real-Time Mode e for preciso validar runtime, restrições, capacidade observada e lacunas sem chamar AWS |
| TRIGGERS | Use quando houver dump JSON/JSONL de AWS Glue Streaming ou Real-Time Mode e for preciso validar runtime, restrições, capacidade observada e lacunas sem chamar AWS. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai dumps Glue Streaming/RTM e julga restricoes observadas; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_next_step` |
| EXAMPLE | “pedido que case a descrição de `review-glue-streaming`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-glue-terraform`

| Campo | Valor |
|---|---|
| NAME | `review-glue-terraform` |
| PURPOSE | Use quando revisar o Terraform/IaC de jobs Glue (worker type, max_capacity junto com worker_type/number_of_workers, execution class, timeout, max_concurrent_runs com bookmarks, max_retries com escrita… |
| TRIGGERS | Use quando revisar o Terraform/IaC de jobs Glue (worker type, max_capacity junto com worker_type/number_of_workers, execution class, timeout, max_concurrent_runs com bookmarks, max_retries com escrita não idempotente, default arguments, Spark UI/event logs, segredo em argumento) em busca de configuração contraditória, observabilidade ausente ou incompatível com o runtime. Use também quando a pergunta for "esse .tf tá certo", "por que a config que eu mudei no Terraform não fez efeito" ou "tem credencial exposta nesse job", mesmo que ninguém fale em regra. Se você está prestes a ler o .tf linha por linha comparando contra a doc do Glue, rode `sparkforge-aws analyze terraform` e `sparkforge-aws judge` em vez disso — o extrator lê os blocos aws_glue_job deterministicamente e o catálogo aplica as regras SF-GLUE por recurso. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa o .tf que ja esta em disco |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `glue-infra-reviewer` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “esse .tf tá certo” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-pyspark-pr`

| Campo | Valor |
|---|---|
| NAME | `review-pyspark-pr` |
| PURPOSE | Use quando revisar um Pull Request PySpark/AWS Glue e precisar classificar risco de regressão de performance, custo e escala antes de aprovar — novas actions, shuffles, joins com cardinalidade, UDFs,… |
| TRIGGERS | Use quando revisar um Pull Request PySpark/AWS Glue e precisar classificar risco de regressão de performance, custo e escala antes de aprovar — novas actions, shuffles, joins com cardinalidade, UDFs, collect, loops de DataFrame, mudança de write mode, particionamento ou operações Iceberg/Parquet introduzidas pelo diff. Use também quando pedirem "dá uma olhada nesse PR", "isso é seguro de mergear", "o que mudou de performance aqui" ou "aprova esse diff", mesmo sem falar em code review formal. Se você está prestes a ler o diff e apontar problema de cabeça, rode `sparkforge-aws analyze pyspark` nos arquivos alterados e compare contra a versão base em vez de confiar em leitura visual — e valide sua própria recomendação com `sparkforge-aws validate` antes de postar, porque um ganho quantificado sem `benchmark_ref` é rejeitado pelo schema. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa um diff fechado e classifica risco |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `data-quality-reviewer`, `pyspark-code-reviewer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “dá uma olhada nesse PR” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-streaming-operations`

| Campo | Valor |
|---|---|
| NAME | `review-streaming-operations` |
| PURPOSE | Use quando houver um contrato declarativo de streaming e for necessário revisar SLO, FinOps, segurança, serving e lakehouse sem inventar medição, preço ou eficácia operacional |
| TRIGGERS | Use quando houver um contrato declarativo de streaming e for necessário revisar SLO, FinOps, segurança, serving e lakehouse sem inventar medição, preço ou eficácia operacional. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — revisa SLO, FinOps, segurança, serving e lakehouse por contrato offline; preserva unresolved |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `review-streaming-operations`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-structured-streaming`

| Campo | Valor |
|---|---|
| NAME | `review-structured-streaming` |
| PURPOSE | Use quando houver código Structured Streaming, StreamingQueryProgress ou metadados de checkpoint e for preciso separar declaração estática, medida temporal, runtime e resultado funcional |
| TRIGGERS | Use quando houver código Structured Streaming, StreamingQueryProgress ou metadados de checkpoint e for preciso separar declaração estática, medida temporal, runtime e resultado funcional. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — extrai source/progress de Structured Streaming e julga limites observados; a saida e relatorio |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `streaming-realtime-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `review-structured-streaming`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `review-terraform-data-platform`

| Campo | Valor |
|---|---|
| NAME | `review-terraform-data-platform` |
| PURPOSE | Use quando for necessario revisar Terraform de plataformas de dados, IAM, providers, plans e drift |
| TRIGGERS | Use quando for necessario revisar Terraform de plataformas de dados, IAM, providers, plans e drift. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — Especialista de dominio; despacho por coordenador |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-lake-formation-specialist`, `sf-security-reviewer`, `sf-terraform-specialist` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `review-terraform-data-platform`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `run-debate`

| Campo | Valor |
|---|---|
| NAME | `run-debate` |
| PURPOSE | Use quando `sparkforge-aws arbitrate` devolver `debate.unresolved` com um `debate_plan` para um par de regras e o operador quiser conduzir o debate na sessão — "roda o debate entre SF-X e SF-Y", "qual… |
| TRIGGERS | Use quando `sparkforge-aws arbitrate` devolver `debate.unresolved` com um `debate_plan` para um par de regras e o operador quiser conduzir o debate na sessão — "roda o debate entre SF-X e SF-Y", "qual das duas ações fica?", "o arbitrate parou em debate, e agora?". A sessão faz o papel de cada lado, pede o brief ao executor com `sparkforge_aws_debate_next`, escreve a submissão e a entrega com `sparkforge_aws_debate_submit`, até o executor devolver `done`. O fechamento é sempre do `referee`, nunca da sessão. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — conduz o laco do debate no agente pai e despacha os lados; despachada inteira, os dois lados dividiriam um contexto e gravariam no case |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_debate_next`, `sparkforge_aws_debate_referee`, `sparkforge_aws_debate_start`, `sparkforge_aws_debate_submit` |
| EXAMPLE | “roda o debate entre SF-X e SF-Y” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-build`

| Campo | Valor |
|---|---|
| NAME | `sdd-build` |
| PURPOSE | Use quando o plan.md da feature está ready e é hora de construir — "executa o plano", "implementa a feature", "fase build" — no SparkForge (perfil dev) ou num job do operador (perfil operator, sempre… |
| TRIGGERS | Use quando o plan.md da feature está ready e é hora de construir — "executa o plano", "implementa a feature", "fase build" — no SparkForge (perfil dev) ou num job do operador (perfil operator, sempre por change sandbox). |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — despacha um subagente por tarefa e dois revisores; despachada inteira, perderia a orquestracao, porque subagente nao gera subagente por default |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_benchmark`, `sparkforge_aws_change_plan`, `sparkforge_aws_change_propose`, `sparkforge_aws_change_sandbox`, `sparkforge_aws_code_symbol`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp` |
| EXAMPLE | “executa o plano” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-define`

| Campo | Valor |
|---|---|
| NAME | `sdd-define` |
| PURPOSE | Use quando a abordagem já está escolhida, ou o pedido já é claro, e falta fixar o que significa pronto — "define os requisitos", "quais os critérios de aceite?", "fase define" — para uma mudança no Sp… |
| TRIGGERS | Use quando a abordagem já está escolhida, ou o pedido já é claro, e falta fixar o que significa pronto — "define os requisitos", "quais os critérios de aceite?", "fase define" — para uma mudança no SparkForge ou num job do operador. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — fecha criterios e hipotese com o operador, uma pergunta por vez; subagente nao pode perguntar (V-DV-10) |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_case_open`, `sparkforge_aws_funcval_plan`, `sparkforge_aws_knowledge_path`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp`, `sparkforge_aws_sdd_status` |
| EXAMPLE | “define os requisitos” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-design`

| Campo | Valor |
|---|---|
| NAME | `sdd-design` |
| PURPOSE | Use quando o define.md da feature está ready e falta decidir como construir — "desenha a solução", "quais arquivos mudam?", "como desfazer?", "fase design" — no SparkForge ou num job do operador |
| TRIGGERS | Use quando o define.md da feature está ready e falta decidir como construir — "desenha a solução", "quais arquivos mudam?", "como desfazer?", "fase design" — no SparkForge ou num job do operador. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — apresenta o desenho por partes e espera aprovacao de cada uma; subagente nao pode perguntar |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_change_plan`, `sparkforge_aws_code_path`, `sparkforge_aws_code_search`, `sparkforge_aws_code_symbol`, `sparkforge_aws_knowledge_path`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp` |
| EXAMPLE | “desenha a solução” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-explore`

| Campo | Valor |
|---|---|
| NAME | `sdd-explore` |
| PURPOSE | Use quando uma ideia ainda sem forma vai virar mudança no SparkForge ou num job Glue/PySpark do operador — "quero fazer X", "uso A ou B?", "como você atacaria isso?" — e ainda não há define, design ne… |
| TRIGGERS | Use quando uma ideia ainda sem forma vai virar mudança no SparkForge ou num job Glue/PySpark do operador — "quero fazer X", "uso A ou B?", "como você atacaria isso?" — e ainda não há define, design nem código. Requisito já claro vai direto para sdd-define. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — pergunta uma coisa por vez e espera o operador escolher a abordagem; despachada, ninguem estaria la para responder |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_case_get`, `sparkforge_aws_code_search`, `sparkforge_aws_code_symbol`, `sparkforge_aws_knowledge_path`, `sparkforge_aws_rules_lookup`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_status` |
| EXAMPLE | “quero fazer X” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-plan`

| Campo | Valor |
|---|---|
| NAME | `sdd-plan` |
| PURPOSE | Use quando o design.md da feature está ready e falta quebrar a construção em tarefas pequenas, com teste e código, que outra sessão execute sem contexto — "escreve o plano", "quebra em tarefas", "fase… |
| TRIGGERS | Use quando o design.md da feature está ready e falta quebrar a construção em tarefas pequenas, com teste e código, que outra sessão execute sem contexto — "escreve o plano", "quebra em tarefas", "fase plan". |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — o plano passa pela leitura do operador antes de ficar ready; subagente nao pode perguntar |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_code_search`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp`, `sparkforge_aws_sdd_status` |
| EXAMPLE | “escreve o plano” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sdd-ship`

| Campo | Valor |
|---|---|
| NAME | `sdd-ship` |
| PURPOSE | Use quando o build_report.md da feature está pronto e é hora de entregar — "entrega a feature", "fecha o ciclo", "fase ship", "posso abrir o PR?", "posso fazer merge?" — no SparkForge ou num job do op… |
| TRIGGERS | Use quando o build_report.md da feature está pronto e é hora de entregar — "entrega a feature", "fecha o ciclo", "fase ship", "posso abrir o PR?", "posso fazer merge?" — no SparkForge ou num job do operador. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — para antes de git push, merge e gh pr create para a escolha do operador; despachada, ninguem estaria la para escolher |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | — |
| RELATED_MCP_TOOLS | `sparkforge_aws_benchmark`, `sparkforge_aws_change_propose`, `sparkforge_aws_funcval_compare`, `sparkforge_aws_sdd_check`, `sparkforge_aws_sdd_stamp`, `sparkforge_aws_sdd_status` |
| EXAMPLE | “entrega a feature” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `spark4-compatibility`

| Campo | Valor |
|---|---|
| NAME | `spark4-compatibility` |
| PURPOSE | Use quando o código PySpark ou o `.jar` precisa rodar sob Apache Spark 4 e alguém pergunta "o que quebra no Spark 4?", "essa config mudou de nome?", "ANSI mode vai estourar meu cast?" ou "meu JAR de S… |
| TRIGGERS | Use quando o código PySpark ou o `.jar` precisa rodar sob Apache Spark 4 e alguém pergunta "o que quebra no Spark 4?", "essa config mudou de nome?", "ANSI mode vai estourar meu cast?" ou "meu JAR de Scala 2.12 funciona?". Use também quando o job falha com `NoSuchMethodError`, `ClassNotFoundException` ou uma exceção de overflow que antes devolvia NULL. Se você está prestes a comparar o código com o guia de migração do Apache no olho, rode `sparkforge-aws migrate glue dir --from 5.1 --to 6.0` e `sparkforge-aws glue dependency-audit dir --glue 6.0` — a área `SF-SPARK4` guarda cada regra pela versão de **Spark**, não de Glue, e por isso vale igual num EMR. |
| SUPPORTED_HOSTS | subagente despachável em Claude/Devin; `playbook` em Codex/Copilot — julga o codigo e os pins contra a fronteira do Spark 4 |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-runtime-specialist` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “o que quebra no Spark 4?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `sparkforge-aws-diagnose`

| Campo | Valor |
|---|---|
| NAME | `sparkforge-aws-diagnose` |
| PURPOSE | Use quando o pedido for genérico e amplo — "meu job Glue tá lento", "por que esse pipeline ficou caro", "não sei por onde começar" — e ainda não há gargalo isolado nem skill específica escolhida… |
| TRIGGERS | Use quando o pedido for genérico e amplo — "meu job Glue tá lento", "por que esse pipeline ficou caro", "não sei por onde começar" — e ainda não há gargalo isolado nem skill específica escolhida. Use também como a primeira skill de qualquer investigação nova, antes de ter event log, plano físico ou qualquer fact coletado. Esta skill não analisa: ela abre o case, coleta o que está disponível, e deixa `sparkforge-aws next-step` decidir a rota. Se você está prestes a escolher a próxima skill "pelo que parece óbvio", pare — rode `sparkforge-aws next-step` em vez disso: a árvore de decisão vive em `rules/catalog/routing.yaml`, e escolher por julgamento próprio é exatamente o que a regra 2 do AGENT_PROTOCOL.md proíbe. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — abre o case e roteia. Despachar joga o ciclo de vida do case para um contexto que nao volta -- e o case e o que faz a investigacao atravessar sessoes e ferramentas |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “meu job Glue tá lento” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `tool-specialist-routing`

| Campo | Valor |
|---|---|
| NAME | `tool-specialist-routing` |
| PURPOSE | Use quando for necessario escolher, validar ou autorizar ferramentas por especializacao, risco e contrato |
| TRIGGERS | Use quando for necessario escolher, validar ou autorizar ferramentas por especializacao, risco e contrato. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — valida roteamento no agente atual |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `sf-runtime-specialist` |
| RELATED_MCP_TOOLS | — |
| EXAMPLE | “pedido que case a descrição de `tool-specialist-routing`” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

### `tune-glue-job`

| Campo | Valor |
|---|---|
| NAME | `tune-glue-job` |
| PURPOSE | Use quando for ajustar workers, worker type, Auto Scaling, execution class ou argumentos de um job Glue depois de já ter um gargalo comprovado — não para descobri-lo… |
| TRIGGERS | Use quando for ajustar workers, worker type, Auto Scaling, execution class ou argumentos de um job Glue depois de já ter um gargalo comprovado — não para descobri-lo. Use também quando a pergunta for "aumenta os workers?", "põe mais DPU", "troca pra worker maior" ou "liga Auto Scaling", mesmo sem esse vocabulário. Se você está prestes a recomendar mais workers a partir só do código ou de instinto, rode `sparkforge-aws analyze terraform`, `sparkforge-aws collect glue-job` e `sparkforge-aws judge` em vez disso — o catálogo SF-GLUE-* aponta contradição de max_capacity com worker_type/number_of_workers, observabilidade ausente e retry sobre escrita não idempotente antes de qualquer decisão de capacidade, e a tabela de decisão em knowledge/glue/workers-and-capacity.md tem capacidade como resposta errada em metade dos casos. |
| SUPPORTED_HOSTS | host pai apenas — não-despachável — o passo 1 exige baseline ja provado por `analyze-spark-ui`, `diagnose-oom` e `diagnose-data-skew`; subagente nao herda o historico do pai e teria de reconstruir a evidencia que motivou a chamada |
| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |
| RELATED_AGENTS | `glue-incremental-performance-architect`, `glue-infra-reviewer`, `spark-performance-architect` |
| RELATED_MCP_TOOLS | `sparkforge_aws_funcval_compare`, `sparkforge_aws_funcval_plan` |
| EXAMPLE | “aumenta os workers?” |
| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |

## §11.1 — Agentic Invocation Cookbook

Prompts de intenção associados ao mecanismo real de cada host. A tarefa é a
mesma; o que muda é o mecanismo que a executa.

### Tarefa canônica

> "Analise os jobs Glue deste repositório utilizando as skills relevantes do
> Spark Forge AWS. Investigue performance, dependências e possíveis riscos,
> separe fatos de hipóteses e produza evidências verificáveis."

| Host | Como invocar |
|---|---|
| **Claude Code** | cole a tarefa na sessão; a skill `sparkforge-aws-diagnose` ativa pela descrição. Para despachar o coordenador: *"Use the spark-performance-architect profile as a subagent for this investigation."* |
| **Devin** | cole a tarefa; para o coordenador como subagente: *"Use the spark-performance-architect profile as a subagent…"* — ou comece a sessão com `Read PROMPT_INICIAL_MESTRE.md and use the spark-performance-architect skill.` |
| **Codex** | cole a tarefa; a orquestração é o `playbook` (sem despacho de subagente): `sparkforge-aws playbook spark-performance-architect --repo .` — cada passo do plano devolvido é executado na sessão. |
| **Copilot / outros leitores de `AGENTS.md`** | cole a tarefa e aponte o `playbook` como procedimento; as skills ficam em `.agents/skills/`. |
