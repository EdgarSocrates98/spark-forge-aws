---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/ANALYTICS_ENGINEERING_MICROSCOPE/define.md
  sha256: "78a5a45d5180d173eb775b3db31a6aac9a806c63960c328f62bb9483f17f62a6"
files:
  - {path: sparkforge_aws/analytics/__init__.py, action: create, reason: "API analytics engineering."}
  - {path: sparkforge_aws/analytics/dbt.py, action: create, reason: "Loader determinístico de dbt artifacts."}
  - {path: sparkforge_aws/analytics/duckdb.py, action: create, reason: "Contrato read-only de microscópio DuckDB."}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "Analisadores CLI/MCP compartilhados."}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Verbos analyze dbt-artifacts e duckdb-microscope."}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "Tools MCP estruturadas."}
  - {path: parity.yaml, action: modify, reason: "Registro de paridade."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por duas novas tools."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada dos verbos."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_dbt_artifacts.md, action: create, reason: "Referência gerada do tool dbt."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_duckdb_microscope.md, action: create, reason: "Referência gerada do tool DuckDB."}
  - {path: fixtures/analytics/dbt/manifest.json, action: create, reason: "Fixture dbt sintética."}
  - {path: fixtures/analytics/dbt/catalog.json, action: create, reason: "Fixture catalog sintética."}
  - {path: fixtures/analytics/dbt/run_results.json, action: create, reason: "Fixture de execução sintética."}
  - {path: fixtures/analytics/duckdb/microscope.yaml, action: create, reason: "Bundle DuckDB read-only."}
  - {path: tests/test_analytics_microscope.py, action: create, reason: "Lineage, read-only e paridade."}
  - {path: docs/knowledge/analytics-engineering-microscope.md, action: create, reason: "Guia operacional."}
decisions:
  - id: D1
    choice: "Artefato de dbt é fonte de lineage; SQL não é reexecutado."
    rejected: ["importar projeto dbt", "reconstruir dependências por regex sem manifest"]
    rollback: "git revert da feature; extratores anteriores continuam disponíveis."
  - id: D2
    choice: "DuckDB bundle declara observações e rejeita mutações."
    rejected: ["instalar pacote automaticamente", "executar SQL arbitrário no analyze"]
    rollback: "git revert do microscópio; nenhum banco externo foi alterado."
covers:
  - {part: "dbt", acceptance: [AC1]}
  - {part: "DuckDB", acceptance: [AC2]}
  - {part: "surfaces", acceptance: [AC3]}
---

# ANALYTICS_ENGINEERING_MICROSCOPE — desenho

```text
dbt artifacts ---------> dbt topology/lineage/results ----+
DuckDB bundle ----------> objects/stats/sql comparisons ---+--> CLI/MCP
```
