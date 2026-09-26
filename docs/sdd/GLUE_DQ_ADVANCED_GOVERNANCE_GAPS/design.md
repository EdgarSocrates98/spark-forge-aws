---
sdd: 1
feature: GLUE_DQ_ADVANCED_GOVERNANCE_GAPS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/GLUE_DQ_ADVANCED_GOVERNANCE_GAPS/define.md
  sha256: "b2b2d976c7e3c8652d1c078603f13d9a2f3c0421d01a710632282b1ece6be7d2"
files:
  - {path: sparkforge/facts/glue_dq_advanced.py, action: modify, reason: "normalizar sampling/geography/authorization/risk e manter rejeição de rows"}
  - {path: sparkforge/dq_ai/assessment.py, action: modify, reason: "derivar statuses e unresolved reasons"}
  - {path: sparkforge/reporting/dq_ai.py, action: modify, reason: "projetar evidência, claims e contexto de risco"}
  - {path: knowledge/glue/dq-advanced-matrix.yaml, action: modify, reason: "documentar defaults e claims com status documental"}
  - {path: knowledge/glue/dq-advanced-matrix.md, action: modify, reason: "explicar fronteira observada/documentada"}
  - {path: rules/catalog/data-quality-ai.yaml, action: modify, reason: "adicionar SF-DQ-AI-006..008"}
  - {path: manifest.json, action: modify, reason: "atualizar contagem manual do catálogo após três regras novas"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "registrar hash do documento de knowledge alterado"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "sincronizar watchlist das fontes de regras/knowledge"}
  - {path: fixtures/dq_ai/advanced_controls_complete/input/recommendation.json, action: create, reason: "golden de sampling/autorização completa"}
  - {path: fixtures/dq_ai/advanced_controls_complete/meta.yaml, action: create, reason: "declara kinds/rules do golden completo"}
  - {path: fixtures/dq_ai/advanced_controls_complete/expected/facts.json, action: create, reason: "golden facts do cenário completo"}
  - {path: fixtures/dq_ai/advanced_controls_complete/expected/findings.json, action: create, reason: "golden findings do cenário completo"}
  - {path: fixtures/dq_ai/geographic_boundary_unresolved/input/recommendation.json, action: create, reason: "golden de Region cross sem geografia"}
  - {path: fixtures/dq_ai/geographic_boundary_unresolved/meta.yaml, action: create, reason: "declara kinds/rules do golden de blind spot"}
  - {path: fixtures/dq_ai/geographic_boundary_unresolved/expected/facts.json, action: create, reason: "golden facts do blind spot"}
  - {path: fixtures/dq_ai/geographic_boundary_unresolved/expected/findings.json, action: create, reason: "golden findings do blind spot"}
  - {path: fixtures/dq_ai/authorization_incomplete/input/recommendation.json, action: create, reason: "golden de cadeia de autorização incompleta"}
  - {path: fixtures/dq_ai/authorization_incomplete/meta.yaml, action: create, reason: "declara kinds/rules da autorização"}
  - {path: fixtures/dq_ai/authorization_incomplete/expected/facts.json, action: create, reason: "golden facts da autorização"}
  - {path: fixtures/dq_ai/authorization_incomplete/expected/findings.json, action: create, reason: "golden findings da autorização"}
  - {path: fixtures/dq_ai/risk_context/input/recommendation.json, action: create, reason: "golden de Iceberg/residência/variabilidade"}
  - {path: fixtures/dq_ai/risk_context/meta.yaml, action: create, reason: "declara kinds/rules do contexto de risco"}
  - {path: fixtures/dq_ai/risk_context/expected/facts.json, action: create, reason: "golden facts de risco"}
  - {path: fixtures/dq_ai/risk_context/expected/findings.json, action: create, reason: "golden findings de risco"}
  - {path: tests/test_dq_ai_unit.py, action: modify, reason: "testar normalização e geografia"}
  - {path: tests/test_dq_ai_security.py, action: modify, reason: "testar autorização e boundary offline"}
  - {path: tests/test_dq_ai_report.py, action: modify, reason: "testar projeções de claims/contexto"}
  - {path: tests/test_fixtures_golden_dq_ai.py, action: modify, reason: "cobrir novos goldens no runner existente"}
decisions:
  - id: D1
    choice: "Matriz guarda default AWS como documented_reference; assessment só chama valor observado quando manifesto o declara."
    rejected: ["Preencher omissões com default, pois isso fabrica evidência", "Ignorar controles, pois preserva lacuna sem ação"]
    rollback: "git revert do commit que altera matriz/extrator/assessment; remover fixtures novas e restaurar campos anteriores."
  - id: D2
    choice: "Region relation e geographic boundary são eixos independentes com estados approved/disallowed/unresolved."
    rejected: ["Usar cross_region como proxy geográfico, pois mistura relação e política", "Inferir geography por prefixo de Region, pois não é uma observação declarada"]
    rollback: "git revert do commit das regras SF-DQ-AI-007 e campos geográficos; SF-DQ-AI-002 permanece com semântica anterior."
  - id: D3
    choice: "Autorização exige KMS agregado mais key policy, runtime role e Lake Formation como evidências independentes."
    rejected: ["Simular provider dentro do extrator, pois viola offline core", "Aceitar kms.status como prova completa, pois oculta camadas ausentes"]
    rollback: "git revert do commit de SF-DQ-AI-008 e dos campos de autorização; manter KMS agregado anterior."
  - id: D4
    choice: "Risco de residência/Iceberg/migração e variabilidade ficam em contexto qualitativo; revisão existente continua enforcement."
    rejected: ["Publicar score numérico sem runs comparáveis", "Criar finding sempre ativo para ADVANCED, pois duplicaria SF-DQ-AI-004"]
    rollback: "git revert da projeção de contexto e remover somente campos opcionais; nenhuma regra existente muda."
covers:
  - {part: sampling-status, acceptance: [AC1]}
  - {part: geographic-status, acceptance: [AC2]}
  - {part: authorization-status, acceptance: [AC3]}
  - {part: report-context, acceptance: [AC4]}
  - {part: golden-boundary, acceptance: [AC5]}
---

# GLUE_DQ_ADVANCED_GOVERNANCE_GAPS — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| sampling-status | extractor, assessment, matrix, rule 006 | AC1 |
| geographic-status | extractor, assessment, rule 007 | AC2 |
| authorization-status | extractor, assessment, report, rule 008 | AC3 |
| report-context | matrix, report, unit/security tests | AC4 |
| golden-boundary | fixtures e testes golden | AC5 |

## Conhecimento consultado

- AgentSpec KB `data-quality` (contracts, observability, schema-validation, data-contract-authoring): contrato explícito, unresolved e observabilidade de drift.
- AgentSpec KB `lakehouse` (iceberg-v3, iceberg-operations): contexto Iceberg e manutenção não devem ser inferidos do manifesto DQ.
- AgentSpec KB `terraform` (providers, iam-module): provider/IAM é fonte externa; sem credenciais hardcoded e sem mutação neste fluxo.
- AgentSpec KB `testing` (fixtures) e `python/file-parser`: fixtures isoladas, parser metadata-only.
- Projeto: `knowledge/glue/dq-advanced-matrix.yaml`, `rules/catalog/data-quality-ai.yaml`, `docs/gates-por-mudanca.md` e fontes AWS já lockadas.
