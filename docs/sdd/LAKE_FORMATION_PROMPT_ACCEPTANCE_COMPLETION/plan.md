---
sdd: 1
feature: LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/design.md
  sha256: "35e4d2d810ad9701794f3af1e5ea9b3b76ed624c7f02e40b65ff8a892218d58f"
tasks:
  - id: T1
    files: [tests/test_lakeformation_prompt_acceptance.py, sparkforge_aws/lakeformation/architecture.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_migration_report_covers_declared_transition_families}
  - id: T2
    files: [tests/test_lakeformation_prompt_acceptance.py, sparkforge_aws/lakeformation/architecture.py]
    covers: [AC4, AC5, AC6]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_access_graph_and_cross_account_observability_are_explicit}
  - id: T3
    files: [tests/test_lakeformation_prompt_acceptance.py, knowledge/lakeformation/operational-closure.md, docs/guia/usos/lake-formation-operacional.md, skills/lakeformation-architecture/SKILL.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CAPABILITY-MATRIX.md, docs/vnext/KNOWLEDGE-MAP.md, docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/prompt-acceptance-audit.md]
    covers: [AC7]
    test: {path: tests/test_lakeformation_prompt_acceptance.py, name: test_prompt_acceptance_audit_is_complete}
---

# LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION — plano

## T1 — migração, acesso e preflight

Escrever os testes de transição, access graph e preflight antes de alterar
`architecture.py`. Cada transição deve retornar família nomeada, plano de teste e
rollback; cada camada ausente deve permanecer unresolved. Rodar os testes focados
e `ruff` até verde. Commit: `feat(lakeformation): complete prompt transition and access contracts`.

## T2 — observabilidade, FinOps, decision graph e cenários

Adicionar observabilidade declarativa para CloudTrail consumer/producer, dimensões
de performance/FinOps e graph bounded. Cobrir cenários positivos/negativos do
prompt sem simular AWS e sem `Action: "*"`. Rodar focused suite, offline bundle e
claims. Commit: `feat(lakeformation): expose bounded evidence and measurement review`.

## T3 — auditoria e documentação

Criar a matriz de aceite com todos os 26 itens da seção 79, atualizar knowledge,
runbook, skill e VNX, regenerar referências/espelhos e rodar gates. Commit:
`docs(lakeformation): publish prompt acceptance audit`.
