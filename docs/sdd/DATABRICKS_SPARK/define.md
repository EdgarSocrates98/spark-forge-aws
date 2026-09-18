---
sdd: 1
feature: DATABRICKS_SPARK
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/DATABRICKS_SPARK/explore.md
  sha256: "20f18de94c88274cbfa38b62ba58d7325d7d1198f20ea0855c7097c274d6a5a7"
hypothesis:
  claim: "O extrator de event log e as regras sem runtime_scope julgam um job Spark no Databricks sem extrator novo de execucao, desde que plataforma e runtime sejam declarados e a fronteira (Photon, remediacao especifica de AWS) recuse com nome em vez de julgar."
  prediction: "Numa fixture sintetica Databricks pareada com uma fixture Glue existente, os findings das regras neutras coincidem; nenhum finding sob plataforma databricks traz remediacao especifica de AWS; com Photon sinalizado, as regras de plano saem recusadas. Se um finding divergir sem causa de plataforma, ou aparecer remediacao de AWS, a afirmacao esta errada."
  experiment: "Rodar judge sobre o par de fixtures (Glue e Databricks), comparar os findings, rodar a auditoria do catalogo e o teste da recusa de Photon."
acceptance:
  - id: AC1
    statement: "A declaracao --databricks <versao DBR> gera env.platform = databricks e deriva a versao do Spark pela matriz, com origem cli:matrix."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark"}
  - id: AC2
    statement: "knowledge/databricks/runtime-matrix.yaml carrega com fonte e data no nivel do documento, vocabulario fechado, e as linhas coincidem com a pagina oficial de versoes suportadas."
    verified_by: {kind: test, ref: "tests/test_databricks_runtime_matrix.py::test_matriz_tem_fonte_data_e_vocabulario_fechado"}
  - id: AC3
    statement: "Um event log que carrega a versao do Databricks Runtime nas propriedades de ambiente e detectado como plataforma databricks sem flag."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks"}
  - id: AC4
    statement: "Versao do Spark lida do event log que diverge da derivada pela matriz vira divergencia registrada, nunca resolucao silenciosa."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_divergencia_spark_registrada"}
  - id: AC5
    statement: "Sob plataforma databricks, com Photon sinalizado, as regras de plano JVM saem como databricks.photon.unresolved em vez de finding."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano"}
  - id: AC6
    statement: "Toda regra com runtime_scope vazio tem remediacao neutra de plataforma, ou ganha escopo, ou esta numa lista auditada de excecoes com motivo."
    verified_by: {kind: test, ref: "tests/test_databricks_rule_audit.py::test_regra_sem_escopo_nao_remedia_com_termo_aws"}
  - id: AC7
    statement: "spark.sql.shuffle.partitions = auto nao e lido como numero: regra e tune que dependem do valor devolvem recusa nomeada."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado"}
  - id: AC8
    statement: "Na fixture Databricks pareada, os findings das regras neutras sao os mesmos da fixture Glue equivalente."
    verified_by: {kind: test, ref: "tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros"}
  - id: AC9
    statement: "O crescimento da superficie pela flag nova esta declarado no surface lock."
    verified_by: {kind: command, ref: "python scripts/check_surface_lock.py"}
success:
  - id: SC1
    metric: "Regras com runtime_scope vazio classificadas como neutras, com escopo novo e em excecao auditada"
    source: "saida do teste tests/test_databricks_rule_audit.py e sparkforge rules lookup --index"
  - id: SC2
    metric: "Findings iguais e divergentes entre a fixture Glue e a Databricks pareada"
    source: "sparkforge judge sobre as duas fixtures, comparado pelo teste AC8"
out_of_scope:
  - "_delta_log, definicao de job/cluster pela Jobs API e billing em DBU: incrementos seguintes."
  - "Coletores collect_databricks_* pela REST API (abordagem C do explore)."
  - "Regras que julgam Photon: aqui Photon so recusa."
  - "SQL warehouse, DBSQL e serverless: a matriz cobre Databricks Runtime classico."
  - "Unity Catalog e governanca Databricks."
  - "Agente ou skill Databricks sem regra executavel por tras: nenhum agente oco novo."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Confirmar se o event log entregue por cluster log delivery traz spark.databricks.clusterUsageTags.sparkVersion nas propriedades de ambiente. A fonte T1 (docs.databricks.com/aws/en/udf/udf-task-context, atualizada 2026-09-11) so documenta a chave como propriedade local de TaskContext, valor '16.3', no Databricks Runtime 16.3+. Destrava: event log observado de um workspace trial, ou pagina T1 sobre o conteudo do event log. Sem nenhum dos dois, AC3 sai recusado e a deteccao fica so pela flag."
  - id: U2
    blocks: [AC5]
    unlock: "Descobrir como Photon aparece no event log (nome de operador no plano, propriedade de ambiente). A pagina T1 docs.databricks.com/aws/en/compute/photon (2026-09-11) documenta so a cor na UI e runtime_engine = PHOTON na API. Destrava: event log observado com Photon ligado, ou fonte T1."
  - id: U3
    blocks: [AC6]
    unlock: "Derivar a lista fechada de termos especificos de AWS lendo a remediacao das regras de runtime_scope vazio por sparkforge rules lookup --index, com a lista revisada pelo operador."
  - id: U4
    blocks: [AC7]
    unlock: "Ler com sparkforge code search o que extratores e tune fazem hoje com valor nao numerico em spark.sql.shuffle.partitions."
change_kinds: [extractor, knowledge_doc, rule, rule_runtime_scope, fixture_corpus, tool_or_verb, claims]
---

# DATABRICKS_SPARK — requisitos

## Problema

O SparkForge julga Spark no Glue e no EMR, mas um job Spark no Databricks hoje
passa pelo motor sem que a plataforma seja nomeada. As 176 regras sem
`runtime_scope` o avaliariam mesmo assim, e parte delas remedia com termos de AWS.
Onde o Databricks muda o significado (Photon, `shuffle.partitions = auto`), o
julgamento sairia errado em silêncio.

## Fontes citadas

- Matriz Databricks Runtime -> Spark: docs.databricks.com/aws/en/release-notes/runtime/,
  atualizada em 2026-09-11. Linhas: 19 -> 4.2.0, 18 LTS -> 4.1.0, 17.3 LTS -> 4.0.0,
  16.4 LTS -> 3.5.2, 15.4 LTS -> 3.5.0, 14.3 LTS -> 3.5.0.
- Chave de versão do runtime: docs.databricks.com/aws/en/udf/udf-task-context
  (2026-09-11), só como propriedade local de TaskContext (U1).
- Photon: docs.databricks.com/aws/en/compute/photon (2026-09-11). Fallback para
  Spark com UDF, RDD/Dataset API, streaming com estado e consulta abaixo de dois
  segundos; sinal no event log não documentado (U2).

## Critérios

- AC1, AC2, AC4, AC6, AC7 e AC8 não dependem de acesso a workspace.
- AC3 e AC5 dependem de U1 e U2. Sem event log observado nem fonte T1, saem como
  recusa nomeada no ship, não como promessa.
- `change_kinds` inclui `claims` porque arquivo `.py` novo move alegações do gate
  de lastro.
