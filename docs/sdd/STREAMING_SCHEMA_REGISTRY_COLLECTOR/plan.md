---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY_COLLECTOR/design.md
  sha256: "cf559a166b743acec6902a069613c71e404b0ad45b386aa2c371a4e281e942ee"
tasks:
  - id: T1
    files: [tests/test_collect_schema_registry.py, sparkforge_aws/collect/schema_registry.py]
    covers: [AC1, AC2]
    test: {path: tests/test_collect_schema_registry.py, name: test_collector_paginates_and_preserves_schema_versions}
  - id: T2
    files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, parity.yaml, tests/test_collect_schema_registry.py]
    covers: [AC3]
    test: {path: tests/test_collect_schema_registry.py, name: test_cli_and_mcp_schema_registry_collection_match}
  - id: T3
    files: [knowledge/schema-registry-data-contracts.md, docs/guia/03-cli.md, docs/guia/04-mcp.md]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_collect_schema_registry.py, name: test_schema_registry_collection_docs_state_read_only_limits}
---

# STREAMING_SCHEMA_REGISTRY_COLLECTOR — plano

Implementação serializada: contrato de cliente falso e teste vermelho; módulo
read-only com paginação/cache; integração CLI/MCP/parity; documentação,
referências e gates. Nenhuma API de escrita será chamada.

## Sequência de commits

1. `feat(schema): add Glue Schema Registry read-only collector`
2. `feat(schema): expose schema registry collector adapters`
3. `docs(schema): document registry collector contract`
