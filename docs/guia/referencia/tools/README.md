<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# Referência das tools MCP

Uma página por tool, agrupadas pela primeira palavra do nome. O efeito diz se a tool só lê, grava em disco local ou acessa a AWS.

## analyze

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_analyze_athena_workgroup`](sparkforge_analyze_athena_workgroup.md) | só leitura | Extrai facts de um dump JSON de workgroups do Athena (`get_work_group`): engine version efetiva, state, bytes_scanned_cutoff. |
| [`sparkforge_analyze_call_graph`](sparkforge_analyze_call_graph.md) | só leitura | Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts JA extraidos (tipicamente `sparkforge_analyze_pyspark` gravado em disco via `--out`) -- funcao pura sobre... |
| [`sparkforge_analyze_catalog_schema`](sparkforge_analyze_catalog_schema.md) | só leitura | Extrai facts de um dump JSON ja coletado do Glue Data Catalog (`GetTables`/`GetTable`): schema, colunas, chaves de particao, contagem de particoes e table properties. |
| [`sparkforge_analyze_cloudwatch`](sparkforge_analyze_cloudwatch.md) | só leitura | Extrai facts `glue.metric` de um artefato de metricas do CloudWatch ja coletado. |
| [`sparkforge_analyze_cloudwatch_logs`](sparkforge_analyze_cloudwatch_logs.md) | só leitura | Extrai facts do LOG do run ja coletado por `collect cloudwatch-logs`. |
| [`sparkforge_analyze_consumers`](sparkforge_analyze_consumers.md) | só leitura | Extrai facts do inventario DECLARADO de consumidores de tabela (`.sparkforge/consumers.yaml`, versionado com o repositorio). |
| [`sparkforge_analyze_controlm_jobs`](sparkforge_analyze_controlm_jobs.md) | só leitura | Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC) -- o JSON de definicao de job versionado no repositorio, o mesmo que `ctm build` valida e `ctm deploy` publica. |
| [`sparkforge_analyze_data_quality`](sparkforge_analyze_data_quality.md) | só leitura | Extrai facts de VALIDACAO DE DADO do proprio codigo PySpark (`.py` do repositorio, nunca API da AWS): onde cada check roda, o que ele custa e se ele tem consequencia. |
| [`sparkforge_analyze_emr_cluster`](sparkforge_analyze_emr_cluster.md) | só leitura | Extrai facts de um dump JSON de cluster EMR on EC2 (`describe-cluster` mais `list-instance-groups`/`list-instance-fleets`/`list-bootstrap-actions`/`get-managed-scaling-policy`/`... |
| [`sparkforge_analyze_emr_eks`](sparkforge_analyze_emr_eks.md) | só leitura | Extrai facts de um dump JSON de execucao Amazon EMR on EKS (`describe-virtual-cluster` mais `describe-job-run`, as DUAS respostas no mesmo arquivo sob `virtualCluster` e `jobRun... |
| [`sparkforge_analyze_emr_serverless`](sparkforge_analyze_emr_serverless.md) | só leitura | Extrai facts de um dump JSON de application Amazon EMR Serverless (`get-application`): release, estado, arquitetura, capacidade pre-inicializada por worker type (`emrs.initial_c... |
| [`sparkforge_analyze_error_signatures`](sparkforge_analyze_error_signatures.md) | só leitura | Casa as assinaturas de `knowledge/errors/` contra os facts do case e emite `error.signature_match` com `matched_on` (`exception_class`, `caused_by` ou `log_line`). |
| [`sparkforge_analyze_event_log`](sparkforge_analyze_event_log.md) | só leitura | Extrai facts de um Spark event log (.jsonl) ja coletado: duracao/skew de task por stage, spill, GC, contagem de tasks, cores do cluster, executor perdido. |
| [`sparkforge_analyze_glue_job_runs`](sparkforge_analyze_glue_job_runs.md) | só leitura | Extrai facts de historico do DIRETORIO de artefatos de run Glue: um `glue.job_run` por run, `glue.job_run.distribution` por capacidade e estado terminal, e `glue.job_run.outcome... |
| [`sparkforge_analyze_glue_resource_link`](sparkforge_analyze_glue_resource_link.md) | só leitura | Extrai a TOPOLOGIA do catalogo ja coletada por `collect glue-resource-link`: o objeto na conta consumidora e resource link ou tabela comum, para onde ele aponta, e se o nome bat... |
| [`sparkforge_analyze_graph`](sparkforge_analyze_graph.md) | só leitura | Extrai facts de PROCESSAMENTO DE GRAFO com GraphFrames do proprio codigo PySpark (`.py` do repositorio, nunca API da AWS). |
| [`sparkforge_analyze_iam_access`](sparkforge_analyze_iam_access.md) | só leitura | Extrai a DECISAO de IAM ja simulada por `collect iam-access`, com a CAMADA que decidiu. |
| [`sparkforge_analyze_iceberg`](sparkforge_analyze_iceberg.md) | só leitura | Extrai facts de um dump JSON das cinco metadata tables Iceberg (`.files`, `.delete_files`, `.snapshots`, `.manifests`, `.partitions`): small files, delete files, cadencia de sna... |
| [`sparkforge_analyze_lakeformation_grants`](sparkforge_analyze_lakeformation_grants.md) | só leitura | Extrai a PERMISSAO do Lake Formation ja coletada por `collect lakeformation`: grant por principal, registro da localizacao S3, e o data lake settings da conta. |
| [`sparkforge_analyze_parquet_footer`](sparkforge_analyze_parquet_footer.md) | só leitura | Extrai facts do FOOTER de arquivos Parquet ja coletado por `collect parquet-footer`: row group, estatistica por coluna, dicionario, page index, bloom filter e codec. |
| [`sparkforge_analyze_plan`](sparkforge_analyze_plan.md) | só leitura | Extrai facts do TEXTO de um plano fisico ja salvo em disco: a saida de `df.explain("formatted")`, `df.explain()`, `df.explain(True)` ou `EXPLAIN [FORMATTED]`. |
| [`sparkforge_analyze_pyspark`](sparkforge_analyze_pyspark.md) | só leitura | Extrai facts deterministicos de codigo PySpark via AST estatico -- nunca importa nem executa o codigo analisado. |
| [`sparkforge_analyze_s3_listing`](sparkforge_analyze_s3_listing.md) | só leitura | Extrai facts de um dump de `aws s3api list-objects-v2`: contagem, media, p95 e maximo de bytes por prefixo, agrupados por (formato, compressao). |
| [`sparkforge_analyze_sql`](sparkforge_analyze_sql.md) | só leitura | Extrai facts de texto SQL por regex/varredura de token (nunca uma gramatica SQL completa): projecao (`SELECT *` vs. |
| [`sparkforge_analyze_sql_metrics`](sparkforge_analyze_sql_metrics.md) | só leitura | Extrai metrica por NO DO PLANO de um Spark event log ja coletado: quantos bytes e quantos arquivos cada fonte custou, medidos pelo proprio Spark. |
| [`sparkforge_analyze_terraform`](sparkforge_analyze_terraform.md) | só leitura | Extrai facts de blocos `resource "aws_glue_job"` em HCL Terraform: glue_version, worker_type, number_of_workers, default_arguments, observabilidade do Spark UI. |
| [`sparkforge_analyze_terraform_diff`](sparkforge_analyze_terraform_diff.md) | só leitura | Compara dois estados de um modulo Terraform (dois checkouts, dois `git worktree`, o main e o branch do PR) e devolve os facts do lado DEPOIS, com `attrs.changed` e `attrs.previo... |

## arbitrate

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_arbitrate`](sparkforge_arbitrate.md) | muda estado local | Executor agentico DETERMINISTICO. |

## benchmark

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_benchmark`](sparkforge_benchmark.md) | só leitura | Compara DUAS execucoes a partir dos facts de event log de cada uma (`sparkforge_analyze_event_log` gravado em disco), e emite `bench.run_delta`, `bench.stage_delta`, `bench.unma... |

## capacity

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_capacity`](sparkforge_capacity.md) | só leitura | Escolhe, entre as capacidades que o job JA RODOU, a mais BARATA que cumpre o SLA -- nunca a mais rapida. |

## case

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_case_get`](sparkforge_case_get.md) | só leitura | Le o estado atual do case (.sparkforge/case.yaml): fase, gates, runtime detectado, indices de facts e findings. |
| [`sparkforge_case_open`](sparkforge_case_open.md) | grava local | Cria um case novo em .sparkforge/case.yaml, detectando o runtime Glue/EMR/Spark/Python/Iceberg a partir dos parametros informados. |
| [`sparkforge_case_update`](sparkforge_case_update.md) | muda estado local | Atualiza a fase, um gate booleano, ou registra o uso de uma skill no case atual. |

## code

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_code_context`](sparkforge_code_context.md) | grava local | A tool PRINCIPAL do Code Intelligence: monta o ContextPack de uma tarefa a partir do indice local do repositorio -- pontos de entrada, simbolos ranqueados, relacoes do grafo, re... |
| [`sparkforge_code_export`](sparkforge_code_export.md) | grava local | Exporta o grafo de codigo no formato de EXTRACAO que a fonte do Graphify publica -- `id`/`label`/`source_file`/`source_location` nos nos, `source`/`target`/`relation`/`confidenc... |
| [`sparkforge_code_path`](sparkforge_code_path.md) | grava local | O caminho MAIS CURTO de chamadas de um simbolo ate outro, descendo pelas chamadas. |
| [`sparkforge_code_read`](sparkforge_code_read.md) | grava local | Le um trecho do repositorio analisado, por `node_id` ou por `file` + `start_line` + `end_line` -- uma das duas formas, nunca as duas nem nenhuma. |
| [`sparkforge_code_search`](sparkforge_code_search.md) | grava local | Busca simbolo por parte do nome no indice local e devolve `node_id`, caminho e linha -- o suficiente para ir ao codigo sem que o indice guarde codigo. |
| [`sparkforge_code_shape`](sparkforge_code_shape.md) | grava local | A FORMA do grafo de codigo: comunidades (grupos que se chamam mais entre si) e os nos de maior grau. |
| [`sparkforge_code_status`](sparkforge_code_status.md) | grava local | O estado do indice local e NENHUM fonte: se existe, se esta fresco em relacao a arvore, contagem de arquivos/simbolos/arestas/nao-resolvidas, versao de schema, worktree e tamanh... |
| [`sparkforge_code_symbol`](sparkforge_code_symbol.md) | grava local | Tudo que o indice sabe sobre UM simbolo: metadado, assinatura normalizada, quem o chama, quem ele chama, e o raio de impacto ate `depth` saltos acima. |
| [`sparkforge_code_sync`](sparkforge_code_sync.md) | grava local | A UNICA tool de mutacao do Code Intelligence: poe o indice local em dia com a arvore. |

## collect

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_collect_athena_workgroup`](sparkforge_collect_athena_workgroup.md) | acessa a AWS | Baixa a configuracao de um workgroup via `athena.get_work_group` (engine version efetiva/selecionada, state, bytes_scanned_cutoff, output_location) e registra no manifesto, ja n... |
| [`sparkforge_collect_cloudwatch`](sparkforge_collect_cloudwatch.md) | acessa a AWS | Baixa as metricas de observabilidade Glue via `cloudwatch.get_metric_data` (skewness, uso de heap, bytes/records lidos e escritos, sucesso/erro) e registra no manifesto. |
| [`sparkforge_collect_cloudwatch_logs`](sparkforge_collect_cloudwatch_logs.md) | acessa a AWS | Baixa o LOG do run no CloudWatch Logs via `logs.filter_log_events` e registra no manifesto. |
| [`sparkforge_collect_emr_cluster`](sparkforge_collect_emr_cluster.md) | acessa a AWS | Baixa os seis dumps de um cluster EMR on EC2 (`describe_cluster`, grupos OU fleets, bootstrap actions, managed scaling e auto termination) e registra a uniao deles no manifesto,... |
| [`sparkforge_collect_emr_eks`](sparkforge_collect_emr_eks.md) | acessa a AWS | Baixa `describe-virtual-cluster` e `describe-job-run` de uma execucao Amazon EMR on EKS e grava as DUAS respostas num unico arquivo autocontido, sob as chaves de topo `virtualCl... |
| [`sparkforge_collect_emr_serverless`](sparkforge_collect_emr_serverless.md) | acessa a AWS | Baixa `get-application` de uma application Amazon EMR Serverless e registra a resposta no manifesto, no mesmo shape camelCase que `aws emr-serverless get-application` devolve --... |
| [`sparkforge_collect_event_log`](sparkforge_collect_event_log.md) | acessa a AWS | Baixa o Spark event log de um job run via `s3.list_objects_v2`/`get_object` e registra no manifesto (`.sparkforge/artifacts/manifest.json`). |
| [`sparkforge_collect_glue_job`](sparkforge_collect_glue_job.md) | acessa a AWS | Baixa a definicao de um job via `glue.get_job` e registra no manifesto. |
| [`sparkforge_collect_glue_job_runs`](sparkforge_collect_glue_job_runs.md) | acessa a AWS | Baixa o historico de execucoes de um job via `glue.get_job_runs` e grava UM artefato por run em estado terminal. |
| [`sparkforge_collect_glue_resource_link`](sparkforge_collect_glue_resource_link.md) | acessa a AWS | Le o objeto que o job consulta na conta CONSUMIDORA via `glue:GetTable` (ou `glue:GetDatabase` sem `table`) e, por default, o recurso de ORIGEM que o link declara. |
| [`sparkforge_collect_iam_access`](sparkforge_collect_iam_access.md) | acessa a AWS | Simula acoes contra um role via `iam:SimulatePrincipalPolicy` e grava a DECISAO da AWS. |
| [`sparkforge_collect_iceberg_metadata`](sparkforge_collect_iceberg_metadata.md) | acessa a AWS | Consulta as cinco metadata tables Iceberg de uma tabela via Athena (`SELECT * FROM "db"."tabela$secao"`) e registra no manifesto. |
| [`sparkforge_collect_lakeformation`](sparkforge_collect_lakeformation.md) | acessa a AWS | Coleta a PERMISSAO de UMA tabela no Lake Formation: `list_permissions` (quem tem o que), `describe_resource` (a localizacao S3 esta registrada, e com qual role) e `get_data_lake... |
| [`sparkforge_collect_verify`](sparkforge_collect_verify.md) | só leitura | Verifica presenca e integridade (sha256 recalculado) de todos os artefatos registrados no manifesto local. |

## controlm

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_controlm_describe`](sparkforge_controlm_describe.md) | só leitura | O que vale numa versao do Control-M AUTOMATION API: quais capacidades existem, quais ja foram depreciadas, e quais exigencias de componente estao em vigor. |

## debate

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_debate_next`](sparkforge_debate_next.md) | grava local | O proximo passo do debate, derivado SO dos arquivos do case: o brief do lado da vez (`status: brief`) ou o fechamento (`status: done`). |
| [`sparkforge_debate_referee`](sparkforge_debate_referee.md) | só leitura | Arbitra o PROTOCOLO de debate do case e diz se o fechamento declarado pode ser publicado. |
| [`sparkforge_debate_start`](sparkforge_debate_start.md) | grava local | Abre o debate que `sparkforge_arbitrate` deixou em `debate.unresolved`: recalcula os planos pelo MESMO caminho do `arbitrate`, sobre os MESMOS insumos (findings, a UNIAO dos fac... |
| [`sparkforge_debate_submit`](sparkforge_debate_submit.md) | muda estado local | Submete o turno do lado da vez, INLINE em `submission`, no schema que o brief publica. |

## doctor

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_doctor`](sparkforge_doctor.md) | só leitura | Confere se o ambiente esta pronto, em nove checagens com status ok, warn, fail ou skip e o comando que resolve: pacote, extras, mcp, catalogo, packs, knowledge, indice_de_codigo... |

## economy

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_economy_report`](sparkforge_economy_report.md) | só leitura | O que a execucao poe na janela de contexto: bytes MEDIDOS por tool, o efeito medido do `detail_level`, o peso do catalogo em repouso e -- quando houver transcript do host -- o t... |

## finops

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_finops`](sparkforge_finops.md) | só leitura | O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta -- capacidade ou codigo. |

## funcval

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_funcval_compare`](sparkforge_funcval_compare.md) | grava local | Compara os DOIS resultados que VOCE mediu contra o plano de `sparkforge_funcval_plan`, e emite `funcval.check_delta`, a sentinela `funcval.analyzed` e `funcval.unresolved`. |
| [`sparkforge_funcval_plan`](sparkforge_funcval_plan.md) | grava local | Deriva O QUE MEDIR nos dois lados de uma mudanca, a partir de facts JA extraidos (`sparkforge_analyze_pyspark` e `sparkforge_analyze_catalog_schema` gravados em disco), e GRAVA... |

## fuse

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_fuse`](sparkforge_fuse.md) | só leitura | Correlaciona facts de fontes diferentes (texto SQL de `sparkforge_analyze_sql` com schema de `sparkforge_analyze_catalog_schema`) pelo nome da tabela, e produz facts `.enriched`... |

## gain

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_gain`](sparkforge_gain.md) | só leitura | Realized Gain Ledger: o ganho OBSERVADO entre runs ja medidos de um job Glue antes (`baseline_paths`) e depois (`candidate_paths`) de uma mudanca. |

## glue

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_glue_dependency_audit`](sparkforge_glue_dependency_audit.md) | só leitura | Lista as dependencias DECLARADAS de um job Glue -- pin de `requirements*.txt` (`mig.python_dep`, com `major` ja separado) e binario `.jar` (`mig.jar_binary`, com `scala_minor` j... |

## iceberg

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_iceberg_assess_upgrade`](sparkforge_iceberg_assess_upgrade.md) | só leitura | Avalia subir o format version de uma tabela Iceberg CONTRA quem a consome. |

## judge

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_judge`](sparkforge_judge.md) | só leitura | Aplica o catalogo de regras versionado sobre facts ja extraidos, filtrado pelo runtime -- que sai dos PROPRIOS facts quando eles o carregam (`tf.attribute` glue_version, `spark.... |

## knowledge

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_knowledge_drift`](sparkforge_knowledge_drift.md) | só leitura | Knowledge Drift Radar: para cada fonte oficial vigiada cujo hash mudou (`changed_at` em knowledge/sources.lock.json), o que ela arrasta. |
| [`sparkforge_knowledge_path`](sparkforge_knowledge_path.md) | só leitura | Resolve a raiz dos arquivos de conhecimento versionado e, opcionalmente, um arquivo dentro dela. |

## lakeformation

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_lakeformation_access_graph`](sparkforge_lakeformation_access_graph.md) | só leitura | O caminho de acesso a uma tabela governada como GRAFO, derivado de facts -- concessao do Lake Formation, decisao SIMULADA do IAM (com a camada que negou) e registro da localizac... |
| [`sparkforge_lakeformation_matrix`](sparkforge_lakeformation_matrix.md) | só leitura | Eixo de VERSAO de Lake Formation por runtime Glue: filesystem S3 default, FGAC por caminho (GlueContext contra Spark-native, leitura contra escrita), DDL/DML e Full Table Access... |

## migration

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_migration_assess`](sparkforge_migration_assess.md) | só leitura | Julga a migracao de um job entre um par de versoes com o catalogo versionado (`SF-MIG`, `SF-SPARK4`, `SF-LF`), uma vez por DEGRAU do caminho -- 4.0 para 6.0 passa por 5.0 e 5.1,... |

## next

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_next_step`](sparkforge_next_step.md) | só leitura | Decide o proximo passo (skill recomendada) a partir de routing.yaml -- o mesmo motor declarativo de sparkforge.rules.engine, mas sobre o estado do case e os achados atuais, nunc... |

## pack

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_pack_list`](sparkforge_pack_list.md) | só leitura | Forge Packs ativos: pacotes de DADO (regras YAML, knowledge e fixtures) de terceiro, carregados junto do core pela variavel SPARKFORGE_PACKS. |

## playbook

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_playbook`](sparkforge_playbook.md) | só leitura | Decomposicao de um coordenador (agents/*.md) em passos sequenciais -- o PISO de orquestracao das cinco plataformas. |

## proof

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_proof`](sparkforge_proof.md) | só leitura | Change Proof: para cada recomendacao APLICADA (`applied`: RULE_ID ou RULE_ID:simbolo), as obrigacoes de prova e o desfecho de cada uma. |

## receipt

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_receipt_emit`](sparkforge_receipt_emit.md) | grava local | Grava o RECIBO de uma execucao do case em `<repo>/.sparkforge/receipts/<receipt_id>.json`: caminho relativo e sha256 do `case.yaml`, de cada arquivo de facts (a UNIAO do case, o... |
| [`sparkforge_receipt_verify`](sparkforge_receipt_verify.md) | só leitura | Confere um recibo de execucao e diz QUAL parte divergiu -- `version`, `integrity`, `case`, `evidence`, `judgment`, `decision`, `proof`, `tools`, `host` --, em vez de devolver so... |

## release

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_release_describe`](sparkforge_release_describe.md) | só leitura | O que uma release E, segundo a fonte DAQUELA plataforma e so ela: cada componente com versao, as fontes e a data de leitura. |
| [`sparkforge_release_diff`](sparkforge_release_diff.md) | só leitura | O que muda de COMPONENTE entre duas releases, cada lado dado por um par (plataforma, release). |

## report

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_report_github`](sparkforge_report_github.md) | só leitura | Projeta findings JA JULGADOS para o GitHub, sem ler artefato e sem rede: `sarif` (SARIF 2.1.0 para o Code Scanning), `summary_markdown` (para o `$GITHUB_STEP_SUMMARY` do PR) e `... |
| [`sparkforge_report_sign`](sparkforge_report_sign.md) | grava local | Escreve, no fim do relatorio, o bloco que prova CORRESPONDENCIA entre o texto, a evidencia e o catalogo que o produziram -- nunca autoria: nao ha chave e nao ha segredo, e qualq... |
| [`sparkforge_report_verify`](sparkforge_report_verify.md) | só leitura | Confere a assinatura de um relatorio e diz QUAL das tres partes divergiu -- evidencia, catalogo ou corpo --, em vez de devolver apenas 'invalido'. |

## resume

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_resume`](sparkforge_resume.md) | só leitura | Monta o payload de rehidratacao de um case: onde parou, runtime, baseline, achados principais, hipoteses abertas, gates, artefatos ausentes e proximo passo. |

## root

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_root_cause`](sparkforge_root_cause.md) | só leitura | Ordena os achados de `judge` por consequencia DECLARADA e nomeia a LACUNA. |

## rules

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_rules_lookup`](sparkforge_rules_lookup.md) | só leitura | Consulta o catalogo de regras determinístico por id ou categoria, devolvendo threshold, runtime_scope e fontes completas. |

## runtime

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_runtime_detect`](sparkforge_runtime_detect.md) | só leitura | Deriva glue/emr/spark/python/iceberg/athena dos facts ja extraidos e dos parametros informados, usando as matrizes oficiais de compatibilidade do Glue e do EMR. |

## scan

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_scan`](sparkforge_scan.md) | grava local | Roda sozinho os analyzes que cabem num repositorio e julga a uniao. |

## simulate

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_simulate`](sparkforge_simulate.md) | só leitura | Simulate: o que uma mudanca de configuracao move, ESTRUTURALMENTE. |

## telemetry

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_telemetry_export`](sparkforge_telemetry_export.md) | só leitura | Os spans de tool que o SparkForge mediu num run (`run_id`, o mesmo de `economy report`) e, com `host_transcript_path`, o transcript do host, em OTLP/JSON (`traces` = TracesData,... |

## tune

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_tune`](sparkforge_tune.md) | só leitura | Configuracao Spark DERIVADA da medida, com a procedencia de cada propriedade. |

## validate

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_validate_output`](sparkforge_validate_output.md) | só leitura | Valida um finding proposto contra o JSON Schema e contra a regra de ganho sem benchmark_ref antes de aceita-lo. |

## workload

| Tool | Efeito | O que faz |
|---|---|---|
| [`sparkforge_workload`](sparkforge_workload.md) | só leitura | Perfil de workload por eixos independentes -- scan, shuffle, memoria, skew, arquivos, join, SLA e classe de entrada -- a partir de facts JA extraidos. |
