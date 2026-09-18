---
sdd: 1
feature: DATABRICKS_SPARK
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/DATABRICKS_SPARK/build_report.md
  sha256: "4b72e4b781d5024aa953548b61fbb129872c1f66013bd92017a1ec9a4b73faa7"
hypothesis_outcome: confirmed
registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage, runtime_scope_gates, reachability_lists, snippet_measure, offline_manifest, sources_lock, fixture_corpus_gates, surface_lock, generated_reference, claims_gate]
deviations:
  - "Ordem de execucao T1, T2, T4, T5, T9, T3, T6, T7, T8, T10, para encurtar o vermelho de tests/test_capability_parity.py, que exige flag, flag MCP e produtor para todo eixo de RuntimeContext."
  - "Arquivos fora do manifesto do design: tests/test_runtime_matrix_drift.py (guard de drift da matriz), tests/test_capability_parity.py (AXES_DECLARED_ONLY para photon), tests/test_fixtures_golden_mcp_parity.py (contrato MCP congelado), tests/test_runtime_inferred_from_facts.py, tests/test_reporting_github.py, sparkforge/reporting/locate.py, knowledge/INDEX.md, docs/gates-por-mudanca.md, e os goldens de fixtures/simulate, fixtures/scenarios, evals/holdout, fixtures/change, fixtures/timeout, fixtures/dq, fixtures/iceberg, fixtures/s3, fixtures/graph, fixtures/funcval, fixtures/exception, fixtures/migration, fixtures/receipt, fixtures/iam_access."
  - "Tabela da matriz no documento ganhou coluna LTS propria, para a chave ser igual a do YAML sem mexer no mecanismo compartilhado do guard de drift."
  - "databricks e photon ficaram fora de required no schema MCP de saida do runtime: o golden MCP e congelado e so aceita mudanca aditiva."
  - "Photon on nao recusa regra que so exige plan.python_udf: o no ArrowEvalPython continua no plano (observado em Databricks Free Edition, 2026-09-18)."
  - "Photon declarado sem a plataforma databricks vira divergencia photon: em vez de ficar no contexto."
  - "--photon com choices on/off em todos os verbos, inclusive os lacos genericos de proof, simulate e scan."
  - "Porta de producao ligada por decisao do operador: todo verbo que julga passa a julgar os facts de ambiente da deteccao de runtime (SF-ENV-001, 004, 005 e 006 em producao); o scan grava esses facts no facts.json."
  - "Auditoria de remediacao: sem diferenciar caixa, sobre todo extrator com EMITTED_KINDS menos exclusoes nomeadas, pulando so regra com eixo de plataforma AWS, e conferindo cada passo de proposed_change e validation. 13 regras reescritas no plano, mais 15 e 6 nas rodadas de revisao."
  - "O guard de drift e a defesa de locate.py foram achados das revisoes, nao do plano."
  - "Tarefas T3, T6, T8 e T10 revisadas pelo controlador sobre o diff, sem subagente revisor proprio; T4, T5, T7 e T9 com spec e qualidade num subagente so, em sequencia."
  - "Suite apos a rodada R2: oito lotes rodaram antes de o processo ser parado por falta de memoria na maquina; o nono (g-z) rodou de novo depois do conserto de locate.py."
---

# DATABRICKS_SPARK — entrega

## Hipótese

Confirmada. A afirmação do define era que o extrator de event log e as regras sem
`runtime_scope` julgam um job Spark no Databricks sem extrator novo de execução,
desde que plataforma e runtime sejam declarados e a fronteira recuse com nome em vez
de julgar.

As três partes da previsão foram medidas:

- **Par Glue/Databricks.** Na fixture `databricks_skewed_stage`, par de
  `skewed_stage`, as seis regras spark-ui disparam iguais, com a mesma severidade e o
  mesmo sujeito (`tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros`).
- **Sem remediação só de AWS.** A auditoria (`tests/test_databricks_rule_audit.py`)
  recalcula o conjunto de regras que um job Databricks alcança e exige que termo de AWS
  venha ao lado de Databricks, por regra e por passo. Única exceção nomeada: SF-PQ-002.
- **Photon.** Com Photon declarado `on`, as regras de plano saem em `skipped` com
  `databricks.photon.unresolved`
  (`tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano`). A exceção
  das regras que só exigem `plan.python_udf` veio de observação e está nos desvios.

A observação em Databricks Free Edition reforça a fronteira em vez de enfraquecê-la.
Num plano Photon, o extrator de plano emite só `plan.analyzed` e `plan.aqe`, sem
`plan.join`, sem `plan.exchange` e sem `plan.unresolved`: julgar esse plano sem a
recusa seria o silêncio que a feature existe para evitar
(`knowledge/databricks/runtime-matrix.md` §4).

## Comandos de aceite (`kind: command`)

| critério | comando | exit |
|---|---|---|
| AC9 | `python scripts/check_surface_lock.py` | 0 (`0 divergencia(s).`) |

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| `rules_catalog_gates`, `manifest_rule_count`, `fixture_kind_coverage`, `reachability_lists` | `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py -q` | 1144 passed |
| `runtime_scope_gates` | `python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q` | 715 passed |
| `snippet_measure` | `python -m pytest tests/test_harness_untrusted.py -q` | 4 passed |
| `fixture_corpus_gates` | `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q` | 89 passed |
| `offline_manifest` | `python -m pytest tests/test_offline_expansion.py -q` e `python scripts/verify_offline_bundle.py` | 4 passed; bundle ok |
| `sources_lock` | `python scripts/refresh_knowledge.py --update --offline` | sincronizado, sem diferença |
| `generated_reference` | `python scripts/gen_reference_docs.py` e `python -m pytest tests/test_reference_docs.py -q` | 268 páginas, 0 regravadas; 5 passed |
| `surface_lock` | `python scripts/check_surface_lock.py` | 0 divergências |
| `claims_gate` | `python scripts/check_vnext_claims.py` e `python -m pytest tests/test_vnext_claims.py tests/test_docs_coverage.py tests/test_installed_provenance.py -q` | 0 divergências; 174 passed |
| números correntes | `python scripts/check_status_numbers.py --strict` | 0 divergências |

A suíte rodou nos nove lotes de `tests/test_suite_batches.py` depois da rodada R1 e
de novo depois da R2 (o lote `g-z` repetido depois do conserto de `locate.py`: 5439
passed). O único vermelho, nos dois ciclos, é
`tests/test_arvore_versionada.py::test_espelho_gerado_esta_em_dia_no_disco`, causado
por `.claude/agents/README.md`, não rastreado de propósito e fora desta feature.

## Pendências

- **U1.** A presença de `spark.databricks.clusterUsageTags.sparkVersion` num event
  log real de cluster clássico continua sem observação; no serverless a chave não é
  legível por `spark.conf` e não há event log entregue.
- **U2, metade do event log.** Photon é visível no texto do plano; como aparece no
  event log continua sem observação.
- **Extrator de plano sob Photon.** Não reconhece operadores `Photon*` (fica calado) e
  rotula um `@F.udf` comum como `udf_type: "pandas"` quando o plano traz
  `ArrowEvalPython`. Feature seguinte proposta: DATABRICKS_PHOTON_PLAN.
- **Fora desta entrega, registrados na revisão final:** texto de agentes e skills
  citando Databricks (M7), a pista `-photon-` do rótulo legado de `spark_version`
  (M10), `User` e `spark.master` com cara de Glue na fixture pareada (M11), e
  `scripts/regen_fixtures.py` sem `regen_timeout` para `fixtures/timeout`.
- **Fora do escopo por definição:** `_delta_log`, Jobs API, billing em DBU e coleta
  pela REST API.
- **Achados fora da feature:** o arquivo vazio rastreado `tuple[dict[str` na raiz,
  vindo do commit `749d44b9`.

## Lições

- A revisão final do diff inteiro achou o que a revisão por tarefa não achava: a
  regra SF-ENV-006 não tinha porta de produção, e só a leitura dos verbos de ponta a
  ponta mostrou isso. Tarefa que acrescenta regra sobre fact derivado deve incluir um
  teste que passe pelo verbo público (`judge`), não só pelo `detect_runtime`.
- A auditoria de texto por substring sensível a maiúsculas deixou passar `glue.*` e
  regras escopadas só por `spark`; o critério certo sai do mesmo conjunto que decide a
  alcançabilidade, e precisa conferir passo a passo.
- Uma observação de dez minutos numa conta gratuita mudou três decisões (UDF fora da
  recusa, `auto` como valor presente no serverless, extrator calado sob Photon).
  Lacuna com `unlock` que custa pouco deve ser destravada antes do build, não depois.
