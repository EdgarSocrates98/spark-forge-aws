---
sdd: 1
feature: ANALYTICS_ENGINEERING_MICROSCOPE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Ler manifest/catalog/run_results do dbt e bundles de introspecção DuckDB como evidência offline."
    tradeoffs: ["reprodutível e sem dependências de engine", "não executa SQL para preencher lacunas"]
  - id: B
    summary: "Instalar DuckDB/dbt e executar consultas durante analyze."
    tradeoffs: ["mais automação", "não determinístico, mutável e dependente de ambiente"]
chosen: A
---

# ANALYTICS_ENGINEERING_MICROSCOPE — exploração

O prompt pede dbt manifest/catalog/run_results, SQL lineage, testes,
incremental/snapshots/semântica e DuckDB como microscópio interno. A abordagem
A transforma artefatos já produzidos em fatos estruturados e deixa execução
para etapa explicitamente autorizada.
