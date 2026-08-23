# MIGRATIONS-GLUE-GAP — o que já existe contra o que o prompt de migrações Glue pediria

O prompt de migrações Glue propõe uma *Engineering & Migration Factory*: uma equipe de agentes
especializados, um fluxo operacional de fases numeradas, um harness de testes com artefatos
nomeados, uma biblioteca de erros com schema próprio e um contrato de saída do orquestrador.
Sua §2 é taxativa na mesma direção dos dois prompts anteriores: não inventar funcionalidade,
não concluir sem evidência, não otimizar sem medir, separar fato documentado de inferência.

Este documento existe entre a exigência e o repositório. Ele responde, componente a
componente, uma única pergunta antes de qualquer módulo novo: **isso já existe aqui,
possivelmente sob outro nome?** É o mesmo gênero de [`CURRENT-HARNESS-GAP.md`](CURRENT-HARNESS-GAP.md)
e [`GLUE6-GAP.md`](GLUE6-GAP.md), aplicado a um terceiro prompt, e segue as mesmas regras de
classificação. O prompt de migrações Glue não é versionado neste repositório, e assim
permanece: o repositório tem remote público, e material de referência não entra nele.

## Como classificar

- **EXISTE, com teste** — nomeio o módulo e o arquivo de teste que exercita o comportamento.
- **EXISTE, sem teste** — nomeio o módulo; nada prova o comportamento.
- **EXISTE PARCIAL** — nomeio o que está lá e o que falta, especificamente.
- **NÃO EXISTE** — digo isso.

Nenhuma linha diz "existe" sem caminho. Nenhuma diz "testado" sem nome de arquivo de teste.

Achado central da leitura: **este prompt é, em larga medida, uma releitura do que as fases
`SF-MIG` e H1–H6 já entregaram** — matriz de runtime como dado com procedência, caminho por
degraus, extrator de facts de migração, gates fail-closed com `missing_evidence`, biblioteca
de erros com fonte e data, e recomendação em vocabulário fechado. O que ele acrescenta se
concentra em poucas frentes, e só uma delas é domínio novo: **conector e JDBC**, que não tem
fact, regra, conhecimento nem agent. As demais são vocabulário — um estado de gate a mais e um
vocabulário de decisão diferente — e a seção final explica por que nenhuma delas deve entrar.

---

## 1. Matriz de versões e caminho de migração (§4, §6.2)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Matriz de runtime como dado, com fonte e data por versão | EXISTE, com teste | `knowledge/glue/runtime-matrix.yaml` carregado por `sparkforge/facts/runtime_matrix.py`; cada componente carrega `source`, `source_type` e `retrieved`, e a carga recusa afirmação sem evidência | `tests/test_runtime_matrix.py` |
| Faixa de versões de Glue coberta pela matriz | EXISTE PARCIAL | A matriz vai de `3.0` a `6.0`. As versões anteriores que a §4 enumera não estão nela, e a decisão não é acidental: são runtimes fora de suporte, sem página de migração viva para citar como fonte, e a regra da matriz é que célula sem fonte não entra | `tests/test_runtime_glue_versions.py` |
| Eixos da matriz além de Spark, Python, Scala e Java | EXISTE PARCIAL | A forma longa resolve Spark, Python, Scala, Java e Iceberg. A §4 pede também status de suporte, EOS/EOL, disponibilidade regional, Hadoop, Boto3, AWS SDK Java, Arrow, Pandas, NumPy, Parquet, JDBC e conectores — nenhum deles existe como campo | `tests/test_runtime_matrix.py` |
| Hudi e Delta Lake como eixo de compatibilidade | EXISTE PARCIAL | Existem como coluna em `knowledge/glue/runtime-matrix.md`, e o próprio documento marca as células como **a verificar** — não foram confirmadas contra fonte oficial. Não existem no dado carregado, não têm fact, não têm regra e não estão na matriz de suporte por engine | `tests/test_runtime_glue_versions.py` |
| Expansão do caminho origem-alvo em degraus | EXISTE, com teste | `sparkforge/migration/version_path.py:steps()` deriva os degraus da ordem da matriz, sem par de versão escrito no código — é o caminho cumulativo que a §6.2 exige | `tests/test_version_path.py` |
| Análise cumulativa distinta do salto direto | EXISTE, com teste | `sparkforge/migration/assessment.py:assess()` julga uma vez por degrau e agrega em `by_step`; `report()` colapsa o achado repetido e guarda em quais degraus ele vale. As duas visões respondem perguntas diferentes | `tests/test_migration_assessment.py` |

## 2. Equipe de agentes especializados (§6)

O prompt manda **criar** uma equipe de agentes nomeados. A tabela mapeia nome a nome contra
`agents/`. Limite declarado, e vale para toda linha desta seção: o teste citado prova que o
agent existe, declara nome, descrição e ferramentas, e está espelhado byte a byte em
`.agents/`, `.claude/` e `.github/` — **não** prova competência de migração. Competência mora nas regras,
nos facts e nas skills que o agent chama, e é lá que as outras seções deste documento medem.

| Agente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| `glue-migration-chief` | EXISTE, com teste | `agents/sf-orchestrator.md` coordena agents em fases limitadas, com roteamento, handoff e critério de parada — é o papel da §6.1 sob outro nome | `tests/test_agents_parity.py` |
| `glue-version-historian` | EXISTE, com teste | `agents/sf-runtime-specialist.md` declara compatibilidade entre versões numa migração, e carrega as skills `migrate-glue-6` e `spark4-compatibility` | `tests/test_agents_parity.py` |
| `spark-runtime-migration-specialist` | EXISTE PARCIAL | `agents/sf-pyspark-specialist.md` cobre plano, join, skew e memória; a fronteira de versão do Spark está em `agents/sf-runtime-specialist.md`. O recorte da §6.3 está repartido entre os dois, e nenhum dos dois é dono dele | `tests/test_agents_parity.py` |
| `python-dependency-specialist` | NÃO EXISTE | Não há agent. O comando existe (`sparkforge glue dependency-audit`), e é ele que julga pin de dependência contra o runtime alvo | — |
| `scala-java-jars-specialist` | NÃO EXISTE | Não há agent. O mesmo comando lê `mig.jar_binary` e julga o sufixo de Scala pelo catálogo | — |
| `s3-filesystem-specialist` | EXISTE, com teste | `agents/sf-s3-specialist.md`, com áreas de regra `SF-S3`, `SF-LAKE` e `SF-SECURITY` declaradas no próprio perfil | `tests/test_agents_parity.py` |
| `open-table-format-specialist` | EXISTE, com teste | `agents/sf-storage-specialist.md` e `agents/sf-iceberg-specialist.md`. A ressalva da §6.7 — não promover formato sem olhar consumidor — já é gate, não conselho | `tests/test_agents_parity.py` |
| `lake-formation-cross-account-specialist` | EXISTE, com teste | `agents/sf-lake-formation-specialist.md` | `tests/test_agents_parity.py` |
| `data-quality-reconciliation-specialist` | EXISTE, com teste | `agents/data-quality-reviewer.md` e `agents/sf-functional-rules-specialist.md` | `tests/test_agents_parity.py` |
| `performance-scale-specialist` | EXISTE, com teste | `agents/spark-performance-architect.md` e `agents/glue-incremental-performance-architect.md` | `tests/test_agents_parity.py` |
| `streaming-cdc-specialist` | EXISTE PARCIAL | `agents/sf-kinesis-specialist.md` cobre Kinesis e streaming. CDC, Debezium, replay, poison message e DLQ não aparecem no perfil nem em regra nenhuma | `tests/test_agents_parity.py` |
| `connector-jdbc-specialist` | NÃO EXISTE | Não há agent, e também não há regra, fact ou conhecimento por baixo que um agent pudesse consultar. Ver a seção de conector e JDBC | — |
| `security-compliance-specialist` | EXISTE, com teste | `agents/sf-security-reviewer.md`, sobre IAM, KMS, S3 e exfiltração | `tests/test_agents_parity.py` |
| `observability-finops-specialist` | EXISTE PARCIAL | `agents/sf-cost-reviewer.md` cobre custo e `agents/glue-infra-reviewer.md` cobre observabilidade — o papel único da §6.14 está partido em dois, e nenhum deles conhece SLA, SLO, RTO ou RPO | `tests/test_agents_parity.py` |
| `test-harness-specialist` | EXISTE PARCIAL | `agents/sf-evidence-verifier.md` e `agents/sf-agent-evaluation-specialist.md` existem, mas o segundo avalia **agents**, não migração. O harness de validação de migração que a §6.15 descreve é a suíte de goldens do repositório, que não tem dono nomeado | `tests/test_agents_parity.py` |
| `incident-troubleshooting-specialist` | EXISTE PARCIAL | O mecanismo existe sem agent: `sparkforge/errors/matcher.py:DeterministicErrorMatcher` casa texto de erro contra `knowledge/errors/` e devolve causa provável, passo de diagnóstico e correção. Falta o papel que classifica erro novo e escreve runbook | `tests/test_error_matcher.py` |

## 3. Pontos críticos da migração (§8)

| Ponto pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| ANSI mode (§8.1) | EXISTE, com teste | `mig.ansi_risk` observa `cast` sem guarda em `sparkforge/facts/migration.py`, e `SF-MIG-003` (`rules/catalog/glue-migration.yaml`) julga só a partir do runtime em que o ANSI vem ligado. A recusa da §8.1 — não desligar ANSI automaticamente — está no `proposed_change` da regra, não numa instrução solta | `tests/test_facts_migration.py` |
| Datas, timestamps e timezone (§8.2) | EXISTE PARCIAL | `SF-SPARK4-001` acusa a configuração de rebase de data e hora que perdeu o prefixo `legacy` e ficou inerte, e `knowledge/spark/spark4-migration.md` registra a virada de `spark.sql.legacy.timeParserPolicy` como mudança sem sinal no código. Nada observa timezone de sessão, calendário, precisão ou timestamp NTZ contra LTZ — não há fact para nenhum dos quatro | `tests/test_spark4_rules.py` |
| EMRFS para S3A (§8.3) | EXISTE, com teste | `mig.emrfs_config` observa a chave exclusiva do EMRFS e `SF-MIG-002` a julga como configuração que sobrevive inerte no runtime novo — o modo de falha é silêncio, e a regra diz isso | `tests/test_facts_migration.py` |
| AWS SDK v1 para v2 (§6.5, §8.4) | EXISTE, com teste | `mig.sdk_import` observa import `com.amazonaws.*` e `SF-MIG-001` julga a sobrevivência dele em runtime que não carrega mais o SDK antigo | `tests/test_facts_migration.py` |
| Java e Scala, recompilação de JAR (§8.4) | EXISTE, com teste | `mig.jar_binary` deriva a versão de Scala do sufixo do artefato e `SF-SPARK4-004` julga quem estiver abaixo da fronteira binária sob o Spark novo; `sparkforge glue dependency-audit` é a porta de entrada, com `--glue` obrigatório | `tests/test_cli_h4.py` |
| Python (§8.5) | EXISTE PARCIAL | `mig.python_dep` observa dependência declarada e `SF-SPARK4-003` julga pin de PyArrow abaixo do piso do Spark. Wheel binária, extensão nativa em C, risco de ABI, lockfile e SBOM continuam sem fact e sem regra | `tests/test_spark4_rules.py` |
| APIs de Spark removidas ou alteradas (§8.6) | EXISTE PARCIAL | `mig.removed_api` e `mig.deprecated_api` cobrem o vocabulário fechado de símbolo que o extrator conhece, e `SF-SPARK4-002` julga chamada de pandas-on-Spark removida. `SQLContext`, RDD, serializer, listener, extensão e data source customizado não estão no vocabulário | `tests/test_facts_migration.py` |
| Lake Formation (§8.7) | EXISTE PARCIAL | `knowledge/glue/lakeformation-fgac.md` registra o que a AWS declara sobre FGAC, e a área `SF-LF` julga incompatibilidade declarada sobre `tf.attribute`. A distinção que a §8.7 exige — DynamicFrame contra DataFrame sob FGAC — não tem fact: nada no repositório observa uso de DynamicFrame no código do job | `tests/test_lakeformation_rules.py` |
| Iceberg, Hudi e Delta (§8.8) | EXISTE PARCIAL | `mig.table_format` separa versão de formato de versão de biblioteca, que é exatamente a confusão que a §8.8 proíbe, e `knowledge/storage/iceberg-feature-support.yaml` cruza feature com engine célula a célula. Hudi e Delta não têm fact, regra nem célula | `tests/test_facts_migration.py` |
| Bookmark como risco de migração (§13) | EXISTE, com teste | `SF-GLUE-003` (`rules/catalog/glue-infra.yaml`) acusa bookmark ligado junto com execução concorrente, com a fixture `fixtures/terraform/bookmarks_with_concurrency/` como golden | `tests/test_fixtures_golden_terraform.py` |
| Compatibilidade de checkpoint de Structured Streaming (§6.11, §13) | NÃO EXISTE | O único checkpoint julgado no repositório é o de GraphFrames (`SF-GRAPH-001`), que é outra coisa: exigência de diretório para um algoritmo de grafo, não compatibilidade de estado entre versões de Spark. Nada observa offset, watermark, state store nem formato de checkpoint | — |

## 4. Conector e JDBC (§6.12)

Esta é a única lacuna de domínio inteiramente descoberta que a leitura encontrou.

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| JDBC como fábrica de DataFrame reconhecida pelo extrator | EXISTE, com teste | `sparkforge/facts/data_quality.py` conhece `jdbc` no vocabulário fechado de fábrica de DataFrame — é o que impede uma leitura JDBC de virar origem desconhecida na investigação de qualidade | `tests/test_facts_data_quality.py` |
| URL de JDBC tratada como portadora de segredo | EXISTE, sem teste | `sparkforge/facts/secrets.py` casa senha embutida em URL, o que pega JDBC. O módulo tem um único consumidor (`sparkforge/facts/event_log.py`) e **nenhum teste**: `terraform.py`, `emr_cluster.py` e `emr_serverless.py` carregam, cada um, uma cópia privada de `_looks_like_secret`, e são essas cópias que os testes de redação exercitam | — |
| Inventário de driver, versão, protocolo, TLS e certificado | NÃO EXISTE | Nenhum fact observa driver JDBC. A §4 pede JDBC como eixo da matriz de runtime, e ele também não está lá | — |
| Julgamento de configuração de leitura JDBC | NÃO EXISTE | `partitionColumn`, `numPartitions`, `lowerBound`, `upperBound` e `fetchsize` não aparecem em lugar nenhum do repositório — nem como fact, nem como regra, nem como conhecimento. Uma leitura JDBC de partição única contra uma origem grande é o gargalo clássico, e nada aqui o vê | — |
| Comparação de driver embarcado entre versões de Glue | NÃO EXISTE | Consequência da linha acima e da matriz sem eixo de JDBC | — |

## 5. Fluxo operacional e artefatos do harness (§7, §12)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Máquina de fases com gate fail-closed | EXISTE, com teste | `sparkforge/case/store.py` declara `PHASES` e `GATES`, e o contrato de cada gate vive em `rules/catalog/routing.yaml`, com `satisfied_by`, `produced_by` e `guards_phases`. Avançar de fase com gate aberto é recusado, não avisado | `tests/test_case_store.py` |
| Cobertura das fases que a §7 enumera | EXISTE PARCIAL | Intake, inventário, facts, diagnóstico, hipótese, experimento, validação e relatório existem. ADR, SDD, shadow run, teste de escala, canary, cutover e pós-migração não são fase da máquina — os quatro últimos aparecem só como eixo de gate que nasce `BLOCKED` | `tests/test_case_store.py` |
| Estados de gate | EXISTE PARCIAL | `sparkforge/migration/assessment.py` usa `FAIL`, `BLOCKED`, `PASS_WITH_RISK` e `PASS`, ordenados do pior para o melhor, e o pior vence quando duas evidências falam do mesmo eixo. O quinto estado que a §12 pede, `NOT_APPLICABLE`, não existe — e a seção final explica por que não deve passar a existir | `tests/test_migration_assessment.py` |
| Evidência auditável e reproduzível | EXISTE, com teste | O caso versiona `case.yaml`, `facts.json`, `findings.json`, `handoff.md` e `artifacts/manifest.json`, este último com sha256, origem e comando de recoleta de cada artefato bruto | `tests/test_case_store.py` |
| Relatório assinado, verificável depois | EXISTE, com teste | `sparkforge report sign` e `report verify` calculam a assinatura sobre o corpo sem o bloco de assinatura, e dizem qual versão assinou contra qual está valendo | `tests/test_adapters_report_signature.py` |
| Artefatos nomeados da §12 | EXISTE PARCIAL | O conteúdo de boa parte deles existe sob outros nomes — matriz de versão, matriz de compatibilidade, registro de decisão, plano de teste, métricas de baseline e de candidato, relatório de reconciliação. Nenhum sai com o nome de arquivo que a §12 fixa, e a lista dela inclui itens sem produtor nenhum: `sbom`, `dependency-lock`, `rollback-runbook.md` e `cutover-runbook.md` | `tests/test_case_store.py` |
| Shadow run, teste de escala, canary e cutover | NÃO EXISTE | Os eixos existem no contrato, e nascem `BLOCKED` com o motivo escrito: exigem execução real contra AWS viva, e nenhuma análise estática os preenche. Isso é o resultado correto, não a pendência — mas quem procura a execução não a encontra aqui | — |

## 6. Qualidade e equivalência de dados (§6.9, §10)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Validação funcional da saída antes de performance | EXISTE, com teste | `sparkforge/facts/funcval.py` monta plano e comparação sobre os eixos de contagem, schema, chaves e agregados, e carrega, no próprio fact, o aviso de que os quatro iguais **não** provam que o dado é o mesmo | `tests/test_facts_funcval.py` |
| Reconciliação com o repertório que a §6.9 enumera | EXISTE PARCIAL | Os eixos acima cobrem contagem, chave distinta, nulo por agregado e soma. Percentil, checksum, hash por linha, contagem por partição, integridade referencial, drift e amostra direcionada não existem | `tests/test_facts_funcval.py` |
| Regra de qualidade declarada no job | EXISTE, com teste | `sparkforge/facts/data_quality.py` reconhece suite de validação pela forma da chamada, não pela sequência, e `rules/catalog/data-quality.yaml` julga onde a validação está e o que ela custa em passada sobre o dado | `tests/test_facts_data_quality.py` |
| Contrato de dado e DQDL | NÃO EXISTE | Não há leitor de DQDL nem representação de contrato de dado como artefato versionado | — |

## 7. Performance em escala (§6.10, §9)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Diagnóstico antes de configuração | EXISTE, com teste | `sparkforge/facts/event_log.py` deriva bytes, registros, tarefa, spill e sinal de OOM do event log, e `sparkforge/facts/spark_plan.py` lê o plano físico com vocabulário fechado de operador. É a exigência da §9 em dado, não em conselho | `tests/test_facts_event_log.py` |
| Comparação entre duas execuções | EXISTE, com teste | `sparkforge/facts/benchmark.py` compara execuções por métrica real e nomeia os artefatos de cada lado; medida sem a chave que ela exige não vira zero, vira sentinela | `tests/test_facts_benchmark.py` |
| Comparação parametrizada por versão de runtime | EXISTE, com teste | `build_benchmark(..., before_runtime=, after_runtime=)` só emite `bench.runtime_pair` quando os dois lados são runtimes diferentes; rótulo único e rótulos iguais têm cada um a sua recusa nomeada | `tests/test_facts_benchmark.py` |
| Skew, spill, small files e layout | EXISTE, com teste | `rules/catalog/pyspark.yaml`, `rules/catalog/parquet.yaml` e `rules/catalog/spark-plan.yaml` julgam sobre o plano e sobre a listagem de objetos | `tests/test_fixtures_golden_plan.py` |
| Recusa de linearidade entre volume e recurso | EXISTE PARCIAL | O catálogo não recomenda aumento de worker sem evidência de limitação de memória (`SF-GLUE-005`), que é metade do que a §6.10 pede. Não existe modelo de capacidade que projete recurso a partir de volume — e a ausência é deliberada, porque projetar isso sem baseline seria exatamente a receita universal que a §2 proíbe | `tests/test_fixtures_golden_terraform.py` |

## 8. Segurança, Lake Formation e cross-account (§6.8, §6.13, §11)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Grafo de permissão e diagnóstico cross-account | EXISTE, com teste | `sparkforge/lakeformation/graph.py` e `sparkforge/lakeformation/doctor.py`, expostos em `forge lakeformation diagnose-cross-account` | `tests/test_lakeformation_engine.py` |
| IAM, KMS, rede e cross-account como eixo do assessment | EXISTE, com teste | As áreas `SF-KMS`, `SF-NET` e `SF-XACC` deram produtor aos três eixos que antes eram decorativos; cada um declara o fact que o destrava e nasce `BLOCKED` nomeando a evidência que falta | `tests/test_migration_assessment.py` |
| Segredo em argumento de job | EXISTE, com teste | `SF-GLUE-006` sobre `tf.attribute`, com o valor redigido no próprio fact — a evidência mostra que havia segredo sem mostrar o segredo | `tests/test_facts_terraform.py` |
| Detector de segredo unificado | EXISTE PARCIAL | `sparkforge/facts/secrets.py` é o módulo canônico e tem um único consumidor. `terraform.py`, `emr_cluster.py` e `emr_serverless.py` carregam, cada um, cópia privada da mesma heurística, e são as cópias que os testes cobrem. A mesma pergunta implementada em paralelo, sem conversão entre as versões | `tests/test_facts_emr_cluster.py` |
| PII, mascaramento, tokenização e regime regulatório | NÃO EXISTE | Nada no repositório classifica dado pessoal nem representa LGPD, GDPR ou PCI DSS. O que existe é redação de segredo, que é outra coisa | — |

## 9. Observabilidade e FinOps (§6.14)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Observabilidade do job como regra, não como conselho | EXISTE, com teste | `SF-GLUE-002` acusa job de produção sem observabilidade, com o par de fixtures `observability_without_glue_context` de um lado e o mesmo argumento com `glueContext` do outro; `knowledge/glue/observability.md` registra o que a métrica alcança e o que ela não alcança | `tests/test_fixtures_golden_infra_code.py` |
| Preço com fonte, data e região | EXISTE, com teste | `knowledge/glue/pricing.yaml` traz o preço publicado por DPU-hora com `source`, `source_type`, `retrieved`, região e versão de runtime — as duas últimas como `UNQUALIFIED`, porque a fonte publica um número só. O módulo não expõe cálculo de desconto nenhum, e há teste que mede essa ausência | `tests/test_glue_pricing.py` |
| Custo por terabyte, por partição e por job | NÃO EXISTE | O preço existe como dado; nenhuma derivação por unidade de negócio existe, e derivá-la exigiria a execução medida que os gates declaram ausente | — |
| SLA, SLO, RTO e RPO | NÃO EXISTE | Nenhum vocabulário de objetivo de serviço no repositório | — |

## 10. Biblioteca de erros (§13)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Biblioteca de erros com casamento determinístico | EXISTE, com teste | `knowledge/errors/` guarda uma entrada por erro observado e `sparkforge/errors/matcher.py:DeterministicErrorMatcher` casa texto de log contra a assinatura, sem chamada de modelo | `tests/test_error_matcher.py` |
| Exigência de fonte oficial e data por entrada | EXISTE, com teste | Toda entrada do diretório precisa de `sources` e `last_verified`, e o teste varre o diretório inteiro cobrando os dois. Erro hipotético não entra: conhecimento inventado com forma de conhecimento observado é pior que lacuna | `tests/test_error_matcher.py` |
| Campos do schema da §13 | EXISTE PARCIAL | O schema local cobre, sob outros nomes, `error_id`, `symptom`, `exact_error`, `diagnostic_steps`, `solution`, `rollback`, `validation`, `official_references` e `last_verified_at`. Faltam de fato: `glue_source_version`, `glue_target_version`, `runtime`, `category`, `context`, `security_impact` e `data_impact`. E três campos existem com sentido **diferente**, não equivalente: `root_cause` virou `likely_causes` (hipótese plural, não causa determinada), `evidence` virou `evidence_required` (o fact que a entrada exige, não a evidência observada) e `workaround` virou `unsafe_fixes` (a correção que **não** se deve fazer) | `tests/test_error_matcher.py` |
| Cobertura das categorias que a §13 enumera | EXISTE PARCIAL | Há entrada para incompatibilidade binária de Scala, `NoSuchFieldError` de SDK, formato Iceberg contra Athena, OOM de executor, conflito de commit Iceberg e negação de acesso cross-account. Erro de ANSI, parsing de data, wheel incompatível, endpoint de S3, tipo de JDBC, checkpoint, duplicidade de saída e regressão de bookmark não têm entrada — e não devem ganhar uma antes de alguém observar o texto exato numa fonte oficial | `tests/test_error_matcher.py` |

## 11. Contrato de saída do orquestrador (§14)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Recomendação final em vocabulário fechado | EXISTE, com teste | `MigrationAssessment.recommendation` sai em `GO`, `CONDITIONAL_GO` ou `NO_GO`; o mesmo vocabulário é `enum` no schema da tool MCP, aparece no golden de cada cenário e no holdout | `tests/test_fixtures_scenarios.py` |
| Blocker vence score | EXISTE, com teste | Gate em `FAIL` força `NO_GO`, e gate sem evidência nasce `BLOCKED` e nunca `PASS` — nenhuma recomendação favorável sai de evidência ausente | `tests/test_migration_assessment.py` |
| Lacuna nomeada em vez de silêncio | EXISTE, com teste | `missing_evidence` diz, por eixo, qual fact falta e qual artefato o traria — o `.tf` do job, o inventário de consumidores, a execução comparada. É a diferença entre "não avaliado" e "aprovado" | `tests/test_migration_assessment.py` |
| Alteração proposta com risco, teste e rollback | EXISTE PARCIAL | Toda regra de migração (`SF-MIG-*`, `SF-SPARK4-*`) declara `proposed_change`, `risks`, `validation` e `rollback`, e o `Finding` os leva até a saída. O carregador **não** os exige: `_REQUIRED` em `sparkforge/rules/loader.py` cobra `id`, `category`, `title`, `requires_facts`, `when`, `runtime_scope` e `sources`, e regra sem campo de remediação carrega sem erro. A garantia vem da disciplina do catálogo, não do código | `tests/test_rules_loader.py` |
| Tabela de evidência com fonte e data | EXISTE PARCIAL | O `Finding` carrega evidência citável e trecho da fonte, e o conhecimento carrega `source` e `retrieved`. Não existe a tabela única afirmação-evidência-fonte-data que a §14 pede como saída | `tests/test_findings_models.py` |
| Vocabulário de decisão da §14 | NÃO EXISTE | `APPROVED_FOR_CANARY`, `APPROVED_FOR_PRODUCTION`, `APPROVED_WITH_EXPLICIT_RISK_ACCEPTANCE`, `REJECTED` e `BLOCKED_PENDING_EVIDENCE` não existem, e a seção final explica por que não devem entrar | — |

---

## Conclusões

### 1. O que o prompt realmente acrescentaria, excluídas as duplicatas

- **Conector e JDBC como domínio.** É a única frente deste prompt sem nenhum equivalente:
  não há fact que observe driver, nem regra que julgue configuração de leitura, nem eixo de
  JDBC na matriz de runtime, nem entrada de erro para incompatibilidade de tipo. Um fact que
  observasse a chamada de leitura JDBC e as chaves de particionamento seria trabalho de
  extrator comum, no molde de `mig.python_dep`, e teria consumidor imediato: o assessment de
  migração e a investigação de performance.
- **Eixos que faltam na matriz de runtime.** Hudi, Delta, Hadoop, Arrow, Boto3 e JDBC. Aqui
  a lacuna **não** é de código: o carregador já recusa célula sem fonte, então o custo é
  encontrar a fonte oficial que enumere cada um por versão. Onde ela não existir, a célula
  fica `UNKNOWN`, que é o resultado honesto e já é o comportamento da matriz de features.
- **Compatibilidade de checkpoint de Structured Streaming entre versões.** Nada aqui a
  observa, e ela é irreversível na prática: um checkpoint que não recarrega no runtime novo
  não tem rollback barato.
- **Distinção DynamicFrame contra DataFrame no código do job.** É o fact que falta para a
  §8.7 e, ao mesmo tempo, para a armadilha de tipo novo de Iceberg que
  `knowledge/storage/iceberg-v3.md` já descreve e declara sem sustentação.
- **Um papel nomeado para o harness de validação de migração.** Não um agent novo — ver a seção
  sobre o que não fazer —, mas o dono declarado da suíte de goldens, que hoje existe sem dono.

### 2. O que já existe e deveria ser integrado, não escrito

A lista longa, e ela é a maior parte do prompt: matriz de runtime com procedência e recusa de
célula sem fonte; caminho por degraus derivado da ordem da matriz; extrator de facts de
migração cobrindo SDK, EMRFS, ANSI, API removida, formato de tabela, JAR e dependência
Python; catálogo com `runtime_scope` por regra, guardado por Spark onde a fronteira é do
Apache e por Glue onde ela é da AWS; gates fail-closed com `missing_evidence` nomeando o
artefato que destrava cada eixo; máquina de fases com gate que recusa avanço; relatório
assinado e verificável; biblioteca de erros com fonte e data cobradas por teste; preço com
procedência e sem cálculo de desconto; comparação de execução parametrizada por runtime; e
recomendação em vocabulário fechado, com golden por cenário.

A §1 do prompt pede uma plataforma que analise, migre, teste, valide, otimize, proteja,
documente e observe. Quase tudo isso já tem porta de entrada: `sparkforge migrate glue`,
`sparkforge glue dependency-audit`, `sparkforge iceberg assess-upgrade`,
`forge lakeformation diagnose-cross-account`, mais as tools MCP equivalentes. O trabalho que
sobra é ligar, não construir.

### 3. O que NÃO fazer, e por quê

- **Não acrescentar `NOT_APPLICABLE` aos estados de gate.** Provar não-aplicabilidade exige
  **evidência negativa**, e o repositório não tem como produzi-la. Declarar que Lake Formation
  não se aplica porque nenhum fact de Lake Formation apareceu é inferência a partir de
  ausência, e a ausência aqui tem duas causas indistinguíveis: o job realmente não usa, ou a
  análise não recebeu o `.tf` onde isso é declarado. `BLOCKED` com `missing_evidence` já
  distingue as duas de forma honesta — ele diz qual artefato falta e onde ele é declarado —,
  e é fail-closed: um eixo não avaliado nunca vira aprovação. `NOT_APPLICABLE` seria um `PASS`
  disfarçado, com a agravante de parecer uma observação.
- **Não trocar o vocabulário de decisão.** `GO`, `CONDITIONAL_GO` e `NO_GO` não são só uma
  convenção de prosa: são `enum` no schema da tool MCP, são o valor conferido no golden de
  cada cenário de `fixtures/scenarios/`, aparecem no `expected` do holdout e são citados na
  skill de migração. Trocar por sinônimos quebraria os goldens e o contrato da tool sem
  acrescentar nenhuma distinção que a saída já não faça: `CONDITIONAL_GO` com o eixo de canary
  `BLOCKED` **é** "aprovado para canary", só que dizendo qual evidência sustenta a condição em
  vez de embutir a condição no rótulo. E `BLOCKED_PENDING_EVIDENCE` já é, campo a campo, o par
  gate `BLOCKED` mais `missing_evidence`.
- **Não criar os agentes que faltam pelo nome.** `python-dependency-specialist`,
  `scala-java-jars-specialist` e `connector-jdbc-specialist` são nomes de papel, não
  capacidades. Os dois primeiros já têm o comando que faria o trabalho, e criar um perfil que
  só o chama acrescenta superfície sem acrescentar julgamento — cada agent novo entra nos
  gates de paridade, precisa de espelho byte a byte em cada diretório de plataforma e lá fica
  para sempre. O terceiro é pior: criar um especialista em JDBC antes de existir fact, regra
  ou conhecimento de JDBC produz um perfil que não tem o que consultar, e um agent sem lastro
  por baixo responde do mesmo jeito que um modelo sem ferramenta nenhuma. O próprio ecossistema
  de prompts deste projeto proíbe isso em outras palavras: nunca criar agent permanente apenas
  para aumentar o número total. A ordem certa é a inversa e já foi seguida antes — o fact e a
  regra primeiro, o agent depois, quando houver o que ele consulte.

### 4. Desvios encontrados durante a auditoria

Nenhum deles é pedido do prompt; são divergência entre documento e código, achados
ao conferir as linhas acima, e ficam registrados aqui porque documento que envelhece calado é
o defeito que o gate de lastro existe para impedir.

- **`docs/aws/glue/6.0/known-unknowns.md` está desatualizado.** Ele afirma que não existe
  avaliação de upgrade de formato de tabela, que não existe auditoria de dependência como
  comando, que não existe conhecimento de preço com data e região e que não existe benchmark
  parametrizado por versão de runtime. Todas elas passaram a existir nas fases H4 e H5.
  A causa estrutural já está registrada em `GLUE6-GAP.md`: `docs/aws/` não está sob o gate de
  lastro, então nenhuma afirmação daqueles documentos é auditada.
- **A linha do pipeline nomeado em `GLUE6-GAP.md` envelheceu.** Ela diz que `iam_kms`, `rede`
  e `cross_account` são nomeados e sempre `BLOCKED`, por não terem produtor nenhum. Desde que
  as áreas `SF-KMS`, `SF-NET` e `SF-XACC` existem, os três têm produtor e o dicionário de
  eixos sem produtor está vazio.
- **O mesmo desvio dentro do teste.** O docstring de `TestEixosNomeados`, em
  `tests/test_migration_assessment.py`, ainda afirma que `iam_kms`, `rede` e `cross_account`
  não têm produtor nenhum — e a classe abaixo dele já contém o teste que prova o contrário,
  medindo que os três saem de `BLOCKED` quando o Terraform chega. O comportamento está certo
  e o teste também; o texto que os explica é que envelheceu.
