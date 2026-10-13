---
sdd: 1
feature: STREAMING_OPERATIONS_AND_SERVING
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_OPERATIONS_AND_SERVING/design.md
  sha256: "faae739ea87667319b6855770fc3a937f696a94d6ab78b3e8e9029173ff452af"
tasks:
  - {id: T1, files: [sparkforge_aws/facts/streaming_ops.py, tests/test_facts_streaming_ops.py], covers: [AC1, AC2], test: {path: tests/test_facts_streaming_ops.py, name: test_streaming_ops_redacts_secret_like_fields}}
  - {id: T2, files: [fixtures/streaming_ops, tests/test_fixtures_golden_streaming_ops.py], covers: [AC3], test: {path: tests/test_fixtures_golden_streaming_ops.py, name: test_streaming_ops_goldens}}
  - {id: T3, files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, tests/test_analyze_streaming_ops.py], covers: [AC4], test: {path: tests/test_analyze_streaming_ops.py, name: test_cli_and_mcp_envelopes_match}}
  - {id: T4, files: [rules/catalog/streaming-operations.yaml, tests/test_rules_catalog_reachability.py], covers: [AC3], test: {path: tests/test_rules_catalog_reachability.py, name: test_kind_exigido_tem_extrator_ou_a_regra_declara_blocked_on}}
  - {id: T5, files: [knowledge/streaming-operations.md, knowledge/streaming-format-serving-matrix.md, skills/review-streaming-operations/SKILL.md, agents/streaming-realtime-architect.md], covers: [AC5], test: {path: tests/test_analyze_streaming_ops.py, name: test_cli_and_mcp_envelopes_match}}
  - {id: T6, files: [docs/streaming/prompt-coverage.md, docs/superpowers/STATUS.md, README.md], covers: [AC5], test: {path: tests/test_docs_coverage.py, name: TestManifest::test_rule_count_equals_the_real_catalog}}
---

# STREAMING_OPERATIONS_AND_SERVING — plano

Implementar facts e testes, conectar adapters, julgar regras, sincronizar
artefatos gerados e só então fechar a cobertura do prompt.
