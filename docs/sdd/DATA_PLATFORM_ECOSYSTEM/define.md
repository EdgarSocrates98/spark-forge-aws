---
sdd: 1
feature: DATA_PLATFORM_ECOSYSTEM
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/DATA_PLATFORM_ECOSYSTEM/explore.md
  sha256: "877efd215e627f5f122066513b24c1b5ac497f59968fa30a40d408df95a0d9e1"
hypothesis:
  claim: "Um inventário com Connector Reliability Model oferece cobertura operacional comum para Serving, ingestão, CDC e AI Data Engineering."
  prediction: "O analisador preserva categoria/kind, ownership, bindings e controles de idempotência, checkpoint, retry, DLQ, rate limit, schema, freshness e recovery; ausências ficam unresolved."
  experiment: "Analisar fixture com Trino, ClickHouse, Airbyte, Debezium, Feast, vector index e radar opcional."
acceptance:
  - id: AC1
    statement: "O contrato normaliza sistemas das categorias serving, ingestion, ai e radar e registra Reliability Model por sistema."
    verified_by: {kind: test, ref: "tests/test_platform_ecosystem.py::test_ecosystem_normalizes_domains_and_reliability"}
  - id: AC2
    statement: "Radar Beam/DataHub/OpenMetadata permanece opcional e referências sem controle ou endpoint ficam unresolved."
    verified_by: {kind: test, ref: "tests/test_platform_ecosystem.py::test_ecosystem_preserves_unresolved_and_optional_radar"}
  - id: AC3
    statement: "CLI e MCP retornam o mesmo inventário estruturado."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli analyze platform-ecosystem --path fixtures/platform/ecosystem.yaml"}
success:
  - id: SC1
    metric: "Todos os sistemas possuem category, kind, owner e source_ref ou unresolved correspondente"
    source: "relatório do inventário"
out_of_scope:
  - "Instalar, provisionar ou consultar produtos de serving, connectors, feature store ou vector DB."
  - "Tratar radar opcional como dependência de runtime."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Registrar tool, referência e surface lock."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc]
---

# DATA_PLATFORM_ECOSYSTEM — requisitos

O mesmo sistema pode aparecer em mais de uma borda, mas seu `id` é único. O
reliability model é declarativo; ele não prova que o connector está saudável.
