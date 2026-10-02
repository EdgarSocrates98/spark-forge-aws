---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_EVALUATION/design.md
  sha256: "b4e21f02b43722dbfffdff465b917784a1036fbc4dda24d9f6a689c71107dd11"
tasks:
  - id: T1
    files: [tests/test_facts_streaming_slo.py, sparkforge/facts/streaming_slo.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_streaming_slo.py, name: test_evaluates_direct_progress_metric}
  - id: T2
    files: [tests/test_streaming_rules.py, rules/catalog/streaming-operations.yaml]
    covers: [AC4]
    test: {path: tests/test_streaming_rules.py, name: test_slo_evaluation_rules_are_evidence_first}
  - id: T3
    files: [sparkforge/facts/streaming_composition.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_streaming_composition.py]
    covers: [AC5]
    test: {path: tests/test_analyze_streaming_composition.py, name: test_slo_cli_and_mcp_envelopes_match}
  - id: T4
    files: [fixtures/streaming_composition, tests/test_fixtures_golden_streaming_composition.py, tests/test_fixtures_kind_coverage.py, tests/test_rules_catalog_reachability.py]
    covers: [AC6]
    test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_goldens}
  - id: T5
    files: [skills/analyze-streaming-composition/SKILL.md, knowledge/streaming-operations.md, docs/streaming/prompt-coverage.md]
    covers: [AC7]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_coverage_mentions_slo_evaluation}
  - id: T6
    files: [docs/surface.lock.json, knowledge/offline-manifest.json, docs/superpowers/STATUS.md]
    covers: [AC7]
    test: {path: tests/test_surface_lock.py, name: test_surface_lock_is_current}
---

# STREAMING_SLO_EVALUATION — plano

Executar em ordem T1–T2–T3–T4–T5–T6. T1 escreve testes vermelhos para
comparação, cobertura temporal e unresolved antes do compositor. T2 fecha judge
com regras evidence-first. T3 conecta o mesmo core a CLI/MCP. T4 cria goldens e
registra os kinds derivados nas duas listas manuais. T5–T6 atualizam documentação
e registries gerados. A suíte completa fica fora desta fase; somente gates
direcionados são rodados até o fechamento do prompt.
