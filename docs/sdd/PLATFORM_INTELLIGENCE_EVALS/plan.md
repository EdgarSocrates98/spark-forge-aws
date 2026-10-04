---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_EVALS/design.md
  sha256: "f22c075a6dee37613244dfa552abb4d6cd0843ccb1e1c69fbade59eebeefe120"
tasks:
  - id: T1
    files: [evals/platform_intelligence/suite.yaml, scripts/check_platform_eval_contract.py, tests/test_platform_evals.py]
    covers: [AC1, AC2]
    test: {path: tests/test_platform_evals.py, name: test_platform_eval_contract_has_quality_and_economy_axes}
  - id: T2
    files: [docs/knowledge/platform-intelligence-evals.md]
    covers: [AC1]
    test: {path: tests/test_platform_evals.py, name: test_platform_eval_knowledge_separates_tokens_and_bytes}
---

# PLATFORM_INTELLIGENCE_EVALS — plano

## T1 — contrato e checker

Criar suite seed com casos graph/lab/catalog/dbt/observability/orchestration/
ecosystem e validador offline.

Commit: `feat(evals): add platform intelligence eval contract`

## T2 — política

Documentar expansão para corpus real, holdout e economia observável.

Commit: `docs(evals): document platform intelligence evaluation policy`
