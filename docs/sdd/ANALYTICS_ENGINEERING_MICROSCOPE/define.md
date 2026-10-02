---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/ANALYTICS_ENGINEERING_MICROSCOPE/explore.md
  sha256: "4d8037536e74c7efc525e84c21515ea86c7a6fe9afe5c4d559a593be8fa91352"
hypothesis:
  claim: "Artefatos dbt e bundles de introspecção DuckDB fornecem evidência suficiente para enriquecer lineage e revisar lakehouse sem executar código."
  prediction: "O analisador identifica recursos dbt, dependências, testes, resultados e metadados DuckDB/Parquet/Iceberg, recusando SQL mutável e marcando lacunas."
  experiment: "Carregar fixtures sintéticas de dbt e DuckDB por CLI/MCP e comparar envelopes canônicos."
acceptance:
  - id: AC1
    statement: "O analisador dbt normaliza manifest, catalog e run_results, preserva dependências e registra referência ausente como unresolved."
    verified_by: {kind: test, ref: "tests/test_analytics_microscope.py::test_dbt_artifacts_preserve_lineage_and_results"}
  - id: AC2
    statement: "O microscópio DuckDB aceita apenas operações read-only declaradas e retorna objetos, colunas, estatísticas, snapshots e comparações SQL."
    verified_by: {kind: test, ref: "tests/test_analytics_microscope.py::test_duckdb_microscope_is_read_only_and_structured"}
  - id: AC3
    statement: "CLI e MCP chamam o mesmo núcleo para dbt e DuckDB."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli analyze dbt-artifacts --path fixtures/analytics/dbt"}
success:
  - id: SC1
    metric: "Dependências e SQL mutável não resolvido aparecem com código explícito"
    source: "envelopes dos analisadores e fixtures"
out_of_scope:
  - "Executar dbt, DuckDB, Trino ou Spark."
  - "Afirmar compatibilidade de versão sem metadata/evidence do artefato."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Adicionar testes de paridade e regenerar referência/surface lock."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc]
---

# ANALYTICS_ENGINEERING_MICROSCOPE — requisitos

O resultado separa fatos declarados de lacunas: ausência de run result não é
sucesso, e ausência de coluna/estatística não é ausência do atributo.
