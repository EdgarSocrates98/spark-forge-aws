---
sdd: 1
feature: ORCHESTRATION_CONTROL_PLANE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/ORCHESTRATION_CONTROL_PLANE/design.md
  sha256: "9c78e34d0c6e8ef02363feedbbac62910d4ab3710955b036b3945fc682a1ee86"
tasks:
  - id: T1
    files: [sparkforge_aws/orchestration/__init__.py, sparkforge_aws/orchestration/topology.py, fixtures/orchestration/control-plane.yaml, tests/test_orchestration.py]
    covers: [AC1, AC2]
    test: {path: tests/test_orchestration.py, name: test_orchestration_normalizes_reliability_controls}
  - id: T2
    files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, parity.yaml]
    covers: [AC3]
    test: {path: tests/test_orchestration.py, name: test_orchestration_surfaces_share_contract}
  - id: T3
    files: [docs/knowledge/orchestration-control-plane.md]
    covers: [AC2]
    test: {path: tests/test_orchestration.py, name: test_orchestration_knowledge_preserves_read_only_boundary}
---

# ORCHESTRATION_CONTROL_PLANE — plano

## T1 — topology

Implementar contrato Airflow/Dagster/Step Functions/Control-M e controles
operacionais declarados.

Commit: `feat(orchestration): add normalized control plane`

## T2 — superfícies

Expor CLI/MCP e parity.

Commit: `feat(orchestration): expose orchestration analysis`

## T3 — documentação

Documentar integração com analyzers existentes e Metadata Graph.

Commit: `docs(orchestration): document control plane contract`
