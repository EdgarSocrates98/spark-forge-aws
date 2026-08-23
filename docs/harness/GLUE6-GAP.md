# GLUE6-GAP — o que já existe contra o que `prompt_glue_harness.md` pediria

`prompt_glue_harness.md` propõe suporte profundo a AWS Glue 6.0, Spark 4.1, Iceberg 1.11 e
Iceberg spec v3, além das cinco migrações com alvo Glue 5.1 ou 6.0 que ele enumera. Sua §28 é
taxativa na mesma direção do harness anterior: "NÃO crie um sistema paralelo". Sua §86 e sua
§105 mandam implementar, não parar na pesquisa.

Este documento existe entre as duas exigências. Ele responde, componente a componente, uma
única pergunta antes de qualquer módulo novo: **isso já existe aqui, possivelmente sob outro
nome?** É o mesmo gênero de [`CURRENT-HARNESS-GAP.md`](CURRENT-HARNESS-GAP.md), aplicado a um
prompt diferente, e segue as mesmas regras de classificação.

## Como classificar

- **EXISTE, com teste** — nomeio o módulo e o arquivo de teste que exercita o comportamento.
- **EXISTE PARCIAL** — nomeio o que está lá e o que falta, especificamente.
- **NÃO EXISTE** — digo isso.

Nenhuma linha diz "existe" sem caminho. Nenhuma diz "testado" sem nome de arquivo de teste.

Achado central da leitura: **a fase `SF-MIG` já entregou o esqueleto que este prompt pede
para as §7, §31, §36, §42 e §43** — matriz de runtime como dado com procedência, expansão de
caminho por degraus, extrator de facts de migração, área de regras com `runtime_scope` e um
contrato de avaliação com gates fail-closed e `missing_evidence`. O que o prompt pede e não
existe se concentra em três frentes distintas, nenhuma delas "harness": representação de
conflito entre fontes, conhecimento de Spark 4 e de Iceberg v3, e a ligação entre um diff de
Terraform e a avaliação de migração.

---

## 1. Fatos de runtime e procedência (§1, §2, §3, §44, §46)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Matriz de runtime verificada, fora do código | EXISTE, com teste | `knowledge/glue/runtime-matrix.yaml` (dado, com `sources` e `retrieved` por versão) carregado por `sparkforge/facts/runtime_matrix.py`; `GLUE_MATRIX` já foi apagado de `sparkforge/facts/runtime_detect.py` | `tests/test_runtime_matrix.py`, incluindo `TestSemVersaoNoCodigo`, que proíbe versão de Glue hardcoded fora do loader |
| Baseline das versões a validar (§3) | EXISTE, com teste | Cinco versões na matriz. Glue 6.0 declara Spark `4.1.1`, Python `3.13`, Scala `2.13.17`, Java `17` e Iceberg `1.11.0` | `tests/test_runtime_glue_versions.py`, `tests/test_runtime_matrix.py` |
| Fonte oficial vigiada com data de recuperação | EXISTE, com teste | `knowledge/sources.lock.json` guarda `retrieved` por URL; `migrating-version-60.html` e `release-notes.html` são as fontes citadas pela linha de Glue 6.0 da matriz | `tests/test_runtime_matrix.py::TestMatrizDeVersoes::test_toda_fonte_esta_no_lock_de_fontes` |
| Campos `source_type`, `status` e `retrieved` por fato temporal (§1) | EXISTE, com teste | Forma longa de componente em `knowledge/glue/runtime-matrix.yaml`, resolvida por `sparkforge/facts/runtime_matrix.py`: cada `claim` carrega `value`, `source`, `source_type` e `retrieved`. `confidence` continua sem existir — severidade e status já cobrem o uso que o motor faz hoje, e um campo a mais sem consumidor seria etiqueta | `tests/test_runtime_matrix.py::TestEvidenciaPorFonte` |
| Estados `VERIFIED`/`CONFLICTING`/`UNRESOLVED` (§1, §45, §78) | EXISTE, com teste | `runtime_matrix.load()` retém o valor de componente em disputa em vez de escolher um, e `conflicting()` lista os pares retidos. Duas invariantes ficam em código, não em disciplina: `VERIFIED` com fontes discordantes estoura, e `CONFLICTING` com fontes concordando também. `STALE` e `UNVERIFIED` são recusados de propósito — afirmam frescor, que depende do TTL por domínio que ainda não existe | `tests/test_runtime_matrix.py::TestEvidenciaPorFonte`, `::TestComponenteEmDisputaNaoJulgaRegra` |
| Classificação de qualidade de fonte (§46) | EXISTE, com teste | `runtime_matrix.SOURCE_TYPES`, vocabulário fechado com os sete tipos que a §46 nomeia. Ranking de autoridade explica a discordância; não a apaga — o status continua sendo o que retém o valor | `tests/test_runtime_matrix.py::TestEvidenciaPorFonte::test_source_type_fora_do_vocabulario_estoura` |
| TTL de conhecimento por domínio (§44) | EXISTE PARCIAL | `sparkforge/context/knowledge_pack.py:KnowledgePackLoader` calcula staleness de pacote de conhecimento e `scripts/refresh_knowledge.py` reconcilia o lock. Falta o que a §44 pede: TTL configurável **por domínio**, hoje inexistente como dado | `tests/test_context_funnel.py`, `tests/test_refresh_knowledge.py` |

## 2. Caminho e grafo de migração (§7, §40, §41)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Expansão `origem → alvo` em degraus | EXISTE, com teste | `sparkforge/migration/version_path.py:steps()` deriva os degraus da ordem da matriz, sem par de versão escrito no código | `tests/test_version_path.py` |
| Composição multi-hop (§7) | EXISTE, com teste | `sparkforge/migration/assessment.py:assess()` chama o `judge` uma vez por degrau e agrega em `by_step`, compondo os degraus intermediários sem obrigar execução deles | `tests/test_migration_assessment.py::test_cada_finding_registra_em_que_degrau_nasceu` |
| Deduplicação de finding entre degraus (§40) | EXISTE, com teste | `MigrationAssessment.report()` colapsa por `(rule_id, subject, evidence)`, guarda a instância mais severa e lista todos os degraus em que o problema vale. `findings` e `by_step` mantêm a cardinalidade por degrau — as duas visões respondem perguntas diferentes, e `to_dict()` traz as três | `tests/test_migration_assessment.py::TestRelatorioDeduplica`, `::TestRelatorioMantemAPiorSeveridade` |
| `RuntimeChangeGraph` com nós por componente (§41) | NÃO EXISTE | `version_path` é uma cadeia linear de versões de Glue. Não há nó `Spark`/`Python`/`Java`/`Scala`/`Iceberg`/`connector` com aresta `from_version`/`to_version`/`breaking`/`severity` consultável sem LLM | — |

## 3. Extração determinística e catálogo de regras (§42, §43)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Extrator de facts de migração | EXISTE, com teste | `sparkforge/facts/migration.py` emite kinds fechados em `EMITTED_KINDS`: `mig.sdk_import`, `mig.emrfs_config`, `mig.legacy_conf`, `mig.deprecated_api`, `mig.ansi_risk`, `mig.table_format`, `mig.jar_binary` e `mig.python_dep` | `tests/test_facts_migration.py`, `tests/test_fixtures_golden_migration.py` |
| Área de regras de migração com `runtime_scope` | EXISTE, com teste | `rules/catalog/glue-migration.yaml` traz a área `SF-MIG`, cada regra declarando a faixa de runtime onde vale — `SF-MIG-003` só a partir de Glue 6.0, pelo ANSI ligado por padrão no Spark 4.1 | `tests/test_migration_assessment.py`, `tests/test_rules_catalog_reachability.py` |
| Áreas `SF-SPARK4` e `SF-ICE-V3` (§43) | EXISTE PARCIAL | `SF-SPARK4` existe em `rules/catalog/spark4.yaml` com três regras, guardadas por versão de **Spark** e não de Glue — a fronteira é do Apache e vale igual num EMR. `SF-ICE-V3` continua sem existir e depende do conhecimento de Iceberg v3 como dado | `tests/test_spark4_rules.py`, `tests/test_rule_scope_by_nature.py` |
| Roteamento explicável das regras de migração | EXISTE, com teste | `rules/catalog/routing.yaml` roteia `SF-MIG` e devolve razão, evidência e alternativas | `tests/test_case_router.py`, `tests/test_router_agents.py` |

## 4. Spark 4 (§10, §11, §12)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Conhecimento de breaking changes de Spark `3.3` a `4.1` | EXISTE, com teste | `knowledge/spark/spark4-migration.md`, confirmado contra o SQL migration guide e o Upgrading PySpark do Spark 4.1.1: configs renomeadas, APIs de pandas-on-Spark removidas, pisos de dependência e as mudanças de comportamento sem sinal no código. As três primeiras viraram regra em `rules/catalog/spark4.yaml` | `tests/test_spark4_rules.py`, `tests/test_offline_expansion.py` |
| `sparkforge_spark4_migration_scan` (§11) | EXISTE PARCIAL | O vocabulário existe: `sparkforge/facts/migration.py` emite `mig.renamed_conf` e `mig.removed_api`, e `sparkforge/facts/pyspark_ast.py` cobre a análise AST. Falta só a tool MCP dedicada — e ela pode não ser necessária, porque `sparkforge_analyze_pyspark` mais `sparkforge_judge` já entregam o mesmo resultado sem superfície nova | `tests/test_facts_migration.py`, `tests/test_spark4_rules.py` |
| Skills `spark-4-*` (§12) | NÃO EXISTE | — | — |

## 5. Compatibilidade binária: Scala, Java e JAR (§13, §14)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Observação de JAR no job | EXISTE, com teste | `mig.jar_binary` carrega `scala` e `scala_minor` derivados do sufixo do nome do artefato, e `SF-SPARK4-004` julga em P0 quem estiver abaixo de Scala 2.13 sob Spark 4. Limite declarado: o fact observa todo `.jar` da árvore, inclusive um que seja recurso de teste fora do classpath do job — separar exigiria um fact sobre `--extra-jars`, que não existe | `tests/test_spark4_rules.py`, `tests/test_facts_migration.py` |
| `sparkforge_jar_compatibility_scan` (§13) | NÃO EXISTE | — | — |
| Golden de JAR Scala antigo em Glue 6.0 (§14) | EXISTE, com teste | `fixtures/migration/spark4_jar_scala_212/` dispara `SF-SPARK4-004`; `fixtures/migration/jar_binary/` é o par negativo **por versão** — mesmo artefato, runtime abaixo do Spark 4. Os vereditos nomeados pela §14 (`RECOMPILE_REQUIRED`, `BLOCKED`) continuam sem existir como vocabulário próprio | `tests/test_fixtures_golden_migration.py` |

## 6. Python e dependências (§15, §16)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Observação de dependência Python | EXISTE PARCIAL | `mig.python_dep` observa dependência declarada. Falta o julgamento da §15: wheel binária, extensão nativa, pin de versão e risco de ABI | `tests/test_facts_migration.py` |
| `forge glue dependency-audit` (§16) | NÃO EXISTE | — | — |

## 7. Iceberg 1.11 e spec v3 (§17 a §24, §47 a §50)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Diagnóstico de tabela Iceberg | EXISTE, com teste | `sparkforge/iceberg/doctor.py:IcebergTableDoctor` devolve `format_version` no `IcebergHealthReport`; `sparkforge/facts/iceberg_metadata.py` extrai metadados de dump | `tests/test_iceberg_doctor.py`, `tests/test_facts_iceberg_metadata.py`, `tests/test_fixtures_golden_iceberg.py` |
| Versão do formato distinta da versão da biblioteca (§18) | EXISTE, com teste | `mig.table_format` separa as duas — é onde a distinção entre "spec feature" e "engine support" começa | `tests/test_facts_migration.py` |
| Conhecimento de Iceberg 1.11 (§17) | EXISTE, com teste | `knowledge/storage/iceberg-v3.md` traz o que a release de 1.11.0 declara — remote scan planning com REST catalog, API de estatística de partição, deletion vectors em Flink e Spark, Java 11 removido, Spark 3.4 deprecado e Spark 4.1 suportado. O que a fonte não afirma fica marcado como a verificar | `tests/test_offline_expansion.py` |
| Domínio `iceberg-v3`, Variant, deletion vectors e row lineage (§18, §21, §22, §23) | EXISTE PARCIAL | `knowledge/storage/iceberg-v3.md` separa **feature da spec** de **suporte da engine**, que é o que a §18 exige, e registra as limitações que a AWS declara para o Glue 6.0. Não existe fixture nem regra: os facts que permitiriam julgar uso de Variant, transform multi-argumento ou DynamicFrame não existem, e a única armadilha judicável hoje já é `SF-ENV-002` | `tests/test_offline_expansion.py` |
| `IcebergFeatureCompatibilityMatrix` (§19, §20) | EXISTE, com teste | `knowledge/storage/iceberg-feature-support.yaml` cruza feature de Iceberg com engine, uma célula por par, e `sparkforge/storage/feature_support.py` recusa a matriz inteira quando uma célula afirma suporte sem `source`, `source_type` e `retrieved` — a regra da §20 em código, não em prosa. A maioria das células é `UNKNOWN`, que é o resultado honesto de só uma engine ter documentação oficial enumerando feature de v3 por nome; o Athena tem uma única célula afirmativa, e há teste que impede a inferência de suporte entre engines | `tests/test_iceberg_feature_support.py` |
| `forge iceberg assess-upgrade` de formato v2 para v3 (§24) | NÃO EXISTE | — | — |
| Iceberg Doctor v2 com prontidão para v3 (§50) | EXISTE PARCIAL | O relatório existe e carrega `format_version`; prontidão para v3, uso de Variant e suporte por consumidor não existem | `tests/test_iceberg_doctor.py` |

## 8. Consumidores, Lake Formation e cross-account (§25 a §30)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Inventário de consumidores (§25) | EXISTE, com teste | `sparkforge/facts/consumers.py` emite `env.consumer` com vocabulário fechado de serviço | `tests/test_facts_consumers.py`, `tests/test_fixtures_golden_consumers.py` |
| Bloqueio por consumidor incompatível (§25) | NÃO EXISTE | O inventário existe; nada cruza feature de Iceberg contra consumidor para bloquear um upgrade | — |
| Grafo de permissão Lake Formation | EXISTE, com teste | `sparkforge/lakeformation/graph.py:LakeFormationPermissionGraph` e `sparkforge/lakeformation/doctor.py:LakeFormationDoctor`, expostos em `forge lakeformation diagnose-cross-account` | `tests/test_lakeformation_engine.py` |
| Matriz de operação por versão, FTA/FGAC e conta (§28) | EXISTE PARCIAL | `knowledge/glue/lakeformation-fgac.md` registra o que a AWS declara sobre FGAC — o que exige, o que bloqueia, a matemática de worker e o recorte de Iceberg — e a área `SF-LF` julga duas incompatibilidades declaradas. Não existe a matriz por **operação** (`SELECT`/`INSERT`/`MERGE`/`ALTER`) cruzada com conta: a fonte enumera limitação, não operação, e preencher célula por operação exigiria inferir | `tests/test_lakeformation_rules.py` |
| Separação entre control plane e data plane (§30) | EXISTE PARCIAL | O grafo modela aresta de permissão com origem e destino; a distinção nominal entre permissão de catálogo, Lake Formation, IAM, S3 e KMS que a §30 exige não está declarada como tipo | `tests/test_lakeformation_engine.py` |

## 9. Contrato do harness de migração (§31 a §37)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Contrato com entrada, gates e recomendação | EXISTE, com teste | `sparkforge/migration/assessment.py:MigrationAssessment` carrega `findings`, `by_step`, `gates`, `missing_evidence` e `recommendation` — é o modelo da §36 construído sem esse nome | `tests/test_migration_assessment.py` |
| Blocker vence score (§37) | EXISTE, com teste | Gate de compatibilidade em `FAIL` força `NO_GO`; gate sem evidência nasce `BLOCKED` e nunca `PASS`, então nenhuma recomendação `GO` sai de evidência ausente | `tests/test_migration_assessment.py::test_gate_sem_evidencia_e_blocked_nunca_pass` |
| Early exit determinístico (§35) | EXISTE PARCIAL | A avaliação é determinística de ponta a ponta e não chama agente nenhum, então o caso da §35 já é o padrão. Falta o inverso: nada escala para agente quando o fato determinístico não basta | `tests/test_migration_assessment.py` |
| Pipeline nomeado da §32 | EXISTE PARCIAL | Fase H2: o contrato passou a nomear os eixos que faltavam. `lakeformation` e `consumidor` são **calculados** — têm produtor (`SF-LF` sobre `tf.attribute`, `SF-ENV` sobre `env.consumer`) e nascem `BLOCKED` quando o fact não veio. `iam_kms`, `rede` e `cross_account` são nomeados e sempre `BLOCKED`, com a evidência que os preencheria: não têm produtor nenhum, e um gate que ninguém preenche é decoração. Parcial por esses três, não pela forma | `tests/test_migration_assessment.py` |
| Entradas opcionais da §31 (Terraform, JAR, topologia de Lake Formation, inventário de consumidores) | EXISTE, com teste | Fase H2: `sparkforge/migration/collect.py` compõe código, `.jar`, `requirements*.txt`, `.tf` quando existe e o inventário de consumidores na convenção `.sparkforge/consumers.yaml`. `assess()` continua puro sobre `list[Fact]` de propósito — composição é I/O, e I/O tem lugar próprio. A CLI, a tool MCP e `scripts/regen_fixtures.py` chamam a mesma função, então o golden descreve a união que o produto emite | `tests/test_migration_collect.py` |

## 10. Terraform (§61 a §64)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Leitura de `glue_version` no HCL | EXISTE, com teste | `sparkforge/facts/terraform.py` lê `glue_version` como atributo de raiz de `aws_glue_job` | `tests/test_facts_terraform.py`, `tests/test_fixtures_golden_terraform.py` |
| Diff com valor anterior | EXISTE, com teste | `extract_terraform_diff()` anota todo `tf.attribute` com `changed` e, quando muda, `previous_value` — a matéria-prima exata da §62 | `tests/test_fixtures_golden_tfdiff.py` |
| Finding de migração de runtime detectada (§64) | EXISTE, com teste | `SF-MIG-004`, em `rules/catalog/glue-migration.yaml`: casa `tf.attribute` com `key: glue_version` e exige `previous_value` diferente de `value`, então um `aws_glue_job` criado já em Glue 6.0 não é acusado de migrar. Declara `runtime_scope: {}` — a afirmação não depende de fronteira de versão, e o par origem/alvo vem do próprio fact | `tests/test_fixtures_golden_tfdiff.py`, com o par de fixtures `glue_version_migrado` (dispara) e `glue_job_novo` (não dispara) |

## 11. Custo, performance e correção de dados (§51 a §54)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Comparação de execuções | EXISTE, com teste | `sparkforge/facts/benchmark.py` e `sparkforge/facts/event_log.py` comparam execuções com métricas reais | `tests/test_facts_benchmark.py` |
| Correção antes de performance (§54) | EXISTE, com teste | `sparkforge/facts/funcval.py` faz validação funcional de saída — contagem, schema, chaves e agregados | `tests/test_facts_funcval.py`, `tests/test_fixtures_golden_funcval.py` |
| Gate que impede performance sem correção | EXISTE, com teste | Em `assess()`, os gates de dados, performance e custo nascem `BLOCKED` com o motivo escrito em `missing_evidence`, nunca `PASS` por omissão | `tests/test_migration_assessment.py::test_gate_sem_evidencia_e_blocked_nunca_pass` |
| Conhecimento de preço com data e região (§51) | NÃO EXISTE | — | — |
| Benchmark parametrizado por versão de runtime (§52) | NÃO EXISTE | O comparador de execuções existe; nada o parametriza por versão de runtime | — |

## 12. Empacotamento, roteamento e economia (§68 a §75)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Modo offline com manifesto e checksum | EXISTE, com teste | `knowledge/offline-manifest.json` mais `scripts/verify_offline_bundle.py`: conhecimento novo precisa entrar no manifesto e o checksum é verificado | `tests/test_offline_expansion.py` |
| Paridade entre repo, wheel, MCP e plugin | EXISTE, com teste | `parity.yaml`, `scripts/sync_skills.py --check` e `manifest.json` | `tests/test_capability_parity.py`, `tests/test_agents_parity.py` |
| Tools MCP a expandir em vez de multiplicar (§70) | EXISTE, com teste | `sparkforge/adapters/tools.py:TOOLS` já expõe `sparkforge_runtime_detect`, `sparkforge_analyze_iceberg`, `sparkforge_analyze_terraform_diff`, `sparkforge_analyze_consumers` e `sparkforge_rules_lookup` | `tests/test_adapters_tools.py`, `tests/test_adapters_mcp.py` |
| `CapabilityRegistry` com chave por capacidade (§74) | NÃO EXISTE | Já medido em [`CURRENT-HARNESS-GAP.md`](CURRENT-HARNESS-GAP.md): `sparkforge/registry/loader.py` indexa por tipo, não por capacidade | — |
| Skills de Glue 6 com disclosure progressivo (§9, §72) | NÃO EXISTE | Nenhuma skill atual é de Glue 6. A infraestrutura de disclosure existe em `sparkforge/context/progressive.py` | — |
| Agent especialista em migração (§8) | EXISTE PARCIAL | `agents/sf-runtime-specialist.md` declara compatibilidade entre versões numa migração. Não existe `sf-glue-migration-specialist`, e a §8 manda evoluir o especialista existente antes de criar outro | `tests/test_agents_parity.py` |

## 13. Avaliação, goldens e documentação (§38, §39, §76 a §84, §103)

| Componente pedido | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| Goldens do domínio de migração | EXISTE, com teste | `fixtures/migration/` cobre um caso por kind emitido, no formato `meta.yaml` mais `input/` e `expected/` | `tests/test_fixtures_golden_migration.py`, `tests/test_fixtures_kind_coverage.py` |
| Suítes de cenário para os pares com alvo Glue 6.0 (§38, §39) | EXISTE PARCIAL | `fixtures/scenarios/` traz cenário por par, com mais de um artefato, medido de ponta a ponta por `assess()` — inclusive o salto longo, que prova a acumulação por degrau e a deduplicação do relatório num caso realista. Três cenários, não os catorze da §38: caso que não dispara regra é fixture que não prova nada, e o `meta.yaml` de cada um registra o que foi deixado de fora e por quê | `tests/test_fixtures_scenarios.py` |
| Holdout não exposto às skills (§77) | EXISTE, com teste | `evals/holdout/` fica fora de `fixtures/` de propósito — os invariantes de lá cobram cobertura, e holdout não é cobertura. A propriedade é **provada**, não confiada: um teste varre `skills/`, `agents/`, `knowledge/` e os espelhos procurando o nome de cada cenário e o próprio caminho do diretório, com guarda de não-vacuidade | `tests/test_evals_holdout.py` |
| Golden de fontes conflitantes (§78) | EXISTE, com teste | Sintético e assim declarado: a matriz publicada não tem componente em disputa, e inventar um para exercitar o mecanismo é o que o próprio carregador recusa. O teste monta a matriz em disco e mede a consequência que importa — regra guardada pelo componente retido é pulada, não julgada | `tests/test_runtime_matrix.py::TestComponenteEmDisputaNaoJulgaRegra` |
| Gate de CI sobre alegação publicada | EXISTE, com teste | `scripts/check_vnext_claims.py` audita `docs/vnext/` e `docs/harness/`, fail-closed nos dois sentidos | `tests/test_vnext_claims.py` |
| Conhecimento de erro por domínio novo (§79) | NÃO EXISTE | `knowledge/errors/` já existe com subdiretórios por domínio, então o lugar está definido | — |
| Documentação dedicada e guia de decisão (§80, §81) | EXISTE PARCIAL | A pasta dedicada em `docs/aws/` traz porta de entrada, runtime, a fronteira do Spark, Iceberg, Lake Formation, prova, `known-unknowns.md` e `decision-guide.md` — este último sustentando "ficar na versão anterior" como resposta legítima e separando redução de preço de ganho de performance, que não foi medido aqui. Parcial pelo que falta **em volta**, não pelo conteúdo: `docs/aws/` não está em `audited_roots()`, então nenhuma alegação daqueles documentos é auditada e nenhum teste cobra a existência deles. A mitigação é estrutural — eles apontam para a fonte em vez de copiá-la | — |
| ADR de suporte a Glue 6.0 (§83) | EXISTE PARCIAL | `docs/vnext/adrs/ADR-009-glue-6-spark-4-iceberg-v3.md` registra as decisões da sequência: conhecimento como dado com fonte, guarda por Spark contra guarda por Glue, `UNKNOWN` por construção, skill sem consumidor não criada, extrator só com consumidor. Parcial pelo mesmo motivo das demais linhas de ADR deste repositório: ele está sob o gate de lastro, então toda alegação numérica dele é auditada, mas nenhum teste cita o documento por nome como asserção de entrega | — |

---

## O que este mapa recomenda atacar primeiro

Três frentes saíram do mapa com custo baixo e consumidor real. **As três já foram feitas** —
o que sobra do prompt está nas linhas `NÃO EXISTE` das tabelas acima, e o parágrafo final
diz por onde não começar:

1. ~~Ligar o diff de Terraform à avaliação de migração (§62, §64).~~ **Feito**: `SF-MIG-004`.
   Era a única linha deste documento em que o trabalho era conexão, não construção — os dois
   lados já existiam e eram testados. A linha da §64 na tabela acima registra o resultado.
2. ~~Representar conflito entre fontes (§1, §2, §45, §78).~~ **Feito**: forma longa de
   componente na matriz, com `status`, `source_type` e valor retido em disputa. A medição
   junto: a divergência de versão de Python que a §2 do prompt afirma **não se reproduz** —
   as três fontes oficiais dizem 3.13, e o registro ficou `VERIFIED` com as três, não um
   `CONFLICTING` inventado para exercitar o mecanismo.
3. ~~Decidir sobre deduplicação de finding entre degraus (§40).~~ **Feito**, e sem revogar a
   decisão anterior: a deduplicação vive na camada de relatório (`report()`), e o dado por
   degrau continua com a cardinalidade que o módulo já fixava. As duas visões
   respondem perguntas diferentes — "quantos problemas eu tenho?" e "isto ainda vale depois
   do próximo salto?".

O que este mapa recomenda **não** fazer agora: as skills das §9 e §12. Elas não têm consumidor
enquanto o conhecimento de Spark 4 não existir como dado.

A `IcebergFeatureCompatibilityMatrix` da §19 estava nesta lista, e saiu — mas a objeção que a
punha aqui **não foi revogada**. A objeção era "célula sem evidência é exatamente o que a §20
proíbe", e ela continua valendo; o que mudou é onde ela mora. Antes era uma advertência neste
parágrafo, que depende de quem lê; agora é uma invariante do carregador, que derruba a matriz
inteira na carga quando uma célula afirmativa chega sem fonte. A consequência prática de levar
a §20 a sério é que a maioria das células saiu `UNKNOWN` — e isso é o resultado, não a
pendência: `UNKNOWN` distingue "não há fonte" de "não suporta", que é a distinção que uma
matriz preenchida por inferência apagaria.
