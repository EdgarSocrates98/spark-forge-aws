<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_dbt_artifacts`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Normaliza manifest.json, catalog.json e run_results.json do dbt em recursos, dependências, colunas, materialization, testes, exposições e resultados. Não importa nem executa dbt; referência ausente vira unresolved e não sucesso implícito.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Diretório dbt ou manifest.json. |

## Na CLI

[`sparkforge analyze dbt-artifacts`](../cli/analyze.md)

## Capacidade

analyze dbt manifest catalog and run results

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
