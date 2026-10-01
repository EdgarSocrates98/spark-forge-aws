---
sdd: 1
feature: GLUE_DQ_ADVANCED_GOVERNANCE_GAPS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/GLUE_DQ_ADVANCED_GOVERNANCE_GAPS/design.md
  sha256: "700969e0144189e849eb189053054d40e52e02d593216668aeccab4cf3e8b0e3"
tasks:
  - id: T1
    files: [tests/test_dq_ai_unit.py, sparkforge/facts/glue_dq_advanced.py, sparkforge/dq_ai/assessment.py, knowledge/glue/dq-advanced-matrix.yaml]
    covers: [AC1, AC2]
    test: {path: tests/test_dq_ai_unit.py, name: test_sampling_controls_keep_documented_defaults_unobserved}
  - id: T2
    files: [tests/test_dq_ai_security.py, sparkforge/facts/glue_dq_advanced.py, sparkforge/dq_ai/assessment.py, rules/catalog/data-quality-ai.yaml]
    covers: [AC3]
    test: {path: tests/test_dq_ai_security.py, name: test_authorization_requires_all_external_evidence_parts}
  - id: T3
    files: [knowledge/glue/dq-advanced-matrix.yaml, knowledge/glue/dq-advanced-matrix.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, rules/catalog/data-quality-ai.yaml, manifest.json, sparkforge/reporting/dq_ai.py]
    covers: [AC4]
    test: {path: tests/test_dq_ai_report.py, name: test_report_exposes_documented_claims_and_risk_context}
  - id: T4
    files: [fixtures/dq_ai/advanced_controls_complete/input/recommendation.json, fixtures/dq_ai/advanced_controls_complete/meta.yaml, fixtures/dq_ai/advanced_controls_complete/expected/facts.json, fixtures/dq_ai/advanced_controls_complete/expected/findings.json, fixtures/dq_ai/geographic_boundary_unresolved/input/recommendation.json, fixtures/dq_ai/geographic_boundary_unresolved/meta.yaml, fixtures/dq_ai/geographic_boundary_unresolved/expected/facts.json, fixtures/dq_ai/geographic_boundary_unresolved/expected/findings.json, fixtures/dq_ai/authorization_incomplete/input/recommendation.json, fixtures/dq_ai/authorization_incomplete/meta.yaml, fixtures/dq_ai/authorization_incomplete/expected/facts.json, fixtures/dq_ai/authorization_incomplete/expected/findings.json, fixtures/dq_ai/risk_context/input/recommendation.json, fixtures/dq_ai/risk_context/meta.yaml, fixtures/dq_ai/risk_context/expected/facts.json, fixtures/dq_ai/risk_context/expected/findings.json, tests/test_fixtures_golden_dq_ai.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_dq_ai.py, name: test_every_dq_ai_fixture_matches_declared_kinds_and_rules}
---

# GLUE_DQ_ADVANCED_GOVERNANCE_GAPS — plano

## T1 — statuses de sampling e geografia

Teste primeiro em `tests/test_dq_ai_unit.py`: declarar workgroup, bucket, retenção, source/inference Region e ausência de geography; afirmar `sampling_controls_status`, `documented_not_observed`, `cross_region` e `geographic_boundary_status`.

Rodar:

```bash
python -m pytest tests/test_dq_ai_unit.py::test_sampling_controls_keep_documented_defaults_unobserved tests/test_dq_ai_unit.py::test_geographic_boundary_is_distinct_from_cross_region -q
```

Falha esperada: `KeyError`/`AssertionError` nos campos que ainda não existem. Implementar parser e assessment mínimos; rodar o mesmo comando verde. Gates: `tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py`.

Commit: `feat: expose Glue DQ sampling and geography gaps`.

## T2 — cadeia de autorização

Teste primeiro em `tests/test_dq_ai_security.py`: payload advanced com `kms.status` suficiente, mas key policy, runtime role e Lake Formation ausentes; afirmar status agregado e finding `SF-DQ-AI-008`, mantendo `provider_calls=0`.

Rodar:

```bash
python -m pytest tests/test_dq_ai_security.py::test_authorization_requires_all_external_evidence_parts -q
```

Falha esperada: `AssertionError` porque o assessment não expõe os três componentes. Implementar normalização/composição sem provider. Rodar o mesmo comando verde. Gates: `tests/test_rules_loader.py tests/test_rules_engine.py tests/test_rules_catalog_reachability.py`.

Commit: `feat: require complete Glue DQ authorization evidence`.

## T3 — claims, risco e regras

Teste primeiro em `tests/test_dq_ai_report.py`: payload com `risk.residency_required`, `iceberg.format_version`, `migration_risk` e sem default observado; afirmar claims documentais/status, variabilidade qualitativa e views sem score numérico. Adicionar regras 006–008 com actions fechadas e atualizar matriz/docs.

Rodar:

```bash
python -m pytest tests/test_dq_ai_report.py::test_report_exposes_documented_claims_and_risk_context -q
```

Falha esperada: `KeyError`/`AssertionError` nos campos de report. Implementar projeções e catálogo. Rodar o mesmo comando verde. Gates: `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q`; `python -m pytest tests/test_offline_expansion.py -q`; `python scripts/verify_offline_bundle.py`.

Commit: `feat: add Glue DQ gap rules and risk report context`.

## T4 — goldens e fronteira final

Teste primeiro usando o runner existente; adicionar quatro fixtures metadata-only com cenários completo, geography unresolved, authorization incomplete e risk context. Gerar expected pelo runner/regenerador do projeto, nunca à mão; afirmar que cada nova regra tem golden e rows continuam recusados.

Rodar:

```bash
python -m pytest tests/test_fixtures_golden_dq_ai.py::test_every_dq_ai_fixture_matches_declared_kinds_and_rules -q
```

Falha esperada: diretórios/expected ausentes ou regras novas sem golden. Implementar fixtures e registros correspondentes; rodar o mesmo comando verde. Gates: `python -m pytest tests/test_dq_ai_unit.py tests/test_dq_ai_security.py tests/test_dq_ai_report.py tests/test_fixtures_golden_dq_ai.py -q`; `python scripts/verify_wheel.py`.

Commit: `test: cover Glue DQ governance gap scenarios`.
