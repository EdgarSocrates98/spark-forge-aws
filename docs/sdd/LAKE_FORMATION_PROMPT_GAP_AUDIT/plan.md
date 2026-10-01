---
sdd: 1
feature: LAKE_FORMATION_PROMPT_GAP_AUDIT
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/design.md
  sha256: "9e24964e297833208de02f663695afe5dc9b66530ca80f7f59a16b6617a5027a"
tasks:
  - id: T1
    files: [tests/test_lakeformation_prompt_acceptance.py]
    covers: [AC1, AC2, AC4]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_prompt_final_knowledge_matrix_is_executable}
  - id: T2
    files: [sparkforge/lakeformation/architecture.py, tests/test_lakeformation_prompt_acceptance.py]
    covers: [AC3]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_migration_report_has_prompt_sections}
  - id: T3
    files: [knowledge/lakeformation/operational-closure.md, docs/guia/usos/lake-formation-operacional.md, skills/lakeformation-architecture/SKILL.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CAPABILITY-MATRIX.md, docs/vnext/KNOWLEDGE-MAP.md, docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/prompt-acceptance-audit.md, tests/test_lakeformation_prompt_acceptance.py]
    covers: [AC5]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_prompt_acceptance_audit_is_complete}
---

# LAKE_FORMATION_PROMPT_GAP_AUDIT — plano

## T1 — matriz final e regressões

Adicionar casos explicitamente versionados para cada combinação final e travar
os cinco gaps destacados. Rodar vermelho antes de qualquer alteração de
produção; depois rodar focused acceptance.

## T2 — migration report e disclosure

Adicionar `review.migration.sections` com dimensões do prompt e referência de
runtime EMR no progressive disclosure. Preservar campos legados e estados
`required`, `version_dependent`, `not_requested` e `unresolved`.

## T3 — documentação e gates

Atualizar runbooks, VNX e auditoria, regenerar skill mirrors se necessário e
executar gates de conhecimento, SDD, offline, claims, superfície, skills e
status. O lote completo fica delegado ao CI já em execução/validado pelo
histórico, conforme escopo do usuário.
