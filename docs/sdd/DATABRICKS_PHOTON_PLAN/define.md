---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/DATABRICKS_PHOTON_PLAN/explore.md
  sha256: "bffa24a84e6e36c89c3b0e632ea0cb98fa5413ef6a29bf6f251bfc5577dbd4a8"
hypothesis:
  claim: "Photon e detectavel no texto do plano pelo prefixo dos operadores, e uma recusa movida por esse artefato substitui a dependencia da declaracao --photon sem mudar nenhum veredito de plano que nao tenha Photon."
  prediction: "Sobre os dois planos Photon observados (fixtures sinteticas derivadas da observacao de 2026-09-18), o SparkForge emite um fact de Photon e as regras de plano saem recusadas com nome, sem --photon e sem --databricks; sobre todas as fixtures de plano ja existentes, os achados ficam identicos. Se o plano Photon continuar calado, ou se qualquer golden de plano sem Photon mudar de veredito, a afirmacao esta errada."
  experiment: "Rodar o extrator e o judge sobre as fixtures Photon novas, regenerar os goldens de plano e comparar os vereditos das fixtures antigas antes e depois."
acceptance:
  - id: AC1
    statement: "Um plano com operadores Photon (prefixo Photon, como PhotonBroadcastHashJoin) gera um fact de Photon com a contagem de operadores Photon e, quando presente, a frase da secao == Photon Explanation ==."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_plano_photon_gera_fact_de_photon"}
  - id: AC2
    statement: "Com o fact de Photon presente, as regras que exigem kind de plano saem em skipped com databricks.photon.unresolved mesmo sem --photon e sem --databricks, exceto as que so exigem plan.python_udf."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_fact_de_photon_recusa_regra_de_plano_sem_declaracao"}
  - id: AC3
    statement: "Um plano sem operador Photon nao gera o fact de Photon, e os achados de todas as fixtures de plano ja existentes ficam identicos."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_plano_sem_photon_nao_muda_veredito"}
  - id: AC4
    statement: "Declaracao --photon off diante de plano com operadores Photon vira divergencia nomeada; o artefato vence a declaracao e a recusa vale."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_photon_off_contra_plano_photon_diverge"}
  - id: AC5
    statement: "Sob plataforma databricks, SF-ENV-006 nao dispara quando o plano ja mostra Photon: o artefato respondeu o que a declaracao responderia."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_plano_photon_cala_sf_env_006"}
  - id: AC6
    statement: "ArrowEvalPython deixa de ser rotulado como UDF pandas: o udf_type diz que a UDF e serializada em Arrow sem afirmar se veio de pandas_udf ou de UDF Python otimizada para Arrow, e a regra de UDF vetorizada continua disparando sem texto que afirme pandas_udf."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_arrow_eval_python_nao_afirma_pandas"}
  - id: AC7
    statement: "No plano Photon com UDF, o ArrowEvalPython entre operadores PhotonArrow continua reconhecido como UDF e a regra de UDF e julgada, nao recusada."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_udf_sob_photon_continua_julgada"}
  - id: AC8
    statement: "A secao 4 de knowledge/databricks/runtime-matrix.md deixa de listar o silencio do extrator como lacuna aberta e diz o que o SparkForge passou a fazer com o plano Photon."
    verified_by: {kind: test, ref: "tests/test_databricks_photon_plan.py::test_knowledge_registra_o_extrator_sob_photon"}
success:
  - id: SC1
    metric: "Fixtures de plano sem Photon com veredito diferente antes e depois"
    source: "diff dos findings.json de fixtures/plan regenerados, conferido pelo teste de AC3"
  - id: SC2
    metric: "Facts e regras recusadas sobre os dois planos Photon observados"
    source: "goldens das fixtures Photon novas em fixtures/plan"
out_of_scope:
  - "Mapear operadores Photon para os equivalentes do Spark (abordagem B do explore)."
  - "Plano Photon que chega pelo event log (SparkListenerSQLExecutionStart): nao observado."
  - "Regra nova que julgue o plano Photon em si (por exemplo, fallback parcial listado na secao de explicacao)."
  - "Deteccao de Photon pela pista -photon- do rotulo legado de spark_version (M10 de DATABRICKS_SPARK)."
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "A forma dos operadores Photon foi observada em um ambiente so (Databricks Free Edition, serverless, Spark 4.2.0, 2026-09-18). Planos de outros Databricks Runtime, ou documentacao oficial dos nomes de operador, confirmam que o prefixo Photon e estavel; ate la, o AC1 vale para a forma observada e o documento diz isso."
  - id: U2
    blocks: [AC1]
    unlock: "A secao == Photon Explanation == foi observada so com 'The query is fully supported by Photon.'; o texto de suporte parcial nao foi visto. Destrava: um plano com operacao nao suportada."
change_kinds: [extractor, rule, rule_runtime_scope, knowledge_doc, fixture_corpus, claims]
---

# DATABRICKS_PHOTON_PLAN — requisitos

## Problema

DATABRICKS_SPARK mediu que o extrator de plano fica calado diante de um plano Photon:
emite só `plan.analyzed` e `plan.aqe`, sem `plan.join`, `plan.exchange` nem
`plan.unresolved`. A recusa das regras de plano existe, mas só dispara quando o
operador declara `--photon on`. Quem não declara recebe silêncio, e silêncio lê como
"plano sem achado".

O `ArrowEvalPython` está rotulado como UDF pandas. Num Databricks observado, um
`@F.udf` comum apareceu como `ArrowEvalPython`, e a regra de UDF vetorizada
(SF-PLAN-002) dispararia afirmando pandas_udf.

## Fontes citadas

- Observação de 2026-09-18 em `knowledge/databricks/runtime-matrix.md` §4
  (Databricks Free Edition, serverless, Spark 4.2.0): operadores `Photon*`, seção
  `== Photon Explanation ==`, `ArrowEvalPython` entre `PhotonArrowBatchSink` e
  `PhotonArrowBatchSource`.
- Regras que leem o plano: SF-PLAN-001 e SF-PLAN-002 (`plan.python_udf`, por
  `attrs.udf_type`), SF-PLAN-003 (`plan.join`), SF-PLAN-004 (`plan.aqe`), SF-PQ-002 e
  SF-PQ-004 (`plan.file_scan`), lidas por `load_catalog`.

## Critérios

- AC1 a AC7 são sobre o extrator, o engine e a detecção; AC8 fecha o documento.
- U1 e U2 limitam a generalidade de AC1 à forma observada. O ship diz isso em vez de
  prometer.
