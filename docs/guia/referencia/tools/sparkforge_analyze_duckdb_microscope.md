<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_duckdb_microscope`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Lê bundle offline de microscópio DuckDB com objetos Parquet/Iceberg, colunas, estatísticas, snapshots, EXPLAIN e comparações SQL declaradas. Só aceita consultas read-only; não instala DuckDB, não executa SQL e não altera banco ou arquivos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Bundle JSON/YAML do microscópio. |

## Na CLI

[`sparkforge-aws analyze duckdb-microscope`](../cli/analyze.md)

## Capacidade

analyze read-only DuckDB Parquet and Iceberg microscope bundles

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
