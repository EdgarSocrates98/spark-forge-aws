---
sdd: 1
feature: STREAMING_OPERATIONS_AND_SERVING
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_OPERATIONS_AND_SERVING/plan.md
  sha256: "0f414e3818a6e787583f71f33c9db33ebe910d0ec978473d96689ba6d8f1b9fb"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_facts_streaming_ops.py -q", exit: 1}, green: {command: "python -m pytest tests/test_facts_streaming_ops.py -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_fixtures_golden_streaming_ops.py -q", exit: 1}, green: {command: "python -m pytest tests/test_fixtures_golden_streaming_ops.py -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_analyze_streaming_ops.py -q", exit: 1}, green: {command: "python -m pytest tests/test_analyze_streaming_ops.py -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python -m pytest tests/test_rules_catalog_reachability.py -q", exit: 1}, green: {command: "python -m pytest tests/test_rules_catalog_reachability.py -q", exit: 0}}
  - {id: T5, status: done, red: {command: "python scripts/sync_skills.py --check", exit: 1}, green: {command: "python scripts/sync_skills.py --check", exit: 0}}
  - {id: T6, status: done, red: {command: "python scripts/check_surface_lock.py", exit: 1}, green: {command: "python scripts/check_surface_lock.py", exit: 0}}
claims:
  - text: "Contrato completo preserva SLO, FinOps, segurança, serving e lakehouse sem preço calculado."
    evidence_ref: "tests/test_facts_streaming_ops.py::test_streaming_ops_preserves_declared_metrics_without_secret_values"
  - text: "Campo sensível nunca aparece em Fact e permanece como unresolved."
    evidence_ref: "tests/test_facts_streaming_ops.py::test_streaming_ops_redacts_secret_like_fields"
change_id: null
---

# STREAMING_OPERATIONS_AND_SERVING — relatório do build

Extrator, adapters, regras, fixtures e documentação formam uma camada
declarativa. Collectors live, benchmark e preço continuam fora do build.
