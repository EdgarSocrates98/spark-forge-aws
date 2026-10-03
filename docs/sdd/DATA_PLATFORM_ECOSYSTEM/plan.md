---
sdd: 1
feature: DATA_PLATFORM_ECOSYSTEM
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/DATA_PLATFORM_ECOSYSTEM/design.md
  sha256: "495de29d55ab3cd16df6b0ab2b5a7aeb5519e6afef13202217cb58bb6f7f53bb"
tasks:
  - id: T1
    files: [sparkforge/platform/ecosystem.py, sparkforge/platform/__init__.py, fixtures/platform/ecosystem.yaml, tests/test_platform_ecosystem.py]
    covers: [AC1, AC2]
    test: {path: tests/test_platform_ecosystem.py, name: test_ecosystem_normalizes_domains_and_reliability}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, parity.yaml]
    covers: [AC3]
    test: {path: tests/test_platform_ecosystem.py, name: test_ecosystem_surfaces_share_contract}
  - id: T3
    files: [docs/knowledge/data-platform-ecosystem.md]
    covers: [AC2]
    test: {path: tests/test_platform_ecosystem.py, name: test_ecosystem_knowledge_marks_radar_optional}
---

# DATA_PLATFORM_ECOSYSTEM — plano

## T1 — inventory/reliability

Implementar contrato e fixture representativa.

Commit: `feat(platform): add data platform ecosystem inventory`

## T2 — superfícies

Adicionar CLI/MCP e parity.

Commit: `feat(platform): expose ecosystem analysis`

## T3 — conhecimento

Documentar serving, connectors, AI Data Engineering e radar.

Commit: `docs(platform): document ecosystem inventory`
