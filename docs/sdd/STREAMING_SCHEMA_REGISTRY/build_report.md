---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY/plan.md
  sha256: "b440a1f4062e7542026c42d24c0d9dd251047a7703bde2e2d5e64f39d9e773c1"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_facts_schema_registry.py -q", exit: 1}, green: {command: "python -m pytest tests/test_facts_schema_registry.py -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_schema_registry_rules.py tests/test_fixtures_golden_schema_registry.py -q", exit: 1}, green: {command: "python -m pytest tests/test_schema_registry_rules.py tests/test_fixtures_golden_schema_registry.py -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_analyze_schema_registry.py -q", exit: 1}, green: {command: "python -m pytest tests/test_analyze_schema_registry.py -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python scripts/sync_skills.py --check", exit: 1}, green: {command: "python scripts/sync_skills.py --check; python scripts/check_surface_lock.py", exit: 0}}
claims:
  - {text: "O diff estrutural separa compatibilidade observada de prova end-to-end.", evidence_ref: "tests/test_facts_schema_registry.py::test_schema_registry_extracts_diff_and_unresolved_policy"}
  - {text: "Cada kind e regra Schema Registry tem golden.", evidence_ref: "tests/test_fixtures_golden_schema_registry.py::test_schema_registry_fixture_goldens"}
  - {text: "CLI e MCP compartilham envelope read-only.", evidence_ref: "tests/test_analyze_schema_registry.py::test_cli_and_mcp_schema_registry_envelopes_match"}
---

# STREAMING_SCHEMA_REGISTRY — build report

Implementação offline concluída com fixtures/goldens, rules, CLI/MCP e skill.
As verificações e eventuais reds serão registradas pelo executor na entrega.
