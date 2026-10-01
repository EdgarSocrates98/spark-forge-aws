---
sdd: 1
feature: LAKE_FORMATION_PROMPT_GAP_AUDIT
phase: define
profile: dev
status: ready
hypothesis:
  claim: "A auditoria final do prompt ainda pode ser fechada com provas determinísticas adicionais, sem criar uma superfície paralela nem alterar o contrato evidence-first."
  prediction: "Casos explícitos para as combinações finais do prompt e um migration report estruturado tornarão verificáveis os gaps de cobertura sem transformar ausência de fonte em suporte."
  experiment: "Adicionar testes de regressão para o decision engine, ampliar os campos estruturados de migração e disclosure, atualizar runbooks/auditoria/VNX e executar os gates afetados."
acceptance:
  - id: AC1
    statement: "A matriz final cobre Glue FTA Parquet, Glue 4 DynamicFrame corrente, EMR Serverless cross-account com resource link, Hybrid cross-account, LF-TBAC/RAM, cross-account v5 e EMR 7.12 FGAC DML version-dependent."
    guard: "Regressão final da matriz: o focused acceptance agregado falhou antes do fechamento, mas não houve execução isolada deste node no estado anterior."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_final_knowledge_matrix_is_executable"}
  - id: AC2
    statement: "Os cinco gaps críticos permanecem travados por regressão: not_supported bloqueia, source/target são independentes, explicit_catalog_id não exige resource link, Hybrid IAMAllowedPrincipals é contextual e Glue 4 sem target não vira migration_required."
    guard: "Regressão de comportamento já corrigido na feature anterior; este teste impede que a auditoria final relaxe o fail-closed."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_critical_gap_regressions"}
  - id: AC3
    statement: "Migration report publica seções estruturadas para runtime, Spark, Python, Iceberg, Lake Formation, DynamicFrame, FGAC/FTA, cross-account, routing, RAM, IDs, código, Terraform, IAM/LF, testes e rollback."
    guard: "O contrato foi introduzido no núcleo anterior; esta aceitação protege o shape contra regressão futura."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_migration_report_has_prompt_sections"}
  - id: AC4
    statement: "Progressive disclosure carrega referência de runtime relevante para EMR e não carrega a referência específica de Glue em um caso EMR."
    guard: "Guarda de regressão da seleção de conhecimento por engine; o focused acceptance atual prova o contrato completo."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_decision_graph_is_bounded_and_version_aware"}
  - id: AC5
    statement: "Runbooks e auditoria documentam os gaps fechados sem alegar execução AWS ou ganho não medido."
    guard: "Guarda documental: o teste deve continuar passando após regenerar mirrors e referências."
    verified_by: {kind: test, ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_acceptance_audit_is_complete"}
success:
  - id: SC1
    metric: "AC1–AC5 verdes na suíte focused"
    source: "pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q"
  - id: SC2
    metric: "SDD, offline, skills, surface, claims e status gates sem divergência"
    source: "sparkforge sdd check; verify_offline_bundle; sync_skills --check; check_surface_lock; check_status_numbers --strict"
out_of_scope:
  - "Chamadas ou mutações AWS, IAM, Lake Formation, RAM, KMS ou S3."
  - "Alterar a matriz de capability sem nova fonte oficial versionada."
  - "Reexecutar o lote completo já validado pelo CI do PR anterior."
unknowns:
  - id: U1
    blocks: []
    unlock: "Coleta de fatos do ambiente real; a prova offline continua explicitamente limitada sem esses fatos."
change_kinds: [knowledge_doc, agent_or_skill, claims]
---

# LAKE_FORMATION_PROMPT_GAP_AUDIT — requisitos

Esta feature não reabre a arquitetura já shipada. Ela fecha a auditoria de
cobertura da seção 66–79 de `prompt_evo_fgac_fta_espec.md`: combinações de
runtime/modelo/formato/rota que ainda estavam apenas implícitas, regressões dos
cinco gaps críticos e o formato operacional do migration report.

O contrato permanece offline, version-aware e evidence-first. O status
`consistent` significa apenas que a declaração e as evidências fornecidas não
deixaram lacuna no contrato; não significa que acesso AWS foi executado.
