---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/ANALYTICS_ENGINEERING_MICROSCOPE/plan.md
  sha256: "0dc8dfe7076c28bd5db95c64a326473aa2bddbb5f2106ac578825cb9f3dd4fe2"
tasks:
  - id: T1
    status: skipped
  - id: T2
    status: skipped
  - id: T3
    status: skipped
claims:
  - text: "O analisador dbt preserva manifest, catalog, run_results, dependências, materialization e lacunas."
    evidence_ref: "tests/test_analytics_microscope.py::test_dbt_artifacts_preserve_lineage_and_results"
  - text: "O microscópio DuckDB é read-only, estruturado e recusa SQL mutável sem executar engine."
    evidence_ref: "tests/test_analytics_microscope.py::test_duckdb_microscope_is_read_only_and_structured"
  - text: "CLI e MCP compartilham contratos canônicos para dbt e DuckDB."
    evidence_ref: "tests/test_analytics_microscope.py::test_analytics_surfaces_share_contracts"
change_id: null
---

# ANALYTICS_ENGINEERING_MICROSCOPE — relatório do build

## Entrega

As três tarefas foram implementadas anteriormente: parser de dbt (`746e489`),
microscópio DuckDB e superfícies/fixtures/registros, e documentação
(`ff7f4f0`). O núcleo só lê artefatos já produzidos e não instala dbt/DuckDB,
executa SQL ou importa projetos.

## Desvio de execução dos testes

T1–T3 estão `skipped` no bloco red/green porque a implementação precede este
relatório e o histórico não preserva comandos vermelhos reproduzíveis. Nenhum
exit vermelho foi inventado. A validação atual executou os testes focados com
`python -m pytest tests/test_analytics_microscope.py
tests/test_fixtures_golden_analytics.py -q --basetemp
.sparkforge_aws/local/pytest-analytics-microscope`, com `5 passed`.

## Revisão

A revisão confirmou que manifest/catalog/run_results são a fonte de lineage,
que SQL não é reexecutado, que mutações DuckDB são recusadas e que ausência de
stats, catalog ou run result permanece unresolved.
