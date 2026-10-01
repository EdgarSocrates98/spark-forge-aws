---
sdd: 1
feature: LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION
phase: define
profile: dev
status: ready
hypothesis:
  claim: "A composição operacional do decision engine ainda pode fechar os requisitos executáveis do prompt sem criar uma nova superfície ou inferir evidência ausente."
  prediction: "Transições de migração adicionais, grafo de acesso Iceberg, observabilidade cross-account, preflight em camadas, dimensões de performance/FinOps e uma matriz explícita de aceite produzirão resultados estruturados; ausência de CloudTrail/RAM continuará unresolved."
  experiment: "Adicionar testes acceptance vermelhos, estender o núcleo offline, registrar a matriz de aceite e executar os gates de conhecimento, claims, referências, SDD e CI do PR."
acceptance:
  - id: AC1
    statement: "Migration report avalia Glue 4→5.0, Glue 4→5.1, Glue 5.0→5.1, Glue→EMR, EMR→release nova, FGAC→FTA e FTA→FGAC, sem inventar ganhos."
    guard: "A execução vermelha foi feita depois do primeiro incremento de implementação; o teste confirma a matriz final, enquanto a saída de migração anterior já tinha cobertura parcial."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_migration_report_covers_declared_transition_families"}
  - id: AC2
    statement: "Explain access distingue o caminho metadata/data, inclui Role e o caminho Iceberg Spark→Iceberg→GlueCatalog→Lake Formation→credentials→S3FileIO, e separa eventos CloudTrail de consumidor/produtor."
    guard: "O contrato de explain-access já tinha uma base operacional; o delta acrescenta as pernas Iceberg e observabilidade e mantém o teste como guarda de composição."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_access_graph_and_cross_account_observability_are_explicit"}
  - id: AC3
    statement: "Preflight valida RAM share/association/version, resource link somente quando a rota exige, credential vending, registro e operação read/write sem transformar ausência em falso."
    guard: "O preflight anterior já existia; o vermelho do delta expôs especificamente os estados active/associated/version e a rota explicit_catalog_id, que foram fechados aqui."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_preflight_is_layered_and_route_aware"}
  - id: AC4
    statement: "Performance/FinOps expõe security requirement, latency, resource overhead, worker requirements, runtime duration, DPUSeconds e cost basis como medidas condicionais."
    guard: "A camada performance_finops já tinha contrato de ausência de medição; o delta amplia as dimensões e o teste final é uma guarda de não-inferência."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_performance_finops_preserves_measurement_boundaries"}
  - id: AC5
    statement: "A saída publica decision graph bounded e progressive disclosure com dimensões engine/runtime/model/format/operation, sem carregar conhecimento de engine não relevante."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_decision_graph_is_bounded_and_version_aware"}
  - id: AC6
    statement: "Os cenários positivos e negativos mínimos de Glue, FTA e EMR do prompt são representados por casos declarativos, incluindo Parquet/Iceberg, IDs, RAM, GetDataAccess, KMS e conflito FGAC/FTA."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_scenario_matrix_has_positive_and_negative_cases"}
  - id: AC7
    statement: "A matriz de aceite do prompt aponta cada critério para implementação, teste e limite honesto, e a documentação/skill/VNX mantém a mesma semântica."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_acceptance_audit_is_complete"}
success:
  - id: SC1
    metric: "Acceptance AC1–AC7 verdes após vermelho próprio"
    source: "python -m pytest tests/test_lakeformation_prompt_acceptance.py -q"
  - id: SC2
    metric: "Gates declarados sem divergência"
    source: "sparkforge sdd check, verify_offline_bundle, check_surface_lock, check_vnext_claims, sync_skills --check"
  - id: SC3
    metric: "CI do PR de fechamento verde nas matrizes disponíveis"
    source: "gh pr checks"
out_of_scope:
  - "Chamadas AWS, mutações de IAM/Lake Formation/RAM/KMS/S3 ou simulação de policy."
  - "Claims numéricos de latency, workers, custo, tokens ou ganho sem runs medidos."
  - "Criar uma tool paralela para cada capítulo do prompt."
unknowns:
  - id: U1
    blocks: []
    unlock: "Coletar CloudTrail/Glue/Spark/RAM do caso real; sem esses artefatos o output permanece unresolved, mas o contrato offline é verificável."
change_kinds: [knowledge_doc, agent_or_skill, tool_or_verb, claims]
---

# LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION — requisitos

Este delta fecha lacunas executáveis que permaneceram depois de
`LAKE_FORMATION_OPERATIONAL_CLOSURE`: migração além de Glue 4/5, grafo de acesso
Iceberg, observabilidade cross-account, preflight de RAM/versionamento, dimensões
de FinOps/performance e auditoria explícita dos 26 critérios da seção 79 de
`prompt_evo_fgac_fta_espec.md`.

Fontes version-aware já registradas no knowledge bundle: AWS Glue FGAC/FTA e
migração 5.1/6.0, Lake Formation cross-account/hybrid/resource links, EMR FGAC/FTA
e Apache Iceberg GlueCatalog/S3FileIO. O delta não promove uma capacidade cuja
fonte oficial ou evidência do caso não fecha.
