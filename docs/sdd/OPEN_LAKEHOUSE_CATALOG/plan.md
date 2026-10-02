---
sdd: 1
feature: OPEN_LAKEHOUSE_CATALOG
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/OPEN_LAKEHOUSE_CATALOG/design.md
  sha256: "5582e2cc832d2e96c947f36d8a69ca421250076cc2a4f43237d7da16f541c212"
tasks:
  - id: T1
    files: [sparkforge/catalog/__init__.py, sparkforge/catalog/contract.py, contracts/lakehouse-catalog-v1.schema.json, fixtures/platform/catalog.yaml, tests/test_lakehouse_catalog.py]
    covers: [AC1]
    test: {path: tests/test_lakehouse_catalog.py, name: test_lakehouse_catalog_contract_is_deterministic}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, parity.yaml]
    covers: [AC2]
    test: {path: tests/test_lakehouse_catalog.py, name: test_lakehouse_catalog_cli_and_mcp_share_contract}
  - id: T3
    files: [docs/knowledge/open-lakehouse-catalog.md]
    covers: [AC2]
    test: {path: tests/test_lakehouse_catalog.py, name: test_lakehouse_catalog_knowledge_declares_unresolved_boundary}
---

# OPEN_LAKEHOUSE_CATALOG — plano

## T1 — contrato multi-engine

Implementar loader, sanitização de secrets, capabilities declaradas e fixture
Glue/Iceberg REST/Polaris/S3 Tables/Lake Formation com engines Spark/Flink/Trino/
Athena/DuckDB. Não executar testes nesta rodada.

Commit: `feat(catalog): add open lakehouse topology contract`

## T2 — superfície de análise

Adicionar CLI/MCP compartilhados e parity entry.

Commit: `feat(catalog): expose lakehouse catalog analysis`

## T3 — documentação

Documentar integração com Metadata Graph e limites de evidência.

Commit: `docs(catalog): document open lakehouse contract`
